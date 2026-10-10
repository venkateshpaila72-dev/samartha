"""Azure Speech Services Client for FarmShield.
Transcribes voice diary audio recordings using Microsoft Azure Speech Cognitive Services,
with fallback to Groq Whisper for browser audio formats (WebM/Opus) and multilingual support.
"""

import logging
import re
from typing import Optional, Tuple
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AzureSpeechClient:
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
    def is_configured(cls) -> bool:
        key = settings.AZURE_SPEECH_KEY.strip()
        region = settings.AZURE_SPEECH_REGION.strip()
        return bool(key and not key.startswith("your_") and region)

    @staticmethod
    def clean_text_for_speech(text: str) -> str:
        """Strips markdown syntax, table rows, URLs, raw JSON, and citations for clean TTS."""
        if not text:
            return ""

        # Remove markdown code blocks and raw JSON
        cleaned = re.sub(r"```[\s\S]*?```", " ", text)
        cleaned = re.sub(r"\{[\s\S]*?\}", " ", cleaned)

        # Remove markdown table rows (| ... |)
        cleaned = re.sub(r"^\|.*\|$", " ", cleaned, flags=re.MULTILINE)

        # Remove Referenced Sources / Citations section at the bottom
        cleaned = re.sub(r"(?i)\n*###?\s*Referenced Sources[\s\S]*$", "", cleaned)
        cleaned = re.sub(r"(?i)\n*Referenced Sources:[\s\S]*$", "", cleaned)

        # Remove URLs
        cleaned = re.sub(r"https?://\S+", "", cleaned)

        # Remove markdown bold/italics/headings/bullet symbols
        cleaned = re.sub(r"[*#_`~>\[\]]", " ", cleaned)

        # Clean multiple spaces and newlines
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Limit to 3500 characters on sentence boundaries for Azure SSML safety
        if len(cleaned) > 3500:
            truncated = cleaned[:3500]
            last_period = max(truncated.rfind(". "), truncated.rfind("। "), truncated.rfind("? "), truncated.rfind("! "))
            if last_period > 1000:
                cleaned = truncated[:last_period + 1]
            else:
                cleaned = truncated + "."

        return cleaned

    @classmethod
    async def transcribe_audio(
        cls,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        language: str = "en-IN",
    ) -> Tuple[str, float]:
        """Transcribes raw audio bytes with Azure Speech API, falling back to Groq Whisper
        if Azure STT encounters format or recognition issues.
        Returns (transcript_text, confidence_score).
        """
        short_lang = language.split("-")[0].lower() if language else "en"

        # 1. Attempt Azure Speech STT if configured
        if cls.is_configured():
            api_key = settings.AZURE_SPEECH_KEY.strip()
            region = settings.AZURE_SPEECH_REGION.strip()
            url = f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={language}&format=detailed"

            headers = {
                "Ocp-Apim-Subscription-Key": api_key,
                "Content-Type": content_type or "audio/wav",
            }

            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    resp = await client.post(url, headers=headers, content=audio_bytes)
                    if resp.status_code == 200:
                        data = resp.json()
                        status = data.get("RecognitionStatus")
                        if status == "Success":
                            display_text = data.get("DisplayText", "").strip()
                            nbest = data.get("NBest", [])
                            confidence = float(nbest[0].get("Confidence", 0.90)) if nbest else 0.90
                            if display_text:
                                return display_text, round(confidence, 2)
                        logger.info("Azure Speech returned status %s; trying Whisper fallback", status)
                    else:
                        logger.warning("Azure Speech STT error status %d: %s", resp.status_code, resp.text[:200])
            except Exception as exc:
                logger.warning("Azure Speech transcription encountered error: %s; falling back", exc)

        # 2. Resilient Fallback: Groq Whisper (natively supports WebM, Opus, WAV, MP3, multilingual)
        if settings.GROQ_API_KEY:
            try:
                whisper_url = "https://api.groq.com/openai/v1/audio/transcriptions"
                w_headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY.strip()}"}
                
                # Determine extension based on content_type
                ext = "wav"
                if "webm" in content_type:
                    ext = "webm"
                elif "ogg" in content_type:
                    ext = "ogg"
                elif "mp4" in content_type or "m4a" in content_type:
                    ext = "m4a"
                elif "mpeg" in content_type or "mp3" in content_type:
                    ext = "mp3"

                files = {"file": (f"audio.{ext}", audio_bytes, content_type or "audio/wav")}
                form_data = {
                    "model": "whisper-large-v3",
                    "language": short_lang,
                }

                async with httpx.AsyncClient(timeout=30.0) as client:
                    w_resp = await client.post(whisper_url, headers=w_headers, files=files, data=form_data)
                    if w_resp.status_code == 200:
                        res_data = w_resp.json()
                        transcript = res_data.get("text", "").strip()
                        if transcript:
                            return transcript, 0.95
                    else:
                        logger.warning("Groq Whisper STT returned status %d: %s", w_resp.status_code, w_resp.text[:200])
            except Exception as w_exc:
                logger.warning("Groq Whisper transcription failed: %s", w_exc)

        raise ValueError("Could not recognize speech from audio. Please speak clearly into the microphone.")

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

        # Clean text for spoken speech (removes tables, URLs, raw metadata, citations)
        cleaned_text = cls.clean_text_for_speech(text)
        if not cleaned_text:
            cleaned_text = "Here is the information from FarmShield."

        # Escape XML characters for SSML
        escaped_text = (
            cleaned_text.replace("&", "&amp;")
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

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=headers, content=ssml.encode("utf-8"))
            if resp.status_code == 200:
                return resp.content
            else:
                raise RuntimeError(f"Azure TTS endpoint returned status {resp.status_code}: {resp.text}")

