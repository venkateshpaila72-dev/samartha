"""Crop Storage Profile Schemas."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class CropProfileBase(BaseModel):
    crop_id: str
    crop_name: str
    crop_category: str
    variety: str
    crop_form: str
    region: str = "Pan-India"
    storage_type: str
    intended_storage_duration: str

    recommended_temperature_min_c: float
    recommended_temperature_max_c: float

    recommended_relative_humidity_min_percent: float
    recommended_relative_humidity_max_percent: float

    recommended_crop_moisture_percent: float
    moisture_basis: str

    additional_parameters: dict[str, Any] = Field(default_factory=dict)
    traditional_storage_methods: list[str] = Field(default_factory=list)
    ventilation_guidance: str
    pest_prevention_guidance: str
    spoilage_warning_signs: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)

    source_name: str
    source_url: Optional[str] = None
    source_publication_date: Optional[str] = None
    applicability_notes: Optional[str] = None
    verification_status: str = "verified"
    confidence_or_evidence_status: str = "high_scientific_consensus"

    version: int = 1
    is_active: bool = True


class CropProfileCreate(CropProfileBase):
    pass


class CropProfileUpdate(BaseModel):
    crop_name: Optional[str] = None
    variety: Optional[str] = None
    crop_form: Optional[str] = None
    storage_type: Optional[str] = None
    intended_storage_duration: Optional[str] = None
    recommended_temperature_min_c: Optional[float] = None
    recommended_temperature_max_c: Optional[float] = None
    recommended_relative_humidity_min_percent: Optional[float] = None
    recommended_relative_humidity_max_percent: Optional[float] = None
    recommended_crop_moisture_percent: Optional[float] = None
    moisture_basis: Optional[str] = None
    traditional_storage_methods: Optional[list[str]] = None
    ventilation_guidance: Optional[str] = None
    pest_prevention_guidance: Optional[str] = None
    spoilage_warning_signs: Optional[list[str]] = None
    recommended_actions: Optional[list[str]] = None
    source_name: Optional[str] = None
    verification_status: Optional[str] = None
    is_active: Optional[bool] = None


class CropProfileOut(CropProfileBase):
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CropSelectionQuery(BaseModel):
    crop_name: str
    variety: Optional[str] = None
    crop_form: Optional[str] = None
    storage_type: Optional[str] = None
    intended_storage_duration: Optional[str] = None
    region: Optional[str] = None


class CropSelectionMatchResult(BaseModel):
    matched_profile: CropProfileOut
    match_confidence: str
    applicability_explanation: str
    is_exact_match: bool
    missing_attributes: list[str] = Field(default_factory=list)
