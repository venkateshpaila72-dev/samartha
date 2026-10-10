"""Azure Translator Client with offline multilingual dictionary fallback.
Preserves numbers, units, and safety indicators.
"""

import logging
from typing import Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Essential agricultural glossary for Indian languages
FALLBACK_DICTIONARIES = {
    "hi": {
        "Storage Advisory": "भंडारण सलाह",
        "Temperature": "तापमान",
        "Relative Humidity": "सापेक्ष आर्द्रता",
        "Crop Moisture": "फसल नमी",
        "Paddy (Rice)": "धान (चावल)",
        "Wheat": "गेहूं",
        "Maize": "मक्का",
        "Onion": "प्याज",
        "Potato": "आलू",
        "Safe Limit": "सुरक्षित सीमा",
        "Action Required": "कार्रवाई आवश्यक",
        "Ventilation Guidance": "हवादार बनाने के निर्देश",
        "Critical Alert": "गंभीर चेतावनी",
    },
    "te": {
        "Storage Advisory": "నిల్వ సలహా",
        "Temperature": "ఉష్ణోగ్రత",
        "Relative Humidity": "సాపేక్ష తేమ",
        "Crop Moisture": "ధాన్యపు తేమ",
        "Paddy (Rice)": "వరి (వరి ధాన్యం)",
        "Wheat": "గోధుమలు",
        "Maize": "మొక్కజొన్న",
        "Onion": "ఉల్లిపాయ",
        "Potato": "బంగాళాదుంప",
        "Safe Limit": "సురక్షిత పరిమితి",
        "Action Required": "తక్షణ చర్య అవసరం",
        "Ventilation Guidance": "గాలి ప్రసరణ మార్గదర్శకాలు",
        "Critical Alert": "తీవ్ర హెచ్చరిక",
    },
    "ta": {
        "Storage Advisory": "சேமிப்பு ஆலோசனை",
        "Temperature": "வெப்பநிலை",
        "Relative Humidity": "ஈரப்பதம்",
        "Paddy (Rice)": "நெல்",
        "Wheat": "கோதுமை",
    },
    "kn": {
        "Storage Advisory": "ದಾಸ್ತಾನು ಸಲಹೆ",
        "Temperature": "ತಾಪಮಾನ",
        "Relative Humidity": "ಆರ್ದ್ರತೆ",
        "Paddy (Rice)": "ಭತ್ತ",
        "Wheat": "ಗೋಧಿ",
    },
}


class AzureTranslatorClient:
    @classmethod
    async def translate_text(cls, text: str, target_lang: str, source_lang: str = "en") -> str:
        if target_lang == source_lang or not text:
            return text

        api_key = settings.AZURE_TRANSLATOR_KEY.strip()
        endpoint = settings.AZURE_TRANSLATOR_ENDPOINT.strip()
        region = settings.AZURE_TRANSLATOR_REGION.strip()

        if api_key and not api_key.startswith("your_"):
            try:
                url = f"{endpoint}/translate?api-version=3.0&to={target_lang}"
                headers = {
                    "Ocp-Apim-Subscription-Key": api_key,
                    "Ocp-Apim-Subscription-Region": region,
                    "Content-Type": "application/json",
                }
                body = [{"Text": text}]
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, headers=headers, json=body)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data[0]["translations"][0]["text"]
            except Exception as e:
                logger.warning(f"Azure Translator call failed: {e}")

        # Fallback dictionary matching for key terms
        dictionary = FALLBACK_DICTIONARIES.get(target_lang, {})
        translated = text
        for en_phrase, tr_phrase in dictionary.items():
            translated = translated.replace(en_phrase, tr_phrase)
        return translated
