"""RAG Adapter for Traditional Agricultural Storage Knowledge & Pinecone Vector DB.
Retrieves source-backed traditional and indigenous post-harvest storage techniques
from Pinecone vector database index with fallback to curated ICAR ITK knowledge base.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List

from app.core.config import settings
from app.schemas.chatbot import SourceReference

logger = logging.getLogger(__name__)

_RAG_DOCUMENTS: list[dict] = []
_PINECONE_CLIENT = None
_PINECONE_INDEX = None


def _load_rag_documents():
    global _RAG_DOCUMENTS
    if not _RAG_DOCUMENTS:
        data_path = Path(__file__).resolve().parent.parent.parent / "data" / "traditional_knowledge_rag.json"
        if data_path.exists():
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    _RAG_DOCUMENTS = json.load(f)
            except Exception as e:
                logger.error(f"Error loading local traditional knowledge documents: {e}")


def _get_pinecone_index():
    global _PINECONE_CLIENT, _PINECONE_INDEX
    if _PINECONE_INDEX is not None:
        return _PINECONE_CLIENT, _PINECONE_INDEX

    api_key = settings.PINECONE_API_KEY.strip()
    index_name = settings.PINECONE_INDEX_NAME.strip()

    if not api_key or api_key.startswith("your_") or not index_name:
        return None, None

    try:
        from pinecone import Pinecone

        client = Pinecone(api_key=api_key)
        index = client.Index(index_name)
        _PINECONE_CLIENT = client
        _PINECONE_INDEX = index
        logger.info(f"Connected to Pinecone vector index '{index_name}'.")
        return _PINECONE_CLIENT, _PINECONE_INDEX
    except Exception as e:
        logger.warning(f"Could not initialize Pinecone client for index '{index_name}': {e}")
        return None, None


class RAGAdapter:
    """Hybrid Retrieval-Augmented Generation (RAG) Adapter.
    Combines Pinecone Vector DB with verified ICAR Traditional Storage Knowledge.
    """

    @classmethod
    def is_pinecone_configured(cls) -> bool:
        return bool(
            settings.PINECONE_API_KEY.strip()
            and not settings.PINECONE_API_KEY.startswith("your_")
            and settings.PINECONE_INDEX_NAME.strip()
        )

    @classmethod
    def _retrieve_from_pinecone(
        cls,
        query: str,
        top_k: int = 2,
    ) -> List[SourceReference]:
        """Queries Pinecone vector index using inference embeddings."""
        pc, index = _get_pinecone_index()
        if not pc or not index:
            return []

        try:
            # Generate embedding via Pinecone Inference (1024 dimensions matching index)
            emb_res = pc.inference.embed(
                model="multilingual-e5-large",
                inputs=[query],
                parameters={"input_type": "query", "truncate": "END"},
            )
            if not emb_res or len(emb_res) == 0:
                return []

            vector = emb_res[0].values
            query_res = index.query(
                vector=vector,
                top_k=top_k,
                namespace="farming-docs",
                include_metadata=True,
            )

            results: List[SourceReference] = []
            for match in query_res.matches:
                meta = match.metadata or {}
                raw_text = meta.get("text", "")
                if not raw_text:
                    continue

                clean_text = " ".join(raw_text.split())
                source_doc = meta.get("source", "Agricultural Research Archive")
                results.append(
                    SourceReference(
                        title=f"Agricultural Research Record ({source_doc})",
                        source_name="Pinecone Vector Knowledge Base (sar)",
                        source_type="vector_rag",
                        content_excerpt=clean_text[:350] + ("..." if len(clean_text) > 350 else ""),
                        relevance_score=round(float(match.score or 0.0), 3),
                        url="https://icar.org.in/",
                    )
                )
            return results
        except Exception as e:
            logger.warning(f"Pinecone vector search failed: {e}. Falling back to traditional knowledge.")
            return []

    @classmethod
    def _retrieve_from_local_knowledge(
        cls,
        query: str,
        crop_name: Optional[str] = None,
        crop_category: Optional[str] = None,
        top_k: int = 2,
    ) -> List[SourceReference]:
        """Queries local curated traditional agricultural storage practices."""
        _load_rag_documents()
        if not _RAG_DOCUMENTS:
            return []

        query_terms = set(query.lower().split())
        scored_docs = []

        for doc in _RAG_DOCUMENTS:
            score = 0.0
            doc_text = f"{doc.get('title', '')} {doc.get('content', '')} {' '.join(doc.get('tags', []))}".lower()

            # Crop matching bonus
            if crop_name and crop_name.lower() in doc.get("crop_name", "").lower():
                score += 5.0

            if crop_category and crop_category.lower() in doc.get("crop_category", "").lower():
                score += 3.0

            # Keyword matching
            matched_terms = [t for t in query_terms if len(t) > 3 and t in doc_text]
            score += len(matched_terms) * 2.0

            if score > 0:
                scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        top_items = scored_docs[:top_k]

        results: List[SourceReference] = []
        for score, doc in top_items:
            results.append(
                SourceReference(
                    title=doc.get("title", "Traditional Storage Method"),
                    source_name=doc.get("source", "ICAR ITK Standards"),
                    source_type="traditional_rag_knowledge",
                    content_excerpt=doc.get("content", "")[:350] + "...",
                    relevance_score=round(score, 2),
                    url="https://icar.org.in/",
                )
            )
        return results

    @classmethod
    def retrieve_relevant_knowledge(
        cls,
        query: str,
        crop_name: Optional[str] = None,
        crop_category: Optional[str] = None,
        top_k: int = 3,
    ) -> List[SourceReference]:
        """Retrieves top-k relevant knowledge combining Pinecone Vector DB & ICAR ITK storage records."""
        combined: List[SourceReference] = []

        # 1. Pinecone Vector DB retrieval if configured
        if cls.is_pinecone_configured():
            pinecone_results = cls._retrieve_from_pinecone(query=query, top_k=2)
            combined.extend(pinecone_results)

        # 2. Local curated traditional storage knowledge
        needed_more = max(1, top_k - len(combined))
        local_results = cls._retrieve_from_local_knowledge(
            query=query,
            crop_name=crop_name,
            crop_category=crop_category,
            top_k=needed_more,
        )
        combined.extend(local_results)

        return combined[:top_k]
