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

import re

MONTH_MAP = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sept": 9, "sep": 9, "october": 10, "oct": 10,
    "november": 11, "nov": 11, "december": 12, "dec": 12,
}

SYSTEM_PROMPT = """You are FarmShield Advisory Assistant, a friendly, multilingual, voice-enabled AI farming assistant.
You help Indian farmers protect stored crops, monitor granary conditions, understand weather forecasts, decide when and where to sell in mandis, and manage farming schedules through warm, clear conversation.

Core Guidelines:
1. GREETINGS:
   If a farmer says "Hello", "Hi", "Namaste", "Good morning", or similar greetings, respond warmly and briefly in 1-2 friendly sentences.
   Example: "Hello! 👋 How is your farm doing today? I can help you check your crop storage, weather, market prices, or harvesting plans."
   DO NOT return a long technical dissertation for a simple greeting.
2. TONE & SIMPLICITY:
   Match the farmer's language and tone where possible. Explain technical concepts in simple, everyday language. Use short paragraphs, clear headings, numbered steps, and practical recommendations.
3. FARMING RECOMMENDATIONS STRUCTURE:
   When answering a farming question (storage preservation, weather planning, market prices/selling, pest control), format your response clearly using these sections:

   **Recommendation:** A clear, direct answer to the farmer's question.

   **Why:** The key facts supporting the answer (e.g., current sensor readings vs ICAR safe limits, APMC modal prices vs haulage deductions, rain probability).

   **What to do next:**
   1. Immediate action.
   2. Preventive or secondary step.
   3. When to measure, inspect, or execute.

   **Risks to consider:** Relevant weather, storage deterioration, price volatility, or crop risks.

   **Data used:** Brief source, date, or sensor telemetry summary.

   Do not force this structure onto basic conversational questions or greetings.
4. HONESTY & FACTUAL ACCURACY:
   - Use database records and live context as the source of truth for batch readings, weather, and verified crop limits.
   - Never invent or fabricate sensor readings, safe limits, market prices, weather conditions, or sources.
   - Clearly distinguish measured facts, forecasts, estimates, and general advice.
   - If uncertain or if information is missing, say so clearly and explain what is needed.
5. RESPECTING FARMER PROFILE & MEMORY:
   - Never repeatedly ask for information already present in the farmer profile or conversation context.
   - When the farmer mentions scheduling an activity (e.g., harvest date), ask for confirmation before modifying records:
     Example: "Would you like me to set your wheat harvest date to October 18, 2026?"
"""


def parse_harvest_date_intent(text: str) -> Optional[tuple[str, Optional[str]]]:
    """Detects intent to set/plan harvest date. Returns (iso_date_string, display_date_str)."""
    t = text.lower()
    if not any(k in t for k in ["harvest", "reap", "cutting"]):
        return None

    # Check for YYYY-MM-DD
    m_iso = re.search(r"\b(202\d-\d{1,2}-\d{1,2})\b", t)
    if m_iso:
        d = m_iso.group(1)
        return d, d

    # Pattern: Month Day (e.g., October 18 or Oct 18, 2026)
    m1 = re.search(
        r"\b(january|february|march|april|may|june|july|august|september|sep|october|oct|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(202\d))?\b",
        t,
    )
    if m1:
        month_name = m1.group(1)
        day_num = int(m1.group(2))
        year_num = int(m1.group(3)) if m1.group(3) else 2026
        month_num = MONTH_MAP.get(month_name, 10)
        iso_str = f"{year_num:04d}-{month_num:02d}-{day_num:02d}"
        disp_str = f"{month_name.title()} {day_num}, {year_num}"
        return iso_str, disp_str

    # Pattern: Day Month (e.g., 18th October, 18 Oct 2026)
    m2 = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(january|february|march|april|may|june|july|august|september|sep|october|oct|november|december)(?:\s*,?\s*(202\d))?\b",
        t,
    )
    if m2:
        day_num = int(m2.group(1))
        month_name = m2.group(2)
        year_num = int(m2.group(3)) if m2.group(3) else 2026
        month_num = MONTH_MAP.get(month_name, 10)
        iso_str = f"{year_num:04d}-{month_num:02d}-{day_num:02d}"
        disp_str = f"{month_name.title()} {day_num}, {year_num}"
        return iso_str, disp_str

    return None


