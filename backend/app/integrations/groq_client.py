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
                # Prioritize verified active models on Groq
                models_to_try = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]
                if settings.GROQ_MODEL not in models_to_try:
                    models_to_try.append(settings.GROQ_MODEL)

                # Build rich, human-readable domain prompt context
                ctx_lines = []
                f_prof = context_data.get("farmer_profile") or {}
                ctx_lines.append(f"Farmer: {f_prof.get('name', 'Farmer')}, Location: {f_prof.get('location', 'Farm')}, Language: {f_prof.get('preferred_language', 'en')}")

                c_prof = context_data.get("crop_profile") or {}
                if c_prof:
                    ctx_lines.append(
                        f"Crop: {c_prof.get('crop_name')} | Safe Temp: {c_prof.get('recommended_temp_min_c')}-{c_prof.get('recommended_temp_max_c')}°C | "
                        f"Safe RH: {c_prof.get('recommended_rh_min_percent')}-{c_prof.get('recommended_rh_max_percent')}% | "
                        f"Safe Moisture: {c_prof.get('safe_moisture_percent')}% | ICAR Source: {c_prof.get('source', 'ICAR')}"
                    )

                latest = context_data.get("latest_reading") or {}
                if latest:
                    ctx_lines.append(f"Storage Sensor Telemetry: Temperature = {latest.get('temperature_c')}°C, Relative Humidity = {latest.get('humidity_percent')}%, Moisture = {latest.get('moisture_percent')}%")

                alerts = context_data.get("active_alerts") or []
                if alerts:
                    ctx_lines.append(f"Active Environmental Storage Alerts: {alerts}")

                w_data = context_data.get("weather_data")
                if w_data:
                    ctx_lines.append(
                        f"Live Weather ({w_data.get('location')}): Current Temp = {w_data.get('current_temperature_c')}°C, RH = {w_data.get('relative_humidity_percent')}%, Condition = {w_data.get('weather_condition')}, Wind = {w_data.get('wind_speed_kmh')} km/h. "
                        f"Storage Impact: {w_data.get('storage_impact_summary')}. 7-Day Forecast: {w_data.get('seven_day_forecast')}"
                    )

                m_data = context_data.get("market_data")
                if m_data:
                    ctx_lines.append(
                        f"Mandi Market Prices ({m_data.get('crop_name')}): Average Modal Price = ₹{m_data.get('average_modal_price')}/qtl, Trend = {m_data.get('price_trend')}. "
                        f"Selling Recommendation: {m_data.get('selling_recommendation')}. Recent Mandis: {m_data.get('latest_mandi_prices')}"
                    )

                rag_sources = context_data.get("rag_sources") or []
                if rag_sources:
                    for src in rag_sources:
                        ctx_lines.append(f"Verified Agricultural Reference: {src.title} — {src.content_excerpt}")

                full_context_str = "\n".join(ctx_lines)

                # Determine requested language
                user_lang = (
                    context_data.get("preferred_language")
                    or f_prof.get("preferred_language")
                    or "en"
                ).lower().split("-")[0]

                lang_names = {
                    "te": "Telugu (తెలుగు)",
                    "hi": "Hindi (हिंदी)",
                    "ta": "Tamil (தமிழ்)",
                    "kn": "Kannada (ಕನ್ನಡ)",
                    "mr": "Marathi (मराठी)",
                    "pa": "Punjabi (ਪੰਜਾਬੀ)",
                    "bn": "Bengali (বাংলা)",
                    "gu": "Gujarati (ગુજરાતી)",
                    "en": "English",
                }
                target_lang_name = lang_names.get(user_lang, "English")

                lang_directive = (
                    f"CRITICAL LANGUAGE INSTRUCTION: The farmer has explicitly selected {target_lang_name} on the website. "
                    f"You MUST generate your entire response in natural, fluent {target_lang_name}. "
                    f"Do NOT answer in English unless the selected language is English."
                    if user_lang != "en" else "Language: English."
                )

                messages = [
                    {"role": "system", "content": f"{system_prompt}\n\n{lang_directive}"},
                    {"role": "user", "content": f"Verified Farm Data:\n{full_context_str}\n\n{lang_directive}\n\nFarmer Query: {user_message}"},
                ]

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
        f_profile = context_data.get("farmer_profile") or {}
        user_lang = (
            context_data.get("preferred_language")
            or f_profile.get("preferred_language")
            or "en"
        ).lower().split("-")[0]

        if context_data.get("is_greeting"):
            f_name = f_profile.get("name")
            name_greet = f", {f_name}" if f_name and f_name != "Farmer" else ""
            if user_lang == "te":
                return f"నమస్కారం{name_greet}! 🙏 మీ వ్యవసాయం ఎలా సాగుతోంది? నేను మీ పంట నిల్వ ఉష్ణోగ్రత, వాతావరణం, మార్కెట్ ధరలు లేదా పంటకోత ప్రణాళికల గురించి సహాయపడగలను.", False
            elif user_lang == "hi":
                return f"नमस्ते{name_greet}! 🙏 आपका खेत कैसा है? मैं आपकी फसल भंडारण, मौसम, मंडी भाव या कटाई योजना में मदद कर सकता हूँ।", False
            return f"Hello{name_greet}! 👋 How is your farm doing today? I can help you check your crop storage, weather, market prices, or harvesting plans.", False

        q_lower = user_message.lower()
        crop_prof = context_data.get("crop_profile") or {}
        crop_name = crop_prof.get("crop_name", "your crop")
        latest = context_data.get("latest_reading") or {}
        alerts = context_data.get("active_alerts") or []
        w_data = context_data.get("weather_data") or {}
        m_data = context_data.get("market_data") or {}
        rag = context_data.get("rag_sources") or []

        # 1. Weather and Crop Planning Intent
        if context_data.get("intent") == "weather" or any(w in q_lower for w in ["weather", "rain", "forecast", "irrigat", "drying", "humid", "aerat"]):
            curr_temp = w_data.get("current_temperature_c", 28.0)
            curr_rh = w_data.get("relative_humidity_percent", 55.0)
            cond = w_data.get("weather_condition", "Clear Sky")
            loc = w_data.get("location", "your area")
            seven_day = w_data.get("seven_day_forecast") or []
            rain_risk = any(d.get("rain_prob_percent", 0) > 40 for d in seven_day[:3])

            if user_lang == "te":
                rec_text = "రాబోయే 48 గంటల్లో ధాన్యం ఆరబెట్టడం మరియు వ్యవసాయ పనులకు అనుకూల వాతావరణం ఉంది." if not rain_risk else "రాబోయే రోజుల్లో వర్ష సూచన ఉన్నందున ఆరుబయట ధాన్యం ఆరబెట్టడం వాయిదా వేయండి."
                lines = [
                    f"**Recommendation:** {rec_text}",
                    "",
                    f"**Why:** {loc} లో ప్రస్తుత వాతావరణం **{curr_temp}°C**, **{curr_rh}% సాపేక్ష తేమ**, మరియు **{cond}** నమోదు అయింది.",
                    "",
                    f"**What to do next:**",
                    f"1. పంటకోత లేదా ఆరబెట్టే ముందు 7 రోజుల వర్ష సూచనను తనిఖీ చేయండి.",
                    f"2. మధ్యాహ్నం వేళల్లో (12 PM–3 PM) బాహ్య తేమ తక్కువగా ఉన్నప్పుడు గోదాం వెంటిలేషన్ చేయండి.",
                    f"3. వర్షం పడే అవకాశం ఉన్నందున రవాణా వాహనాలపై టార్పాలిన్లను కప్పండి.",
                    "",
                    f"**Risks to consider:** వాతావరణ తేమ 70% కంటే ఎక్కువైతే ధాన్యం తేమను పీల్చుకుని బూజు పట్టే ప్రమాదం ఉంది.",
                    "",
                    f"**Data used:** ఓపెన్-మెటియో 7 రోజుల వాతావరణ సూచన ({loc}).",
                ]
            else:
                rec_text = "Favorable operational window for drying and field activities over the next 48 hours." if not rain_risk else "Postpone sun-drying and outdoor handling due to elevated rain probability in the upcoming forecast."
                lines = [
                    f"**Recommendation:** {rec_text}",
                    "",
                    f"**Why:** Current conditions in {loc} report **{curr_temp}°C**, **{curr_rh}% relative humidity**, and **{cond}**.",
                    "",
                    f"**What to do next:**",
                    f"1. Check 7-day rain probability before starting combine harvesting or open-air sun drying.",
                    f"2. Ventilate storage structures during dry afternoon hours (12 PM–3 PM) when outdoor humidity is lowest.",
                    f"3. Cover transport vehicles and keep tarpaulins ready in case of localized showers.",
                    "",
                    f"**Risks to consider:** Ambient relative humidity above 70% increases grain moisture absorption and accelerates fungal spore germination.",
                    "",
                    f"**Data used:** Open-Meteo 7-day meteorological forecast for {loc}.",
                ]
            return "\n".join(lines), False

        # 2. Market Prices & Selling Recommendations Intent
        if context_data.get("intent") == "market" or any(m in q_lower for m in ["price", "sell", "selling", "mandi", "market", "quintal", "rate"]):
            sell_rec = m_data.get("selling_recommendation") or {}
            avg_price = m_data.get("average_modal_price") or 2500.0
            trend = m_data.get("price_trend") or "stable"
            ranked = sell_rec.get("ranked_options") or []
            top_mandi = ranked[0].get("market_name") if ranked else "nearest APMC"
            top_price = ranked[0].get("modal_price_per_quintal") if ranked else avg_price

            decision = sell_rec.get("decision_summary") or ("Consider selling today at highest-paying nearby mandi" if trend != "rising" else "Consider holding for upcoming 3–5 days")
            if user_lang == "te":
                lines = [
                    f"**Recommendation:** {decision}",
                    "",
                    f"**Why:** {crop_name} సగటు మోడల్ ధర క్వింటాలుకు **₹{avg_price:,.0f}**, ధర ధోరణి **{trend}**. సమీప మార్కెట్: **{top_mandi}** (₹{top_price:,.0f}/క్వింటాల్).",
                    "",
                    f"**What to do next:**",
                    f"1. రవాణా ఖర్చులను (సుమారు ₹1.50/క్వింటాల్/కి.మీ) మినహాయించిన తర్వాత నికర రాబడిని లెక్కించండి.",
                    f"2. ధాన్యంలో తేమ సురక్షిత పరిమితి ({crop_prof.get('safe_moisture_percent', 12)}%) కంటే తక్కువగా ఉందని నిర్ధారించుకోండి.",
                    f"3. APMC ఎలక్ట్రానిక్ బరువు రశీదును తప్పనిసరిగా తీసుకోండి.",
                    "",
                    f"**Risks to consider:** సురక్షితం కాని గోదాముల్లో ఎక్కువ కాలం ఉంచితే ధాన్యం బరువు తగ్గడం, పురుగులు పట్టే ప్రమాదం ఉంది.",
                    "",
                    f"**Data used:** అగ్మార్క్‌నెట్ (Agmarknet) APMC మార్కెట్ రికార్డులు.",
                ]
            else:
                lines = [
                    f"**Recommendation:** {decision}",
                    "",
                    f"**Why:** Stored APMC mandi observations for {crop_name} indicate an average modal price of **₹{avg_price:,.0f} / quintal** with a **{trend}** price trend. Top alternative: **{top_mandi}** at **₹{top_price:,.0f} / qtl**.",
                    "",
                    f"**What to do next:**",
                    f"1. Compare net return after deducting local transport costs (approx. ₹1.50/qtl/km) before dispatching lot.",
                    f"2. Inspect stored grain moisture: ensure moisture is strictly below safe threshold ({crop_prof.get('safe_moisture_percent', 12)}%) before hauling.",
                    f"3. Avoid selling on unverified credit; ensure government APMC electronic weighment receipt.",
                    "",
                    f"**Risks to consider:** {sell_rec.get('storage_risk_assessment', 'Holding crops in unsealed storage risks dry-matter shrinkage and weevil infestation if storage limits are exceeded.')}",
                    "",
                    f"**Data used:** Verified Agmarknet APMC mandi records and FarmShield historical price trend model.",
                ]
            return "\n".join(lines), False

        # 3. Storage Monitoring & Threshold Violation Intent
        t = latest.get("temperature_c")
        rh = latest.get("humidity_percent")
        t_min = crop_prof.get("recommended_temp_min_c", 15.0)
        t_max = crop_prof.get("recommended_temp_max_c", 22.0)
        rh_min = crop_prof.get("recommended_rh_min_percent", 50.0)
        rh_max = crop_prof.get("recommended_rh_max_percent", 65.0)
        is_temp_violation = (t is not None and t > t_max) or "too high" in q_lower or "temperature" in q_lower or "hot" in q_lower

        if is_temp_violation and t is not None:
            alert_action = alerts[0].get("action") if alerts else "Increase ventilation and shade storage structure immediately."
            if user_lang == "te":
                lines = [
                    f"**Recommendation:** వేగంగా గోదాం లోని వెంటిలేషన్ లేదా ఎగ్జాస్ట్ ఫ్యాన్ లను ప్రారంభించండి, అంతర్గత ఉష్ణోగ్రతను {t_max:.0f}°C కంటే తక్కువగా తగ్గించండి.",
                    "",
                    f"**Why:** మీ గోదాం లోని ప్రస్తుత ఉష్ణోగ్రత **{t}°C**, ఇది సురక్షిత పరిమితి ({t_min:.0f}–{t_max:.0f}°C) కన్నా **క్లిష్టంగా (critical)** ఎక్కువ. తేమ {rh or 58}% ఉన్నప్పటికీ, అధిక ఉష్ణోగ్రత వల్ల {crop_name} ధాన్యం నాణ్యత కోల్పోతుంది.",
                    "",
                    f"**What to do next:**",
                    f"1. **తక్షణ చర్య:** {alert_action} లేదా ఎగ్జాస్ట్ ఫ్యాన్లు ఆన్ చేసి ఉష్ణోగ్రతను {t_min:.0f}–{t_max:.0f}°C మధ్యకు తగ్గించండి.",
                    f"2. **ప్రతిరోధక చర్య:** గోదాం ఇన్సులేషన్ మెరుగుపరచండి మరియు చల్లని సమయాల్లో మాత్రమే వెంటిలేషన్ చేయండి.",
                    f"3. **పర్యవేక్షణ:** ప్రతి 30–45 నిమిషాలకు ఉష్ణోగ్రతను తనిఖీ చేసి సురక్షిత పరిమితిలో ఉందని నిర్ధారించుకోండి.",
                    "",
                    f"**Risks to consider:** అధిక ఉష్ణోగ్రత వల్ల పురుగులు, ఎంజైమ్ చర్యలు పెరిగి నిల్వ కాలం తగ్గుతుంది.",
                    "",
                    f"**Data used:** సెన్సార్ టెలిమెట్రీ & ICAR సురక్షిత నిల్వ ప్రమాణాలు.",
                ]
            else:
                lines = [
                    f"**Recommendation:** Immediate corrective cooling and ventilation required for {crop_name}.",
                    "",
                    f"**Why:** Current measured storage temperature is **{t}°C**, which exceeds the verified ICAR safe ceiling of **{t_max}°C** (safe range: **{t_min}°C–{t_max}°C**).",
                    "",
                    f"**What to do next:**",
                    f"1. **Immediate action:** {alert_action}",
                    f"2. **Preventive step:** Keep aeration vents open during cooler night/early morning hours (15°C–20°C ambient) and install reflective rooftop thatch.",
                    f"3. **When to check again:** Take a fresh sensor measurement in 3 hours to confirm internal granary temperature is declining.",
                    "",
                    f"**Risks to consider:** Temperatures above {t_max}°C accelerate grain respiration, cause dry matter shrinkage, and incubate storage insect pests (weevils and borers).",
                    "",
                    f"**Data used:** Verified ICAR Post-Harvest Standards for {crop_name} & Live Sensor Telemetry.",
                ]
            return "\n".join(lines), False

        # 4. Traditional Pest & Preservation Guidance Intent
        if rag:
            top_rag = rag[0]
            lines = [
                f"**Recommendation:** Implement verified traditional neem deterrence method for {crop_name}.",
                "",
                f"**Why:** Natural botanical repellents deter storage weevils (Sitophilus oryzae / Rhyzopertha dominica) without toxic chemical pesticide residues.",
                "",
                f"**What to do next:**",
                f"1. Dry fresh neem leaves in the shade until crispy (2–3 days).",
                f"2. Mix dried leaves at 2% by weight (20 kg shade-dried leaves per 1,000 kg grain) throughout the storage stack.",
                f"3. Seal storage container tightly to maintain hermetic conditions and exclude ambient moisture.",
                "",
                f"**Risks to consider:** Ensure leaves are fully shade-dried before mixing; damp leaves will introduce mold and localized hot spots.",
                "",
                f"**Data used:** {top_rag.title} ({top_rag.source_name}).",
            ]
            return "\n".join(lines), False

        # 5. Default General Farming Consultation
        lines = [
            f"**Recommendation:** Maintain standard ICAR post-harvest preservation practices for {crop_name}.",
            "",
            f"**Why:** Verified agronomic standards require maintaining storage temperature between **{t_min}°C–{t_max}°C** and humidity between **{rh_min}%–{rh_max}%** to prevent insect proliferation.",
            "",
            f"**What to do next:**",
            f"1. Verify that storage bags are stacked on wooden pallets at least 15 cm above ground to prevent moisture migration.",
            f"2. Ventilate the granary during dry mid-day hours when outdoor ambient humidity is below 60%.",
            f"3. Inspect bags weekly for localized heating or insect dust.",
            "",
            f"**Risks to consider:** Ambient relative humidity above {rh_max}% leads to grain moisture re-absorption and mold growth.",
            "",
            f"**Data used:** {crop_prof.get('source', 'ICAR Post-Harvest Storage Standards')}.",
        ]
        return "\n".join(lines), False

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
