"""AI Context Builder for FarmShield.
Assembles minimal, strictly relevant domain context from MongoDB and live providers (Weather, Market, ICAR RAG)
for Groq LLM reasoning without sending indiscriminate dumps.
"""

import logging
import re
from typing import Any, Optional

from app.integrations.rag_adapter import RAGAdapter
from app.repositories.alert_repository import AlertRepository
from app.repositories.crop_repository import CropRepository
from app.repositories.diary_repository import DiaryRepository
from app.repositories.sensor_repository import SensorRepository
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chatbot import SourceReference

logger = logging.getLogger(__name__)


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
    async def build_context(
        cls,
        user_id: str,
        batch_id: Optional[str],
        user_query: str,
        language: Optional[str] = None,
    ) -> dict[str, Any]:
        user_doc = UserRepository.get_by_id(user_id) or {}
        is_greeting = is_simple_greeting(user_query)
        selected_lang = (language or user_doc.get("preferred_language") or "en").lower().split("-")[0]

        context: dict[str, Any] = {
            "is_greeting": is_greeting,
            "preferred_language": selected_lang,
            "farmer_profile": {
                "name": user_doc.get("full_name", "Farmer"),
                "location": user_doc.get("village_or_location", "Farm"),
                "preferred_language": selected_lang,
            },
            "has_batch_context": False,
            "crop_profile": None,
            "latest_reading": None,
            "active_alerts": [],
            "recent_diary_entries": [],
            "rag_sources": [],
            "weather_data": None,
            "market_data": None,
            "intent": "general",
        }

        if is_greeting:
            context["intent"] = "greeting"
            return context

        q_lower = user_query.lower()
        crop_name = None
        crop_category = None

        # 1. Resolve Active Batch or detect crop from text
        if batch_id:
            batch = StorageBatchRepository.get_by_id(batch_id)
            owner_id = batch.get("user_id") or batch.get("farmer_id") if batch else None
            if batch and owner_id == user_id:
                context["has_batch_context"] = True
                context["batch_metadata"] = {
                    "batch_id": batch.get("batch_id") or batch.get("id"),
                    "batch_name": batch.get("custom_batch_name"),
                    "quantity_kg": batch.get("quantity_kg"),
                    "storage_structure": batch.get("storage_structure_type"),
                    "storage_location": batch.get("storage_location"),
                    "storage_start_date": batch.get("storage_start_date"),
                    "harvest_date": batch.get("harvest_date"),
                }

                # Load Verified Crop Profile
                crop_profile = CropRepository.get_by_id(batch.get("crop_id", ""))
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

        # If no crop profile yet, infer crop from query
        if not crop_name:
            all_crops = CropRepository.get_all()
            for cp in all_crops:
                c_n = (cp.get("crop_name") or "").lower()
                c_tokens = re.split(r"[\s()]+", c_n)
                if any(tok in q_lower for tok in c_tokens if len(tok) >= 4):
                    crop_name = cp.get("crop_name")
                    crop_category = cp.get("crop_category")
                    context["crop_profile"] = {
                        "crop_name": crop_name,
                        "crop_category": crop_category,
                        "variety": cp.get("variety"),
                        "crop_form": cp.get("crop_form"),
                        "recommended_temp_min_c": cp.get("recommended_temperature_min_c"),
                        "recommended_temp_max_c": cp.get("recommended_temperature_max_c"),
                        "recommended_rh_min_percent": cp.get("recommended_relative_humidity_min_percent"),
                        "recommended_rh_max_percent": cp.get("recommended_relative_humidity_max_percent"),
                        "safe_moisture_percent": cp.get("recommended_crop_moisture_percent"),
                        "ventilation_guidance": cp.get("ventilation_guidance"),
                        "pest_guidance": cp.get("pest_prevention_guidance"),
                        "spoilage_signs": cp.get("spoilage_warning_signs"),
                        "source": cp.get("source_name"),
                    }
                    break

        # 2. Intent Identification
        is_weather_intent = any(w in q_lower for w in ["weather", "rain", "forecast", "irrigat", "drying", "humid", "aerat", "sun", "wind", "cloud"])
        is_market_intent = any(m in q_lower for m in ["price", "sell", "selling", "mandi", "market", "quintal", "rate", "best day", "hold", "profit"])
        is_storage_intent = any(s in q_lower for s in ["storage", "temp", "temperature", "safe", "limit", "sensor", "violation", "alert", "reading", "granary", "bin"])
        is_pest_intent = is_storage_or_preservation_query(user_query)

        if is_weather_intent:
            context["intent"] = "weather"
        elif is_market_intent:
            context["intent"] = "market"
        elif is_storage_intent:
            context["intent"] = "storage"
        elif is_pest_intent:
            context["intent"] = "pest"
        else:
            context["intent"] = "general"

        # 3. Retrieve Live Weather Data if relevant
        if is_weather_intent or "weather" in q_lower:
            loc = user_doc.get("village_or_location") or "New Delhi, IN"
            try:
                from app.integrations.weather_client import WeatherClient
                w_report = await WeatherClient.get_weather(location=loc)
                context["weather_data"] = {
                    "location": loc,
                    "current_temperature_c": w_report.current_temperature_c,
                    "relative_humidity_percent": w_report.relative_humidity_percent,
                    "weather_condition": w_report.weather_condition,
                    "wind_speed_kmh": w_report.wind_speed_kmh,
                    "storage_impact_summary": w_report.storage_impact_summary,
                    "seven_day_forecast": [
                        {
                            "day": d.day_name,
                            "date": d.date,
                            "temp_max_c": d.temp_max_c,
                            "temp_min_c": d.temp_min_c,
                            "rain_prob_percent": d.precipitation_probability_percent,
                            "rain_mm": d.precipitation_sum_mm,
                            "condition": d.weather_condition,
                            "harvest_recommendation": d.harvest_recommendation,
                            "drying_recommendation": d.drying_recommendation,
                            "irrigation_recommendation": d.irrigation_recommendation,
                            "ventilation_recommendation": d.ventilation_recommendation,
                            "pest_disease_risk": d.pest_disease_risk,
                        }
                        for d in (w_report.seven_day_forecast or [])[:7]
                    ],
                    "thirty_day_outlook": w_report.thirty_day_outlook.model_dump() if w_report.thirty_day_outlook else None,
                }
            except Exception as e:
                logger.warning(f"Could not load weather data for context builder: {e}")

        # 4. Retrieve Live Mandi Market Data & Selling Recommendation if relevant
        if is_market_intent or "mandi" in q_lower or "price" in q_lower:
            target_crop = crop_name or "Wheat"
            latest_t = (context.get("latest_reading") or {}).get("temperature_c")
            crop_max_t = (context.get("crop_profile") or {}).get("recommended_temp_max_c")
            storage_risk_high = bool(context.get("active_alerts")) or (
                latest_t is not None and crop_max_t is not None and latest_t > crop_max_t
            )
            qty_qtl = None
            if context.get("batch_metadata", {}).get("quantity_kg"):
                qty_qtl = round(context["batch_metadata"]["quantity_kg"] / 100.0, 1)

            try:
                from app.integrations.market_client import MarketClient
                m_report = await MarketClient.get_market_prices(
                    crop_name=target_crop,
                    state=None,
                    district=None,
                    storage_risk_high=storage_risk_high,
                    quantity_quintals=qty_qtl,
                )
                context["market_data"] = {
                    "crop_name": target_crop,
                    "average_modal_price": m_report.average_modal_price,
                    "price_trend": m_report.price_trend,
                    "recommendation": m_report.recommendation,
                    "selling_recommendation": m_report.selling_recommendation.model_dump() if m_report.selling_recommendation else None,
                    "latest_mandi_prices": [
                        {
                            "mandi": p.market_name,
                            "district": p.district,
                            "state": p.state,
                            "modal_price": p.modal_price_per_quintal,
                            "date": p.price_date,
                        }
                        for p in (m_report.latest_prices or [])[:3]
                    ],
                }
            except Exception as e:
                logger.warning(f"Could not load market data for context builder: {e}")

        # 5. Retrieve RAG Traditional Knowledge if query pertains to pests/preservation
        rag_sources: list[SourceReference] = []
        if is_pest_intent or is_storage_intent:
            raw_sources = RAGAdapter.retrieve_relevant_knowledge(
                query=user_query,
                crop_name=crop_name,
                crop_category=crop_category,
                top_k=2,
            )
            for src in raw_sources:
                score = src.relevance_score or 0.0
                if (src.source_type == "vector_rag" and score >= 0.5) or (src.source_type != "vector_rag" and score >= 1.0):
                    rag_sources.append(src)
                    if len(rag_sources) >= 1:
                        break
            if not rag_sources:
                for src in raw_sources:
                    if src.source_type != "vector_rag" and (src.relevance_score or 0.0) >= 1.0:
                        rag_sources.append(src)
                        break

        context["rag_sources"] = rag_sources
        return context
