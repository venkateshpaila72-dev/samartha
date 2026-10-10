"""Chatbot Service for FarmShield."""

import datetime
import uuid
from typing import Optional

from app.db.collection_names import CONVERSATIONS_COLLECTION, MESSAGES_COLLECTION
from app.db.mongo import get_db
from app.integrations.groq_client import GroqClient
from app.schemas.chatbot import (
    ChatMessageCreate,
    ChatMessageOut,
    ConversationCreate,
    ConversationOut,
    SourceReference,
)
from app.services.context_builder import AIContextBuilder

_IN_MEMORY_CONVOS: dict[str, dict] = {}
_IN_MEMORY_MSGS: list[dict] = []

SYSTEM_PROMPT = """You are FarmShield Advisory Assistant, an AI expert in crop post-harvest storage monitoring and agricultural preservation.
You help Indian farmers protect stored grain, pulses, oilseeds, and vegetables from deterioration, pests, and mold.

Core Rules:
1. Use database records as the source of truth for persisted batch readings and verified crop reference parameters.
2. Cite supporting agricultural sources (e.g., ICAR, IIRR, CPRI, IIPR) and traditional methods where provided.
3. Clearly distinguish facts, recommendations, and uncertain inferences.
4. Never invent sensor readings or crop temperature limits.
5. Provide actionable, practical storage instructions (ventilation timing, pest deterrence, sun-drying).
"""


