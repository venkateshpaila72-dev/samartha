
"""Speech-to-text transcription endpoint."""

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
from pydantic import BaseModel

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
}

MAX_AUDIO_SIZE = 10 * 1024 * 1024

SUPPORTED_SPEECH_LANGUAGES = {
    "hi": "hi-IN",
    "te": "te-IN",
    "ta": "ta-IN",
    "kn": "kn-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "gu": "gu-IN",
    "en": "en-IN",
}


class TranscriptionResponse(BaseModel):
    transcript: str
    confidence: float
    language: str


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

    content_type = (file.content_type or "").lower()

    if content_type and content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unsupported audio format '{content_type}'. "
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
            detail="Audio file exceeds the maximum allowed size of 10 MB.",
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
            content_type=content_type or "audio/wav",
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
