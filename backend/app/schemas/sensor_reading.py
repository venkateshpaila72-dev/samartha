"""Sensor Reading Schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class SensorReadingCreate(BaseModel):
    batch_id: str
    temperature_c: float = Field(ge=-20.0, le=70.0, description="Ambient or grain temperature in Celsius")
    relative_humidity_percent: float = Field(ge=0.0, le=100.0, description="Ambient relative humidity in %")
    crop_moisture_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    co2_ppm: Optional[float] = Field(default=None, ge=0.0, le=10000.0)
    sensor_id: str = "manual_entry_01"
    provenance: str = Field(default="manual", pattern="^(hardware_sensor|manual|simulated)$")
    timestamp: Optional[str] = None
    notes: Optional[str] = None


class SensorReadingOut(BaseModel):
    reading_id: str
    batch_id: str
    temperature_c: float
    relative_humidity_percent: float
    crop_moisture_percent: Optional[float] = None
    co2_ppm: Optional[float] = None
    sensor_id: str
    provenance: str  # hardware_sensor, manual, simulated
    timestamp: str
    is_temperature_in_range: bool
    is_humidity_in_range: bool
    notes: Optional[str] = None


class MonitoringSummaryOut(BaseModel):
    batch_id: str
    crop_name: str
    current_temperature_c: Optional[float] = None
    current_humidity_percent: Optional[float] = None
    current_moisture_percent: Optional[float] = None
    target_temperature_min_c: float
    target_temperature_max_c: float
    target_humidity_min_percent: float
    target_humidity_max_percent: float
    target_moisture_percent: float
    last_reading_time: Optional[str] = None
    reading_provenance: Optional[str] = None
    sensor_freshness_status: str  # online, stale, offline, no_data
    risk_level: str  # normal, moderate, high, critical
    active_alerts: list[dict] = Field(default_factory=list)
    recent_readings: list[SensorReadingOut] = Field(default_factory=list)