def is_confirmation_reply(text: str) -> bool:
    t = text.strip().lower().rstrip("!.?~")
    confirm_phrases = {
        "yes", "yes confirm", "yes, confirm", "yes confirm it", "yes, confirm it",
        "confirm", "confirm it", "please confirm", "proceed", "yes proceed", "sure", "ok confirm",
        "haan", "theek hai", "yes please", "do it", "confirm please", "ok please", "yup"
    }
    return t in confirm_phrases or any(t.startswith(cp) for cp in ["yes, confirm", "yes confirm", "confirm it", "proceed with"])


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
        context_data = await AIContextBuilder.build_context(
            user_id=user_id,
            batch_id=batch_id,
            user_query=payload.message,
            language=payload.language or getattr(convo, "language", None),
        )

        # 2. Check if user is confirming a pending action from the conversation
        prior_msgs = cls.list_messages(convo_id)
        last_bot_msg = next((m for m in reversed(prior_msgs) if m.role == "assistant" and getattr(m, "pending_action", None)), None)

        pending_action_data = None
        action_executed_data = None
        bot_response = None
        sources: list[SourceReference] = []

        if is_confirmation_reply(payload.message) and last_bot_msg and last_bot_msg.pending_action:
            act = last_bot_msg.pending_action
            target_b_id = act.get("batch_id")
            new_date = act.get("harvest_date") or act.get("date")
            c_name = act.get("crop_name", "crop")

            from app.repositories.storage_batch_repository import StorageBatchRepository
            target_batch = StorageBatchRepository.get_by_id(target_b_id) if target_b_id else None
            is_admin = current_user and current_user.get("role") == "admin"

            if target_batch and (target_batch.get("farmer_id") == user_id or target_batch.get("user_id") == user_id or is_admin):
                StorageBatchRepository.update(target_b_id, {"harvest_date": new_date})
                bot_response = f"✅ Confirmed! I have set your {c_name} harvest date to **{new_date}** in your verified farm storage records."
                action_executed_data = {
                    "action_type": act.get("action_type", "update_harvest_date"),
                    "batch_id": target_b_id,
                    "crop_name": c_name,
                    "harvest_date": new_date,
                    "date": new_date,
                    "status": "success",
                }
            else:
                bot_response = f"⚠️ Could not confirm: storage batch '{target_b_id}' was not found or access was denied."

        # 3. Check if user wants to schedule or set harvest date
        harvest_intent = parse_harvest_date_intent(payload.message) if not bot_response else None
        if harvest_intent and not bot_response:
            iso_d, disp_d = harvest_intent
            from app.repositories.storage_batch_repository import StorageBatchRepository
            target_b = None
            if batch_id:
                target_b = StorageBatchRepository.get_by_id(batch_id)
            else:
                user_batches = StorageBatchRepository.list_by_farmer(user_id, status="active")
                if len(user_batches) == 1:
                    target_b = user_batches[0]
                elif len(user_batches) > 1:
                    # Match by crop name if mentioned in query
                    for ub in user_batches:
                        b_crop = (ub.get("custom_batch_name") or "").lower()
                        if any(c in payload.message.lower() for c in b_crop.split()):
                            target_b = ub
                            break

            if target_b:
                c_name = target_b.get("custom_batch_name") or "crop"
                b_ident = target_b.get("batch_id") or target_b.get("id")
                bot_response = f"Would you like me to set your {c_name} harvest date to **{disp_d}**?"
                pending_action_data = {
                    "action_type": "update_harvest_date",
                    "batch_id": b_ident,
                    "crop_name": c_name,
                    "harvest_date": iso_d,
                    "date": iso_d,
                    "display_date": disp_d,
                    "confirmation_prompt": f"Set {c_name} harvest date to {disp_d}?",
                }
            else:
                bot_response = f"I can set your harvest date to **{disp_d}**. Which storage batch or crop would you like to schedule this for?"

        # 4. Standard conversational advisory if no action intercepted
        if not bot_response:
            bot_response, is_live = await GroqClient.generate_response(
                system_prompt=SYSTEM_PROMPT,
                user_message=payload.message,
                context_data=context_data,
            )

            # Assemble strictly relevant sources with deduplication
            seen_titles = set()
            if not context_data.get("is_greeting"):
                # Only include crop profile if user asked about limits, measurements, or storage
                q_l = payload.message.lower()
                is_storage_rel = any(w in q_l for w in ["temp", "humid", "limit", "safe", "storage", "hot", "cool", "moist", "pest"])
                if is_storage_rel and context_data.get("crop_profile"):
                    cp = context_data["crop_profile"]
                    t_title = f"Verified ICAR Profile: {cp.get('crop_name')}"
                    sources.append(
                        SourceReference(
                            title=t_title,
                            source_name=cp.get("source", "ICAR Standards"),
                            source_type="verified_crop_profile",
                            content_excerpt=f"Safe Temp: {cp.get('recommended_temp_min_c')}-{cp.get('recommended_temp_max_c')}°C | Safe RH: {cp.get('recommended_rh_min_percent')}-{cp.get('recommended_rh_max_percent')}%",
                            url="https://icar.org.in/",
                        )
                    )
                    seen_titles.add(t_title)

                for r_src in context_data.get("rag_sources", []):
                    if r_src.title not in seen_titles:
                        sources.append(r_src)
                        seen_titles.add(r_src.title)

        # 5. Save user message
        user_msg_id = f"msg_{uuid.uuid4().hex[:10]}"
        user_msg_doc = {
            "message_id": user_msg_id,
            "conversation_id": convo_id,
            "role": "user",
            "content": payload.message,
            "sources": [],
            "suggested_followups": [],
            "batch_context_used": None,
            "pending_action": None,
            "action_executed": None,
            "timestamp": now_iso,
        }
        _IN_MEMORY_MSGS.append(user_msg_doc.copy())
        col = cls._msg_col()
        if col is not None:
            col.insert_one(user_msg_doc.copy())

        # 6. Suggested Followups
        if context_data.get("is_greeting"):
            followups = [
                "Check wheat storage temperature & safe limits",
                "What is the 7-day weather forecast?",
                "Should I sell my wheat in the mandi today?",
                "How do I prevent storage weevils naturally?",
            ]
        elif pending_action_data:
            followups = [
                "Yes, confirm it.",
                "Cancel, change date",
            ]
        else:
            followups = [
                "What are the verified safe humidity limits?",
                "When is the best time to ventilate the storage room?",
                "What is the mandi price trend for this crop?",
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
                "crop_name": (context_data.get("crop_profile") or {}).get("crop_name"),
            }
            if batch_id
            else None,
            "pending_action": pending_action_data,
            "action_executed": action_executed_data,
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
            pending_action=pending_action_data,
            action_executed=action_executed_data,
            timestamp=bot_now_iso,
        )

    @classmethod
    async def confirm_action(
        cls,
        user_id: str,
        convo_id: str,
        action_data: dict,
        current_user: Optional[dict] = None,
    ) -> ChatMessageOut:
        """Executes a confirmed pending action (e.g., harvest date update) with authorization."""
        target_b_id = action_data.get("batch_id")
        new_date = action_data.get("harvest_date")
        c_name = action_data.get("crop_name", "crop")

        if not target_b_id or not new_date:
            raise ValueError("Missing batch_id or harvest_date for action confirmation.")

        from app.repositories.storage_batch_repository import StorageBatchRepository
        target_batch = StorageBatchRepository.get_by_id(target_b_id)
        if not target_batch:
            raise ValueError(f"Storage batch '{target_b_id}' not found.")

        is_admin = current_user and current_user.get("role") == "admin"
        owner_id = target_batch.get("farmer_id") or target_batch.get("user_id")
        if owner_id != user_id and not is_admin:
            raise ValueError("Forbidden: You do not own this storage batch.")

        StorageBatchRepository.update(target_b_id, {"harvest_date": new_date})

        bot_msg_id = f"msg_{uuid.uuid4().hex[:10]}"
        bot_now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        msg_content = f"✅ Confirmed! I have set your {c_name} harvest date to **{new_date}** in your verified farm storage records."

        action_executed = {
            "action_type": action_data.get("action_type", "update_harvest_date"),
            "batch_id": target_b_id,
            "crop_name": c_name,
            "harvest_date": new_date,
            "date": new_date,
            "status": "success",
        }

        doc = {
            "message_id": bot_msg_id,
            "conversation_id": convo_id,
            "role": "assistant",
            "content": msg_content,
            "sources": [],
            "suggested_followups": ["What should I prepare before harvest?", "Check weather forecast for harvest date"],
            "batch_context_used": {"batch_id": target_b_id, "crop_name": c_name},
            "pending_action": None,
            "action_executed": action_executed,
            "timestamp": bot_now_iso,
        }
        _IN_MEMORY_MSGS.append(doc.copy())
        col = cls._msg_col()
        if col is not None:
            col.insert_one(doc.copy())

        return ChatMessageOut(**doc)
