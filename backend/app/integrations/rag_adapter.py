"""RAG Adapter for Traditional Agricultural Storage Knowledge.
Retrieves source-backed traditional and indigenous post-harvest storage techniques.
"""

import json
from pathlib import Path
from typing import Optional

from app.schemas.chatbot import SourceReference

_RAG_DOCUMENTS: list[dict] = []


def _load_rag_documents():
    global _RAG_DOCUMENTS
    if not _RAG_DOCUMENTS:
        data_path = Path(__file__).resolve().parent.parent.parent / "data" / "traditional_knowledge_rag.json"
        if data_path.exists():
            with open(data_path, "r", encoding="utf-8") as f:
                _RAG_DOCUMENTS = json.load(f)


class RAGAdapter:
    @classmethod
    def retrieve_relevant_knowledge(
        cls,
        query: str,
        crop_name: Optional[str] = None,
        crop_category: Optional[str] = None,
        top_k: int = 3,
    ) -> list[SourceReference]:
        """Retrieve top-k relevant traditional storage practices matching query & crop."""
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

        results = []
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
