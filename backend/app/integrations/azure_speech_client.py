"""Azure Speech Services Client for FarmShield.
Transcribes voice diary audio recordings using Microsoft Azure Speech Cognitive Services.
"""

import logging
from typing import Optional, Tuple
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AzureSpeechClient:
    @classmethod
    def is_configured(cls) -> bool:
        key = settings.AZURE_SPEECH_KEY.strip()
        region = settings.AZURE_SPEECH_REGION.strip()
        return bool(key and not key.startswith("your_") and region)

    @classmethod
    async def transcribe_audio(cls, audio_bytes: bytes, content_type: str = "audio/wav", language: str = "en-IN") -> Tuple[str, float]:
        """Transcribes raw audio bytes with Azure Speech API.
        Returns (transcript_text, confidence_score).
        Raises RuntimeError or ValueError on configuration/service failure.
        """
        if not cls.is_configured():
            raise RuntimeError("Azure Speech Services credentials are not configured in environment.")

        api_key = settings.AZURE_SPEECH_KEY.strip()
        region = settings.AZURE_SPEECH_REGION.strip()
        url = f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={language}&format=detailed"

        headers = {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": content_type,
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, headers=headers, content=audio_bytes)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("RecognitionStatus")
                if status == "Success":
                    display_text = data.get("DisplayText", "")
                    # Extract confidence if available in NBest
                    nbest = data.get("NBest", [])
                    confidence = float(nbest[0].get("Confidence", 0.90)) if nbest else 0.90
                    return display_text, round(confidence, 2)
                else:
                    raise ValueError(f"Speech recognition could not interpret audio: {status}")
    VOICE_MAP = {
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

    @classmethod
    async def synthesize_speech(cls, text: str, language: str = "en") -> bytes:
        """Synthesizes text into MP3 audio bytes using Azure Cognitive Services Text-to-Speech REST API.
        Selects neural voice matching the requested language.
        """
        if not cls.is_configured():
            raise RuntimeError("Azure Speech Services credentials are not configured in environment.")

        api_key = settings.AZURE_SPEECH_KEY.strip()
        region = settings.AZURE_SPEECH_REGION.strip()
        url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

        lang_code = (language or "en").lower().split("-")[0]
        voice_lang, voice_name = cls.VOICE_MAP.get(lang_code, ("en-IN", "en-IN-NeerjaNeural"))

        # Clean text for SSML (escape XML characters)
        escaped_text = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

        ssml = (
            f"<speak version='1.0' xml:lang='{voice_lang}'>"
            f"<voice xml:lang='{voice_lang}' name='{voice_name}'>"
            f"{escaped_text}"
            f"</voice>"
            f"</speak>"
        )

        headers = {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
            "User-Agent": "FarmShield-TTS",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, content=ssml.encode("utf-8"))
            if resp.status_code == 200:
                return resp.content
            else:
                raise RuntimeError(f"Azure TTS endpoint returned status {resp.status_code}: {resp.text}")
