"""Storage Alert and Notification Schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class StorageAlertOut(BaseModel):
    alert_id: str
    batch_id: str
    crop_name: str
    condition_type: str  # temperature_high, temperature_low, humidity_high, humidity_low, moisture_high, sensor_offline
    severity: str  # info, warning, critical
    measured_value: Optional[float] = None
    target_threshold: Optional[float] = None
    unit: str
    message: str
    recommended_action: str
    status: str  # active, acknowledged, resolved
    whatsapp_notified: bool = False
    created_at: str
    resolved_at: Optional[str] = None


class AlertStatusUpdate(BaseModel):
    status: str = Field(pattern="^(acknowledged|resolved)$")
    resolution_note: Optional[str] = None


class NotificationPreferencesUpdate(BaseModel):
    enable_whatsapp_alerts: bool = True
    whatsapp_phone_number: Optional[str] = None
    alert_severity_threshold: str = "warning"  # warning, critical
