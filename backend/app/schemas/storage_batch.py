"""Storage Batch Schemas."""

from typing import Any, Optional
from pydantic import BaseModel, Field

from app.schemas.crop_profile import CropProfileOut


class StorageBatchCreate(BaseModel):
    crop_id: str
    custom_batch_name: str = Field(min_length=2)
    quantity_kg: float = Field(gt=0)
    harvest_date: str
    storage_start_date: str
    storage_structure_type: str = Field(default="Warehouse")
    storage_location: str = "Farm Main Granary"
    initial_crop_condition: str = "Good, clean, healthy harvest"
    notes: Optional[str] = None


class StorageBatchUpdate(BaseModel):
    custom_batch_name: Optional[str] = None
    quantity_kg: Optional[float] = None
    storage_structure_type: Optional[str] = None
    storage_location: Optional[str] = None
    initial_crop_condition: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class LatestReadingSummary(BaseModel):
    temperature_c: Optional[float] = None
    relative_humidity_percent: Optional[float] = None
    crop_moisture_percent: Optional[float] = None
    co2_ppm: Optional[float] = None
    timestamp: Optional[str] = None
    is_temperature_safe: Optional[bool] = None
    is_humidity_safe: Optional[bool] = None
    overall_status: str = "unknown"  # safe, warning, critical, unknown


class StorageBatchOut(BaseModel):
    batch_id: str
    farmer_id: str
    crop_id: str
    custom_batch_name: str
    quantity_kg: float
    harvest_date: str
    storage_start_date: str
    storage_structure_type: str
    storage_location: str
    initial_crop_condition: str
    status: str = "active"  # active, harvested, sold, closed
    notes: Optional[str] = None
    created_at: str
    updated_at: str
    crop_profile: Optional[CropProfileOut] = None
    latest_reading: Optional[LatestReadingSummary] = None
    active_alerts_count: int = 0
