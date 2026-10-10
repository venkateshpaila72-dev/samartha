
"""API endpoints for translating dynamic text using Azure Translator."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.api.dependencies import get_current_user
from app.integrations.azure_translator_client import AzureTranslatorClient
from app.schemas.common import APIResponse

router = APIRouter(tags=["Translation"])

SUPPORTED_LANGUAGE_PATTERN = r"^(en|te|hi|mr|bn|ta|kn|gu)$"


class TranslationRequest(BaseModel):
<<<<<<< HEAD
    text: str = Field(min_length=1, max_length=5000)
    target_language: str = Field(pattern=SUPPORTED_LANGUAGE_PATTERN)
    source_language: str = Field(
        default="en",
        pattern=SUPPORTED_LANGUAGE_PATTERN,
    )
=======
    text: str = Field(min_length=1)
    target_language: str = Field(pattern="^(hi|te|ta|kn|mr|bn|pa|en)$")
    source_language: str = Field(default="en", pattern="^(hi|te|ta|kn|mr|bn|pa|en)$")
>>>>>>> e593938731cffe4d25d52e76603c5c3a00419be2


class BatchTranslationRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=100)
    target_language: str = Field(pattern=SUPPORTED_LANGUAGE_PATTERN)
    source_language: str = Field(
        default="en",
        pattern=SUPPORTED_LANGUAGE_PATTERN,
    )

    @field_validator("texts")
    @classmethod
    def validate_text_lengths(cls, values):
        if any(len(value) > 5000 for value in values):
            raise ValueError("Each text must be 5000 characters or fewer")
        return values


class TranslationResult(BaseModel):
    original_text: str
    translated_text: str
    target_language: str
    source_language: str


class BatchTranslationResult(BaseModel):
    translated_texts: list[str]
    target_language: str
    source_language: str


@router.post(
    "/translation",
    response_model=APIResponse[TranslationResult],
)
async def translate_text(
    payload: TranslationRequest,
    current_user=Depends(get_current_user),
):
    translated = await AzureTranslatorClient.translate_text(
        payload.text,
        payload.target_language,
        payload.source_language,
    )

    return APIResponse(
        success=True,
        message="Text translated successfully.",
        data=TranslationResult(
            original_text=payload.text,
            translated_text=translated,
            target_language=payload.target_language,
            source_language=payload.source_language,
        ),
    )


@router.post(
    "/translation/batch",
    response_model=APIResponse[BatchTranslationResult],
)
async def translate_batch(
    payload: BatchTranslationRequest,
    current_user=Depends(get_current_user),
):
    translated = await AzureTranslatorClient.translate_many(
        payload.texts,
        payload.target_language,
        payload.source_language,
    )

    return APIResponse(
        success=True,
        message="Texts translated successfully.",
        data=BatchTranslationResult(
            translated_texts=translated,
            target_language=payload.target_language,
            source_language=payload.source_language,
        ),
    )
