
"""Azure Translator client with caching and safe fallback behavior."""

import logging
from typing import Iterable

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "en", "te", "hi", "mr", "bn", "ta", "kn", "gu"
}

CACHE = {}
MAX_CACHE_ITEMS = 10000

FALLBACK_DICTIONARIES = {
    "hi": {
        "Temperature": "तापमान",
        "Relative Humidity": "सापेक्ष आर्द्रता",
        "Storage Advisory": "भंडारण सलाह",
        "Safe Limit": "सुरक्षित सीमा",
        "Action Required": "कार्रवाई आवश्यक",
    },
    "te": {
        "Temperature": "ఉష్ణోగ్రత",
        "Relative Humidity": "సాపేక్ష తేమ",
        "Storage Advisory": "నిల్వ సలహా",
        "Safe Limit": "సురక్షిత పరిమితి",
        "Action Required": "తక్షణ చర్య అవసరం",
    },
    "mr": {
        "Temperature": "तापमान",
        "Relative Humidity": "सापेक्ष आर्द्रता",
        "Storage Advisory": "साठवण सल्ला",
        "Safe Limit": "सुरक्षित मर्यादा",
    },
    "bn": {
        "Temperature": "তাপমাত্রা",
        "Relative Humidity": "আপেক্ষিক আর্দ্রতা",
        "Storage Advisory": "সংরক্ষণ পরামর্শ",
        "Safe Limit": "নিরাপদ সীমা",
    },
    "ta": {
        "Temperature": "வெப்பநிலை",
        "Relative Humidity": "ஈரப்பதம்",
        "Storage Advisory": "சேமிப்பு ஆலோசனை",
        "Safe Limit": "பாதுகாப்பான வரம்பு",
    },
    "kn": {
        "Temperature": "ತಾಪಮಾನ",
        "Relative Humidity": "ಆರ್ದ್ರತೆ",
        "Storage Advisory": "ಸಂಗ್ರಹ ಸಲಹೆ",
        "Safe Limit": "ಸುರಕ್ಷಿತ ಮಿತಿ",
    },
    "gu": {
        "Temperature": "તાપમાન",
        "Relative Humidity": "સાપેક્ષ ભેજ",
        "Storage Advisory": "સંગ્રહ સલાહ",
        "Safe Limit": "સુરક્ષિત મર્યાદા",
    },
}


class AzureTranslatorClient:
    @classmethod
    async def translate_many(
        cls,
        texts: Iterable[str],
        target_lang: str,
        source_lang: str = "en",
    ) -> list[str]:
        original = list(texts)

        if target_lang not in SUPPORTED_LANGUAGES:
            target_lang = "en"

        if source_lang not in SUPPORTED_LANGUAGES:
            source_lang = "en"

        if target_lang == source_lang or target_lang == "en":
            return original

        results = [None] * len(original)
        missing = []
        missing_keys = []

        for index, text in enumerate(original):
            if not isinstance(text, str) or not text.strip():
                results[index] = text
                continue

            key = (source_lang, target_lang, text)

            if key in CACHE:
                results[index] = CACHE[key]
            elif key not in missing_keys:
                missing_keys.append(key)
                missing.append(text)

        translations = {}

        api_key = settings.AZURE_TRANSLATOR_KEY.strip()
        endpoint = settings.AZURE_TRANSLATOR_ENDPOINT.strip().rstrip("/")
        region = settings.AZURE_TRANSLATOR_REGION.strip()

        if missing and api_key and not api_key.startswith("your_"):
            try:
                url = (
                    f"{endpoint}/translate"
                    f"?api-version=3.0&from={source_lang}&to={target_lang}"
                )

                headers = {
                    "Ocp-Apim-Subscription-Key": api_key,
                    "Content-Type": "application/json",
                }

                if region:
                    headers["Ocp-Apim-Subscription-Region"] = region

                async with httpx.AsyncClient(timeout=15.0) as client:
                    # Azure Translator accepts up to 100 text objects per request.
                    for offset in range(0, len(missing), 100):
                        chunk = missing[offset:offset + 100]
                        response = await client.post(
                            url,
                            headers=headers,
                            json=[{"Text": text} for text in chunk],
                        )
                        response.raise_for_status()

                        payload = response.json()
                        for local_index, item in enumerate(payload):
                            global_index = offset + local_index
                            translated = (
                                item.get("translations", [{}])[0].get(
                                    "text", missing[global_index]
                                )
                            )
                            translations[missing_keys[global_index]] = translated

            except Exception as exc:
                logger.warning(
                    "Azure Translator failed; using fallback/original text: %s",
                    exc,
                )

        for key in missing_keys:
            translated = translations.get(key)

            if translated is None:
                translated = key[2]
                fallback = FALLBACK_DICTIONARIES.get(target_lang, {})

                for english, local in fallback.items():
                    translated = translated.replace(english, local)

            if len(CACHE) >= MAX_CACHE_ITEMS:
                CACHE.clear()

            CACHE[key] = translated

        final_results = []

        for index, text in enumerate(original):
            if results[index] is not None:
                final_results.append(results[index])
                continue

            key = (source_lang, target_lang, text)
            final_results.append(CACHE.get(key, text))

        return final_results

    @classmethod
    async def translate_text(
        cls,
        text: str,
        target_lang: str,
        source_lang: str = "en",
    ) -> str:
        result = await cls.translate_many(
            [text],
            target_lang,
            source_lang,
        )
        return result[0]
