"""Speech-to-text transcription and text-to-speech synthesis endpoints."""

import base64
import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user
from app.integrations.azure_speech_client import AzureSpeechClient
from app.schemas.common import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Speech & Voice"])

ALLOWED_AUDIO_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/ogg",
    "audio/webm",
    "audio/mpeg",
    "audio/mp4",
    "audio/m4a",
    "application/octet-stream",
}

MAX_AUDIO_SIZE = 15 * 1024 * 1024

SUPPORTED_SPEECH_LANGUAGES = {
    "hi": "hi-IN",
    "te": "te-IN",
    "ta": "ta-IN",
    "kn": "kn-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "gu": "gu-IN",
    "pa": "pa-IN",
    "en": "en-IN",
}


class TranscriptionResponse(BaseModel):
    transcript: str
    confidence: float
    language: str


class SpeechSynthesisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000, description="Text to convert to speech")
    language: Optional[str] = Field(default="en", description="Target language code (en, hi, te, etc.)")
    voice_name: Optional[str] = Field(default=None, description="Optional Azure voice identifier")


class SpeechSynthesisResponse(BaseModel):
    audio_base64: str
    media_type: str = "audio/mpeg"
    language: str
    voice_name: str


@router.post(
    "/speech/transcribe",
    response_model=APIResponse[TranscriptionResponse],
)
async def transcribe_audio_file(
    file: Optional[UploadFile] = File(None),
    current_user=Depends(get_current_user),
):
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An audio file must be provided for speech transcription.",
        )

    raw_content_type = (file.content_type or "").lower()
    base_content_type = raw_content_type.split(";")[0].strip()

    if base_content_type and base_content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unsupported audio format '{raw_content_type}'. "
                "Please upload WAV, OGG, or WebM audio."
            ),
        )

    audio_bytes = await file.read()

    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded audio file is empty.",
        )

    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file exceeds the maximum allowed size of 15 MB.",
        )

    if not AzureSpeechClient.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech transcription service is not configured.",
        )

    preferred_language = (
        current_user.get("preferred_language", "en")
        if isinstance(current_user, dict)
        else getattr(current_user, "preferred_language", "en")
    )

    lang_code = SUPPORTED_SPEECH_LANGUAGES.get(
        preferred_language,
        "en-IN",
    )

    try:
        transcript, confidence = await AzureSpeechClient.transcribe_audio(
            audio_bytes,
            content_type=raw_content_type or "audio/wav",
            language=lang_code,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Audio could not be transcribed: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Azure Speech transcription failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Speech transcription service failed.",
        ) from exc

    return APIResponse(
        success=True,
        message="Audio transcribed successfully.",
        data=TranscriptionResponse(
            transcript=transcript,
            confidence=confidence,
            language=lang_code,
        ),
    )


@router.post(
    "/speech/synthesize",
    response_model=APIResponse[SpeechSynthesisResponse],
)
async def synthesize_speech_endpoint(
    payload: SpeechSynthesisRequest,
    current_user=Depends(get_current_user),
):
    if not payload.text or not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Text must not be empty.",
        )

    preferred_language = payload.language or (
        current_user.get("preferred_language", "en")
        if isinstance(current_user, dict)
        else getattr(current_user, "preferred_language", "en")
    )

    try:
        audio_bytes, locale, voice_name = await AzureSpeechClient.synthesize_speech(
            text=payload.text.strip(),
            language=preferred_language,
            voice_name=payload.voice_name,
        )
    except Exception as exc:
        logger.exception("Azure Speech synthesis failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Speech synthesis service failed.",
        ) from exc

    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")

    return APIResponse(
        success=True,
        message="Speech synthesized successfully.",
        data=SpeechSynthesisResponse(
            audio_base64=audio_b64,
            media_type="audio/mpeg",
            language=locale,
            voice_name=voice_name,
        ),
    )
