"""Multilingual Translation Endpoints."""

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.integrations.azure_translator_client import AzureTranslatorClient
from app.schemas.common import APIResponse

router = APIRouter(tags=["Translation"])


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1)
    target_language: str = Field(pattern="^(hi|te|ta|kn|mr|bn|pa|en)$")
    source_language: str = "en"


class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    target_language: str
    source_language: str


@router.post("/translation", response_model=APIResponse[TranslationResponse])
async def translate_text(
    payload: TranslationRequest,
    current_user: dict = Depends(get_current_user),
):
    translated = await AzureTranslatorClient.translate_text(
        text=payload.text,
        target_lang=payload.target_language,
        source_lang=payload.source_language,
    )
    return APIResponse(
        success=True,
        message="Text translated successfully.",
        data=TranslationResponse(
            original_text=payload.text,
            translated_text=translated,
            target_language=payload.target_language,
            source_language=payload.source_language,
        ),
    )
