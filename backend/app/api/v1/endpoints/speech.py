"""Speech-to-text Transcription Endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.integrations.azure_speech_client import AzureSpeechClient
from app.schemas.common import APIResponse

router = APIRouter(tags=["Speech & Voice"])


class TranscriptionResponse(BaseModel):
    transcript: str
    confidence: float = 0.95
    language: str = "en-IN"


@router.post("/speech/transcribe", response_model=APIResponse[TranscriptionResponse])
async def transcribe_audio_file(
    file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
):
    audio_bytes = b""
    if file:
        audio_bytes = await file.read()

    lang = current_user.get("preferred_language", "en")
    lang_code = f"{lang}-IN" if lang in ["hi", "te", "ta", "kn"] else "en-IN"

    transcript = await AzureSpeechClient.transcribe_audio(audio_bytes, language=lang_code)

    return APIResponse(
        success=True,
        message="Audio transcribed successfully.",
        data=TranscriptionResponse(transcript=transcript, confidence=0.95, language=lang_code),
    )
