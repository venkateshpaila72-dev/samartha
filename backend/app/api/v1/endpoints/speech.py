"""Speech-to-text Transcription Endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
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

MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10 MB


class TranscriptionResponse(BaseModel):
    transcript: str
    confidence: float
    language: str


@router.post("/speech/transcribe", response_model=APIResponse[TranscriptionResponse])
async def transcribe_audio_file(
    file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
):
    if not file:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An audio file must be provided for speech transcription.",
        )

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported audio format '{content_type}'. Please upload WAV, OGG, or WebM audio.",
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
            detail=f"Audio file exceeds maximum allowed size of {MAX_AUDIO_SIZE // (1024 * 1024)} MB.",
        )

    if not AzureSpeechClient.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech transcription service is currently not configured or unavailable.",
        )

    lang = current_user.get("preferred_language", "en")
    lang_code = f"{lang}-IN" if lang in ["hi", "te", "ta", "kn", "mr", "bn", "pa"] else "en-IN"

    try:
        transcript, confidence = await AzureSpeechClient.transcribe_audio(
            audio_bytes,
            content_type=content_type or "audio/wav",
            language=lang_code,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Audio could not be transcribed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Azure Speech transcription failure: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Speech transcription service error: {str(e)}",
        )

    return APIResponse(
        success=True,
        message="Audio transcribed successfully.",
        data=TranscriptionResponse(
            transcript=transcript,
            confidence=confidence,
            language=lang_code,
        ),
    )
