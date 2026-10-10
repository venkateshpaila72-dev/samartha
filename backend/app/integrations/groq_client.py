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

    @classmethod
    async def format_whatsapp_storage_alert(
        cls,
        crop_name: str,
        batch_name: str,
        metric_name: str,
        metric_emoji: str,
        measured_value: float,
        unit: str,
        safe_limit_or_range_label: str,
        safe_limit_or_range_val: str,
        status_label: str,
        severity: str,
        recommended_action: str,
        reading_time: Optional[str] = None,
    ) -> Optional[str]:
        """Uses Groq LLM to format a professional, farmer-friendly WhatsApp alert message
        using ONLY verified backend data. Returns None on timeout or failure for deterministic fallback.
        Strictly prevents raw RAG research records, citations, or hallucinated values.
        """
        api_key = settings.GROQ_API_KEY.strip()
        if not api_key or api_key.startswith("your_"):
            return None

        system_prompt = (
            "You are FarmShield's WhatsApp Storage Alert formatting assistant.\n"
            "Your task is to format a clear, professional, farmer-friendly WhatsApp alert message "
            "using ONLY the verified backend information provided.\n\n"
            "CRITICAL RULES:\n"
            "1. Use ONLY the supplied values, crop name, batch name, safe limits, and action. "
            "Do NOT invent, alter, or hallucinate sensor readings, safe limits, or corrective actions.\n"
            "2. Structure the message cleanly with WhatsApp bolding (*text*) and emojis:\n"
            "🚨 *FarmShield Storage Alert*\n\n"
            "🌾 *Crop:* <crop_name>\n"
            "📦 *Batch:* <batch_name>\n\n"
            "<metric_emoji> *<metric_name>:* <measured_value><unit>\n"
            "✅ *<safe_limit_or_range_label>:* <safe_limit_or_range_val>\n"
            "⚠️ *Status:* <status_label>\n\n"
            "*Recommended action:*\n"
            "<farmer-friendly, actionable corrective procedure based directly on provided recommended_action>\n\n"
            "Please monitor the storage conditions and follow the recommended safety procedure.\n\n"
            "3. Under NO circumstances include RAG research records, research-paper abstracts, chunk citations (e.g., sar-4), "
            "'Traditional guidance', or raw database records.\n"
            "4. Output ONLY the formatted WhatsApp message text. No introductory or trailing chat filler."
        )

        user_content = (
            f"Verified Alert Context:\n"
            f"- Crop: {crop_name}\n"
            f"- Batch: {batch_name}\n"
            f"- Parameter: {metric_name} ({metric_emoji})\n"
            f"- Actual Reading: {measured_value:.1f}{unit}\n"
            f"- Safe Limit/Range Label: {safe_limit_or_range_label}\n"
            f"- Safe Limit/Range Value: {safe_limit_or_range_val}\n"
            f"- Alert Status: {status_label}\n"
            f"- Severity: {severity}\n"
            f"- Action: {recommended_action}\n"
        )
        if reading_time:
            user_content += f"- Reading Time: {reading_time}\n"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        models_to_try = [settings.GROQ_MODEL]
        for candidate in ["llama-3.1-8b-instant", "qwen/qwen3.8-27b"]:
            if candidate not in models_to_try:
                models_to_try.append(candidate)

        try:
            # Enforce 6-second timeout for snappy alert delivery
            async with httpx.AsyncClient(timeout=6.0) as client:
                for model_name in models_to_try:
                    payload = {
                        "model": model_name,
                        "messages": messages,
                        "temperature": 0.2,
                        "max_tokens": 400,
                    }
                    resp = await client.post(cls.API_URL, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"].strip()
                        lower_c = content.lower()
                        # Strict verification: reject if any raw research citations or RAG tokens leak
                        if "traditional guidance" in lower_c or "agricultural research record" in lower_c or "sar-" in lower_c:
                            logger.warning("Groq alert output contained forbidden RAG tokens; rejecting and falling back.")
                            return None
                        # Ensure core verified details are present
                        if crop_name.lower() in lower_c and f"{measured_value:.1f}" in content:
                            return content
                    elif resp.status_code == 404:
                        continue
                    else:
                        logger.warning("Groq returned %s for alert formatting: %s", resp.status_code, resp.text)
                        break
        except Exception as exc:
            logger.warning("Groq WhatsApp alert formatting failed or timed out: %s", exc)

        return None
