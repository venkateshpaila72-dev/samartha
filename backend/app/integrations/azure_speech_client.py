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
            else:
                raise RuntimeError(f"Azure Speech endpoint returned status {resp.status_code}: {resp.text}")