class ChatbotService:
    @staticmethod
    def _convo_col():
        db = get_db()
        return db[CONVERSATIONS_COLLECTION] if db is not None else None

    @staticmethod
    def _msg_col():
        db = get_db()
        return db[MESSAGES_COLLECTION] if db is not None else None

    @classmethod
    def create_conversation(cls, user_id: str, payload: ConversationCreate) -> ConversationOut:
        if payload.batch_id:
            from app.repositories.storage_batch_repository import StorageBatchRepository
            b = StorageBatchRepository.get_by_id(payload.batch_id)
            if not b:
                raise ValueError(f"Storage batch '{payload.batch_id}' not found.")
            owner_id = b.get("user_id") or b.get("farmer_id")
            if owner_id != user_id:
                raise ValueError(f"Forbidden: You do not own storage batch '{payload.batch_id}'.")

        convo_id = f"conv_{uuid.uuid4().hex[:10]}"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        doc = {
            "conversation_id": convo_id,
            "user_id": user_id,
            "batch_id": payload.batch_id,
            "title": payload.title or "Storage Advisory Chat",
            "language": payload.language,
            "created_at": now_iso,
            "updated_at": now_iso,
            "message_count": 0,
        }
        _IN_MEMORY_CONVOS[convo_id] = doc.copy()
        col = cls._convo_col()
        if col is not None:
            col.insert_one(doc.copy())
        return ConversationOut(**doc)

    @classmethod
    def list_conversations(cls, user_id: str) -> list[ConversationOut]:
        col = cls._convo_col()
        if col is not None:
            docs = list(col.find({"user_id": user_id}).sort("updated_at", -1))
            if docs:
                for d in docs:
                    d.pop("_id", None)
                return [ConversationOut(**d) for d in docs]
        user_convs = [c for c in _IN_MEMORY_CONVOS.values() if c["user_id"] == user_id]
        return [ConversationOut(**c) for c in sorted(user_convs, key=lambda x: x["updated_at"], reverse=True)]

    @classmethod
    def get_conversation(cls, convo_id: str, user_id: str) -> Optional[ConversationOut]:
        col = cls._convo_col()
        if col is not None:
            doc = col.find_one({"conversation_id": convo_id, "user_id": user_id})
            if doc:
                doc.pop("_id", None)
                return ConversationOut(**doc)
        c = _IN_MEMORY_CONVOS.get(convo_id)
        if c and c["user_id"] == user_id:
            return ConversationOut(**c)
        return None

    @classmethod
    def list_messages(cls, convo_id: str) -> list[ChatMessageOut]:
        col = cls._msg_col()
        if col is not None:
            docs = list(col.find({"conversation_id": convo_id}).sort("timestamp", 1))
            if docs:
                for d in docs:
                    d.pop("_id", None)
                return [ChatMessageOut(**d) for d in docs]
        conv_msgs = [m for m in _IN_MEMORY_MSGS if m["conversation_id"] == convo_id]
        return [ChatMessageOut(**m) for m in sorted(conv_msgs, key=lambda x: x["timestamp"])]

    @classmethod
    async def post_message(
        cls,
        user_id: str,
        convo_id: str,
        payload: ChatMessageCreate,
        current_user: Optional[dict] = None,
    ) -> ChatMessageOut:
        convo = cls.get_conversation(convo_id, user_id)
        if not convo:
            raise ValueError("Conversation not found or unauthorized.")

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        batch_id = payload.batch_id or convo.batch_id

        if batch_id:
            from app.repositories.storage_batch_repository import StorageBatchRepository
            b = StorageBatchRepository.get_by_id(batch_id)
            if not b:
                raise ValueError(f"Storage batch '{batch_id}' not found.")
            is_admin = current_user and current_user.get("role") == "admin"
            owner_id = b.get("user_id") or b.get("farmer_id")
            if owner_id != user_id and not is_admin:
                raise ValueError(f"Forbidden: You do not own storage batch '{batch_id}'.")

        # 1. Build context
        context_data = AIContextBuilder.build_context(
            user_id=user_id,
            batch_id=batch_id,
            user_query=payload.message,
        )

        # 2. Save user message
        user_msg_id = f"msg_{uuid.uuid4().hex[:10]}"
        user_msg_doc = {
            "message_id": user_msg_id,
            "conversation_id": convo_id,
            "role": "user",
            "content": payload.message,
            "sources": [],
            "suggested_followups": [],
            "batch_context_used": None,
            "timestamp": now_iso,
        }
        _IN_MEMORY_MSGS.append(user_msg_doc.copy())
        col = cls._msg_col()
        if col is not None:
            col.insert_one(user_msg_doc.copy())

        # 3. Call Groq client
        bot_response, is_live = await GroqClient.generate_response(
            system_prompt=SYSTEM_PROMPT,
            user_message=payload.message,
            context_data=context_data,
        )

        # 4. Assembled Sources
        sources: list[SourceReference] = []
        if context_data.get("crop_profile"):
            cp = context_data["crop_profile"]
            sources.append(
                SourceReference(
                    title=f"Verified Profile: {cp.get('crop_name')}",
                    source_name=cp.get("source", "ICAR Standards"),
                    source_type="verified_crop_profile",
                    content_excerpt=f"Safe Temp: {cp.get('recommended_temp_min_c')}-{cp.get('recommended_temp_max_c')}°C | Safe RH: {cp.get('recommended_rh_min_percent')}-{cp.get('recommended_rh_max_percent')}% | Max Moisture: {cp.get('safe_moisture_percent')}%",
                    url="https://icar.org.in/",
                )
            )
        sources.extend(context_data.get("rag_sources", []))

        # 5. Suggested Followups
        followups = [
            "How do I prevent weevils naturally?",
            "What should I do if humidity exceeds limits?",
            "When is the best time to ventilate the storage room?",
        ]

        bot_msg_id = f"msg_{uuid.uuid4().hex[:10]}"
        bot_now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        bot_msg_doc = {
            "message_id": bot_msg_id,
            "conversation_id": convo_id,
            "role": "assistant",
            "content": bot_response,
            "sources": [s.model_dump() for s in sources],
            "suggested_followups": followups,
            "batch_context_used": {
                "batch_id": batch_id,
                "crop_name": context_data.get("crop_profile", {}).get("crop_name"),
            }
            if batch_id
            else None,
            "timestamp": bot_now_iso,
        }
        _IN_MEMORY_MSGS.append(bot_msg_doc.copy())
        if col is not None:
            col.insert_one(bot_msg_doc.copy())

        # Update conversation message count
        if convo_id in _IN_MEMORY_CONVOS:
            _IN_MEMORY_CONVOS[convo_id]["updated_at"] = bot_now_iso
            _IN_MEMORY_CONVOS[convo_id]["message_count"] = _IN_MEMORY_CONVOS[convo_id].get("message_count", 0) + 2

        convo_col = cls._convo_col()
        if convo_col is not None:
            convo_col.update_one(
                {"conversation_id": convo_id},
                {"$set": {"updated_at": bot_now_iso}, "$inc": {"message_count": 2}},
            )

        return ChatMessageOut(
            message_id=bot_msg_id,
            conversation_id=convo_id,
            role="assistant",
            content=bot_response,
            sources=sources,
            suggested_followups=followups,
            batch_context_used=bot_msg_doc["batch_context_used"],
            timestamp=bot_now_iso,
        )
