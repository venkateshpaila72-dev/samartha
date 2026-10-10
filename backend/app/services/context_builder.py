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
from app.schemas.chatbot import SourceReference


class AIContextBuilder:
    @classmethod
    def build_context(
        cls,
        user_id: str,
        batch_id: Optional[str],
        user_query: str,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {
            "has_batch_context": False,
            "crop_profile": None,
            "latest_reading": None,
            "active_alerts": [],
            "recent_diary_entries": [],
            "rag_sources": [],
            "structured_summary": "",
        }

        crop_name = None
        crop_category = None

        if batch_id:
            batch = StorageBatchRepository.get_by_id(batch_id)
            if batch:
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

        # Retrieve RAG Traditional Knowledge
        rag_sources: list[SourceReference] = RAGAdapter.retrieve_relevant_knowledge(
            query=user_query,
            crop_name=crop_name,
            crop_category=crop_category,
            top_k=2,
        )
        context["rag_sources"] = rag_sources

        return context
