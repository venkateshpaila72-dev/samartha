"""Farmer Diary Schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class DiaryEntryCreate(BaseModel):
    batch_id: str
    observation_text: str = Field(min_length=2)
    observation_category: str = Field(
        default="general_inspection",
        description="smell, insect_activity, moisture_leakage, color_change, caking, temperature_hotspot, general_inspection",
    )
    photo_urls: list[str] = Field(default_factory=list)
    voice_recording_url: Optional[str] = None
    voice_transcript: Optional[str] = None
    severity_assessment: str = Field(default="normal", pattern="^(normal|minor_concern|urgent_attention)$")
    provenance: str = Field(default="farmer_visual_report", pattern="^(farmer_visual_report|voice_transcription|field_scout)$")


class DiaryEntryUpdate(BaseModel):
    observation_text: Optional[str] = None
    observation_category: Optional[str] = None
    severity_assessment: Optional[str] = None
    photo_urls: Optional[list[str]] = None


class DiaryEntryOut(BaseModel):
    entry_id: str
    batch_id: str
    farmer_id: str
    observation_text: str
    observation_category: str
    photo_urls: list[str] = Field(default_factory=list)
    voice_recording_url: Optional[str] = None
    voice_transcript: Optional[str] = None
    severity_assessment: str
    provenance: str
    ai_advisory_analysis: Optional[str] = None
    created_at: str
    updated_at: str
