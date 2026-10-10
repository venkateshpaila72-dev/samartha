"""AI Context Builder for FarmShield.
Assembles minimal, strictly relevant domain context from MongoDB and RAG
for Groq LLM reasoning without sending indiscriminate dumps.
"""

from typing import Any, Optional

from app.integrations.rag_adapter import RAGAdapter
from app.repositories.alert_repository import AlertRepository
from app.repositories.crop_repository import CropRepository
from app.repositories.diary_repository import DiaryRepository
from app.repositories.sensor_repository import SensorRepository
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chatbot import SourceReference


def is_simple_greeting(text: str) -> bool:
    cleaned = text.strip().lower().rstrip("!.?~")
    greetings = {
        "hello", "hi", "hey", "namaste", "namaskar", "good morning",
        "good afternoon", "good evening", "vanakkam", "namaskara",
        "sat sri akaal", "kem cho", "khemo chho", "halo", "hola"
    }
    return cleaned in greetings or any(cleaned.startswith(g + " ") for g in greetings if len(g) > 2)


def is_storage_or_preservation_query(text: str) -> bool:
    t = text.lower()
    keywords = [
        "weevil", "pest", "mold", "mould", "rot", "preserv", "spoil",
        "hermetic", "pusa bin", "neem", "fumigat", "infest", "beetle",
        "fungus", "fungal", "traditional", "safe temp", "humidity limit"
    ]
    return any(k in t for k in keywords)


class AIContextBuilder:
    @classmethod
    def build_context(
        cls,
        user_id: str,
        batch_id: Optional[str],
        user_query: str,
    ) -> dict[str, Any]:
        user_doc = UserRepository.get_by_id(user_id) or {}
        is_greeting = is_simple_greeting(user_query)

        context: dict[str, Any] = {
            "is_greeting": is_greeting,
            "farmer_profile": {
                "name": user_doc.get("full_name", "Farmer"),
                "location": user_doc.get("village_or_location", "Farm"),
                "preferred_language": user_doc.get("preferred_language", "en"),
            },
            "has_batch_context": False,
            "crop_profile": None,
            "latest_reading": None,
            "active_alerts": [],
            "recent_diary_entries": [],
            "rag_sources": [],
            "structured_summary": "",
        }

        if is_greeting:
            return context

        crop_name = None
        crop_category = None

        if batch_id:
            batch = StorageBatchRepository.get_by_id(batch_id)
            owner_id = batch.get("user_id") or batch.get("farmer_id") if batch else None
            if batch and owner_id == user_id:
                context["has_batch_context"] = True
                context["batch_metadata"] = {
                    "batch_id": batch.get("batch_id"),
                    "batch_name": batch.get("custom_batch_name"),
                    "quantity_kg": batch.get("quantity_kg"),
                    "storage_structure": batch.get("storage_structure_type"),
                    "storage_location": batch.get("storage_location"),
                    "storage_start_date": batch.get("storage_start_date"),
                }

                # Load Verified Crop Profile
                crop_profile = CropRepository.get_by_id(batch["crop_id"])
                if crop_profile:
                    crop_name = crop_profile.get("crop_name")
                    crop_category = crop_profile.get("crop_category")
                    context["crop_profile"] = {
                        "crop_name": crop_name,
                        "crop_category": crop_category,
                        "variety": crop_profile.get("variety"),
                        "crop_form": crop_profile.get("crop_form"),
                        "recommended_temp_min_c": crop_profile.get("recommended_temperature_min_c"),
                        "recommended_temp_max_c": crop_profile.get("recommended_temperature_max_c"),
                        "recommended_rh_min_percent": crop_profile.get("recommended_relative_humidity_min_percent"),
                        "recommended_rh_max_percent": crop_profile.get("recommended_relative_humidity_max_percent"),
                        "safe_moisture_percent": crop_profile.get("recommended_crop_moisture_percent"),
                        "ventilation_guidance": crop_profile.get("ventilation_guidance"),
                        "pest_guidance": crop_profile.get("pest_prevention_guidance"),
                        "spoilage_signs": crop_profile.get("spoilage_warning_signs"),
                        "source": crop_profile.get("source_name"),
                    }

                # Load Latest Sensor Measurement
                latest = SensorRepository.get_latest_for_batch(batch_id)
                if latest:
                    context["latest_reading"] = {
                        "temperature_c": latest.get("temperature_c"),
                        "humidity_percent": latest.get("relative_humidity_percent"),
                        "moisture_percent": latest.get("crop_moisture_percent"),
                        "timestamp": latest.get("timestamp"),
                        "provenance": latest.get("provenance"),
                    }

                # Load Active Alerts
                alerts = AlertRepository.list_by_batch(batch_id, status="active")
                context["active_alerts"] = [
                    {
                        "condition": a.get("condition_type"),
                        "severity": a.get("severity"),
                        "measured_val": a.get("measured_value"),
                        "threshold": a.get("target_threshold"),
                        "action": a.get("recommended_action"),
                    }
                    for a in alerts[:3]
                ]

                # Load Recent Diary Notes
                diary_entries = DiaryRepository.list_by_batch(batch_id)
                context["recent_diary_entries"] = [
                    {
                        "category": d.get("observation_category"),
                        "text": d.get("observation_text"),
                        "severity": d.get("severity_assessment"),
                        "date": d.get("created_at"),
                    }
                    for d in diary_entries[:3]
                ]

        # Retrieve RAG Traditional Knowledge only when query pertains to storage preservation/pests
        rag_sources: list[SourceReference] = []
        if is_storage_or_preservation_query(user_query):
            raw_sources = RAGAdapter.retrieve_relevant_knowledge(
                query=user_query,
                crop_name=crop_name,
                crop_category=crop_category,
                top_k=2,
            )
            # Filter strictly: only keep items with meaningful relevance score and non-empty content
            for src in raw_sources:
                score = src.relevance_score or 0.0
                # Discard low-scoring vector noise (<0.6); keep genuine semantic matches or curated knowledge
                if (src.source_type == "vector_rag" and score >= 0.6) or (src.source_type != "vector_rag" and score >= 1.0):
                    rag_sources.append(src)
                    if len(rag_sources) >= 1:  # Limit to 1 clean relevant source to avoid citation clutter
                        break
            if not rag_sources:
                for src in raw_sources:
                    if src.source_type != "vector_rag" and (src.relevance_score or 0.0) >= 1.0:
                        rag_sources.append(src)
                        break

        context["rag_sources"] = rag_sources

        # Weather query detection
        q_lower = user_query.lower()
        if any(w in q_lower for w in ["weather", "rain", "forecast", "irrigat", "drying", "humid", "aerat"]):
            context["weather_query"] = True
            loc = user_doc.get("village_or_location") or "New Delhi, IN"
            try:
                from app.integrations.weather_client import WeatherClient
                # We can note location for prompt awareness
                context["weather_location"] = loc
            except Exception:
                pass

        # Market/selling query detection
        if any(m in q_lower for m in ["price", "sell", "selling", "mandi", "market", "quintal", "rate"]):
            context["market_query"] = True
            if crop_name:
                context["target_crop_name"] = crop_name

        return context
