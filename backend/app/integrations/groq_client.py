"""Groq LLM Client for FarmShield.
Calls Groq API with structured context or falls back gracefully when API key is pending.
"""

import logging
from typing import Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GroqClient:
    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    @classmethod
    async def generate_response(
        cls,
        system_prompt: str,
        user_message: str,
        context_data: dict,
    ) -> tuple[str, bool]:
        """Returns (response_text, is_live_groq_call)."""
        api_key = settings.GROQ_API_KEY.strip()

        if api_key and not api_key.startswith("your_"):
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context: {context_data}\n\nFarmer Question: {user_message}"},
                ]
                models_to_try = [settings.GROQ_MODEL]
                for fb in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
                    if fb not in models_to_try:
                        models_to_try.append(fb)

                async with httpx.AsyncClient(timeout=30.0) as client:
                    for model_name in models_to_try:
                        payload = {
                            "model": model_name,
                            "messages": messages,
                            "temperature": 0.3,
                            "max_tokens": 1024,
                        }
                        resp = await client.post(cls.API_URL, headers=headers, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            content = data["choices"][0]["message"]["content"]
                            return content, True
                        elif resp.status_code == 404:
                            logger.info(f"Model '{model_name}' not available on Groq, trying next candidate...")
                            continue
                        else:
                            logger.warning(f"Groq API returned status {resp.status_code}: {resp.text}")
                            break
            except Exception as e:
                logger.error(f"Error calling Groq API: {e}")

        # Intelligent Fallback Advisor based on assembled context
        crop_prof = context_data.get("crop_profile") or {}
        crop_name = crop_prof.get("crop_name", "your crop")
        latest = context_data.get("latest_reading") or {}
        alerts = context_data.get("active_alerts") or []
        rag = context_data.get("rag_sources") or []

        advisory_lines = []
        advisory_lines.append(f"### Storage Advisory for {crop_name}\n")

        if latest:
            t = latest.get("temperature_c", "N/A")
            rh = latest.get("humidity_percent", "N/A")
            advisory_lines.append(f"- **Current Storage Readings**: Temperature is **{t}°C** and Relative Humidity is **{rh}%**.")

        if crop_prof:
            t_min = crop_prof.get("recommended_temp_min_c")
            t_max = crop_prof.get("recommended_temp_max_c")
            rh_min = crop_prof.get("recommended_rh_min_percent")
            rh_max = crop_prof.get("recommended_rh_max_percent")
            safe_m = crop_prof.get("safe_moisture_percent")
            advisory_lines.append(f"- **Verified ICAR Target Limits**: Temperature should stay between **{t_min}°C – {t_max}°C**, RH between **{rh_min}% – {rh_max}%**, and maximum safe grain moisture is **{safe_m}%**.")

        if alerts:
            advisory_lines.append(f"\n⚠️ **Active Storage Alert Warning**:")
            for a in alerts:
                advisory_lines.append(f"  - Condition: `{a.get('condition')}` | Recommended Action: {a.get('action')}")

        if crop_prof.get("ventilation_guidance"):
            advisory_lines.append(f"\n- **Ventilation Guidance**: {crop_prof.get('ventilation_guidance')}")

        if rag:
            advisory_lines.append(f"\n- **Traditional Agricultural Knowledge**: {rag[0].title} — {rag[0].content_excerpt}")

        advisory_lines.append(
            "\n*Note: Recommendations are compiled from verified scientific references (ICAR/FAO) and current storage readings.*"
        )

        return "\n".join(advisory_lines), False
