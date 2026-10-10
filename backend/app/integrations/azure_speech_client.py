"""Azure Speech Services Client for FarmShield.
Provides Speech-to-Text (STT) and Text-to-Speech (TTS) using Microsoft Azure Cognitive Services.
"""

import logging
from typing import Optional, Tuple
from xml.sax.saxutils import escape as xml_escape
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Canonical Azure Neural Voices for Indian languages
VOICE_MAPPING: dict[str, tuple[str, str]] = {
    "en": ("en-IN", "en-IN-NeerjaNeural"),
    "hi": ("hi-IN", "hi-IN-SwaraNeural"),
    "te": ("te-IN", "te-IN-ShrutiNeural"),
    "ta": ("ta-IN", "ta-IN-PallaviNeural"),
    "kn": ("kn-IN", "kn-IN-SapnaNeural"),
    "mr": ("mr-IN", "mr-IN-AarohiNeural"),
    "bn": ("bn-IN", "bn-IN-TanishaaNeural"),
    "gu": ("gu-IN", "gu-IN-DhwaniNeural"),
    "pa": ("pa-IN", "pa-IN-OjasNeural"),
}


class AzureSpeechClient:
    @classmethod
    def is_configured(cls) -> bool:
        key = settings.AZURE_SPEECH_KEY.strip()
        region = settings.AZURE_SPEECH_REGION.strip()
        return bool(key and not key.startswith("your_") and region)

    @classmethod
    async def transcribe_audio(
        cls,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        language: str = "en-IN",
    ) -> Tuple[str, float]:
        """Transcribes raw audio bytes using Azure Speech STT REST API.
        Returns (transcript_text, confidence_score).
        """
        if not cls.is_configured():
            if settings.APP_ENV == "test":
                return "Simulated audio transcription for storage inspection.", 0.95
            raise RuntimeError("Azure Speech Services credentials are not configured in environment.")

        api_key = settings.AZURE_SPEECH_KEY.strip()
        region = settings.AZURE_SPEECH_REGION.strip()
        url = f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={language}&format=detailed"

        # Azure STT requires specific Content-Type specification for PCM WAV
        effective_content_type = content_type
        if "wav" in content_type.lower():
            effective_content_type = "audio/wav; codecs=audio/pcm; samplerate=16000"
        elif "ogg" in content_type.lower():
            effective_content_type = "audio/ogg; codecs=opus"
        elif "webm" in content_type.lower():
            effective_content_type = "audio/webm; codecs=opus"

        headers = {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": effective_content_type,
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, headers=headers, content=audio_bytes)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("RecognitionStatus")
                if status == "Success":
                    display_text = data.get("DisplayText", "")
                    nbest = data.get("NBest", [])
                    confidence = float(nbest[0].get("Confidence", 0.90)) if nbest else 0.90
                    return display_text, round(confidence, 2)
                elif status in ("InitialSilenceTimeout", "NoMatch", None) or data.get("Duration", 0) == 0:
                    return "", 0.0
                else:
                    raise ValueError(f"Speech recognition status: {status}")
            else:
                raise RuntimeError(f"Azure Speech endpoint returned status {resp.status_code}: {resp.text}")

    @classmethod
    async def synthesize_speech(
        cls,
        text: str,
        language: str = "en",
        voice_name: Optional[str] = None,
    ) -> Tuple[bytes, str, str]:
        """Synthesizes text into high-fidelity neural MP3 speech using Azure Cognitive Services.
        Returns (audio_bytes, locale_code, voice_name).
        """
        if not cls.is_configured():
            if settings.APP_ENV == "test":
                return b"ID3_MOCK_MP3_AUDIO_BYTES", "en-IN", "en-IN-NeerjaNeural"
            raise RuntimeError("Azure Speech Services credentials are not configured in environment.")

        # Determine locale and voice
        clean_lang = (language or "en").lower().split("-")[0]
        default_locale, default_voice = VOICE_MAPPING.get(clean_lang, ("en-IN", "en-IN-NeerjaNeural"))
        chosen_voice = voice_name or default_voice
        chosen_locale = default_locale

        api_key = settings.AZURE_SPEECH_KEY.strip()
        region = settings.AZURE_SPEECH_REGION.strip()
        url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

        safe_text = xml_escape(text.strip())
        ssml = (
            f"<speak version='1.0' xml:lang='{chosen_locale}'>"
            f"<voice xml:lang='{chosen_locale}' name='{chosen_voice}'>"
            f"{safe_text}"
            f"</voice>"
            f"</speak>"
        )

        headers = {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
            "User-Agent": "FarmShield",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=headers, content=ssml.encode("utf-8"))
            if resp.status_code == 200:
                return resp.content, chosen_locale, chosen_voice
            else:
                raise RuntimeError(
                    f"Azure Speech TTS returned status {resp.status_code}: {resp.text}"
                )
