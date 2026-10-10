"""Monitoring Service for FarmShield.
Handles reading ingestion, rule evaluation, alert deduplication, and recovery.
"""

import datetime
import uuid
from typing import Optional

from app.monitoring.rules import evaluate_measurement_rules
from app.repositories.alert_repository import AlertRepository
from app.repositories.crop_repository import CropRepository
from app.repositories.sensor_repository import SensorRepository
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.schemas.sensor_reading import (
    MonitoringSummaryOut,
    SensorReadingCreate,
    SensorReadingOut,
)


class MonitoringService:
    @classmethod
    def ingest_reading(cls, payload: SensorReadingCreate) -> SensorReadingOut:
        batch = StorageBatchRepository.get_by_id(payload.batch_id)
        if not batch:
            raise ValueError(f"Storage batch '{payload.batch_id}' not found.")

        crop_profile = CropRepository.get_by_id(batch["crop_id"])
        if not crop_profile:
            crop_profile = {
                "crop_name": batch.get("custom_batch_name", "Crop"),
                "recommended_temperature_min_c": 15.0,
                "recommended_temperature_max_c": 25.0,
                "recommended_relative_humidity_min_percent": 50.0,
                "recommended_relative_humidity_max_percent": 70.0,
                "recommended_crop_moisture_percent": 12.0,
            }

        t_min = crop_profile.get("recommended_temperature_min_c", 15.0)
        t_max = crop_profile.get("recommended_temperature_max_c", 25.0)
        rh_min = crop_profile.get("recommended_relative_humidity_min_percent", 50.0)
        rh_max = crop_profile.get("recommended_relative_humidity_max_percent", 70.0)

        is_t_safe = t_min <= payload.temperature_c <= t_max
        is_rh_safe = rh_min <= payload.relative_humidity_percent <= rh_max

        now_iso = payload.timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        reading_id = f"read_{uuid.uuid4().hex[:10]}"

        reading_doc = {
            "reading_id": reading_id,
            "batch_id": payload.batch_id,
            "temperature_c": payload.temperature_c,
            "relative_humidity_percent": payload.relative_humidity_percent,
            "crop_moisture_percent": payload.crop_moisture_percent,
            "co2_ppm": payload.co2_ppm,
            "air_velocity_m_s": payload.air_velocity_m_s,
            "pressure_kpa": payload.pressure_kpa,
            "light_lux": payload.light_lux,
            "sensor_id": payload.sensor_id,
            "provenance": payload.provenance,
            "timestamp": now_iso,
            "is_temperature_in_range": is_t_safe,
            "is_humidity_in_range": is_rh_safe,
            "notes": payload.notes,
        }

        # 1. Persist Reading
        SensorRepository.insert(reading_doc)

        # 2. Update Batch Latest Reading Summary
        overall_status = "safe"
        if not is_t_safe or not is_rh_safe:
            overall_status = "warning"
        if payload.temperature_c > (t_max + 4.0) or payload.relative_humidity_percent > (rh_max + 8.0):
            overall_status = "critical"

        StorageBatchRepository.update(
            payload.batch_id,
            {
                "latest_reading": {
                    "temperature_c": payload.temperature_c,
                    "relative_humidity_percent": payload.relative_humidity_percent,
                    "crop_moisture_percent": payload.crop_moisture_percent,
                    "co2_ppm": payload.co2_ppm,
                    "air_velocity_m_s": payload.air_velocity_m_s,
                    "pressure_kpa": payload.pressure_kpa,
                    "light_lux": payload.light_lux,
                    "timestamp": now_iso,
                    "is_temperature_safe": is_t_safe,
                    "is_humidity_safe": is_rh_safe,
                    "overall_status": overall_status,
                },
                "updated_at": now_iso,
            },
        )

        # 3. Evaluate Rule Engine & Manage Alert Transitions
        violations = evaluate_measurement_rules(
            payload.temperature_c,
            payload.relative_humidity_percent,
            payload.crop_moisture_percent,
            crop_profile,
        )

        active_triggered_types = {v.condition_type for v in violations}

        # Check existing open (active + acknowledged) alerts for this batch
        all_batch_alerts = AlertRepository.list_by_batch(payload.batch_id)
        existing_open = [a for a in all_batch_alerts if a.get("status") in ("active", "acknowledged")]

        # Create new alerts for freshly triggered conditions (Debounce)
        for v in violations:
            existing_alert = AlertRepository.get_active_condition(payload.batch_id, v.condition_type)
            if not existing_alert:
                alert_id = f"alert_{uuid.uuid4().hex[:10]}"
                alert_doc = {
                    "alert_id": alert_id,
                    "batch_id": payload.batch_id,
                    "crop_name": crop_profile.get("crop_name", "Crop"),
                    "condition_type": v.condition_type,
                    "severity": v.severity,
                    "measured_value": v.measured_value,
                    "target_threshold": v.target_threshold,
                    "unit": v.unit,
                    "message": v.message,
                    "recommended_action": v.recommended_action,
                    "status": "active",
                    "whatsapp_notified": False,
                    "created_at": now_iso,
                    "resolved_at": None,
                }
                AlertRepository.create(alert_doc)

                # Auto-dispatch WhatsApp for new critical alerts
                if v.severity == "critical":
                    cls._maybe_auto_dispatch_whatsapp(batch, alert_doc)

        # Auto-resolve conditions that have recovered back to safe range
        for ea in existing_open:
            cond_type = ea["condition_type"]
            if cond_type not in active_triggered_types:
                # Measurement returned to normal! Auto-resolve
                AlertRepository.update_status(ea["alert_id"], status="resolved", resolved_at=now_iso)

        return SensorReadingOut(**reading_doc)

    @classmethod
    def _maybe_auto_dispatch_whatsapp(cls, batch: dict, alert_doc: dict):
        import time
        import re
        import asyncio
        from app.repositories.user_repository import UserRepository
        from app.integrations.whatsapp_client import WhatsAppClient

        batch_id = batch.get("batch_id")
        now = time.time()
        last_time = getattr(cls, "_batch_whatsapp_cooldown", {}).get(batch_id, 0.0)
        if now - last_time < 900:  # 15 minutes cooldown
            return

        owner_id = batch.get("user_id") or batch.get("farmer_id")
        if not owner_id:
            return
        owner = UserRepository.get_by_id(owner_id)
        if not owner:
            return
        prefs = owner.get("notification_preferences", {})
        if not prefs.get("enable_whatsapp_alerts", True):
            return
        target_phone = prefs.get("whatsapp_phone_number") or owner.get("phone_number")
        if not target_phone or not re.match(r"^\+[1-9]\d{7,14}$", target_phone):
            return

        if not hasattr(cls, "_batch_whatsapp_cooldown"):
            cls._batch_whatsapp_cooldown = {}
        cls._batch_whatsapp_cooldown[batch_id] = now

        async def _send():
            try:
                success = await WhatsAppClient.send_alert_notification(
                    phone_number=target_phone,
                    crop_name=alert_doc.get("crop_name", "Crop"),
                    condition_type=alert_doc.get("condition_type", "critical"),
                    measured_value=alert_doc.get("measured_value", 0.0),
                    unit=alert_doc.get("unit", ""),
                    recommended_action=alert_doc.get("recommended_action", ""),
                    batch_id=batch_id,
                    preferred_language=owner.get("preferred_language", "en"),
                )
                if success:
                    AlertRepository.update(alert_doc["alert_id"], {"whatsapp_notified": True})
            except Exception:
                pass

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_send())
        except RuntimeError:
            pass

    @classmethod
    def get_monitoring_summary(cls, batch_id: str) -> MonitoringSummaryOut:
        batch = StorageBatchRepository.get_by_id(batch_id)
        if not batch:
            raise ValueError(f"Storage batch '{batch_id}' not found.")

        crop_profile = CropRepository.get_by_id(batch["crop_id"]) or {}
        latest = SensorRepository.get_latest_for_batch(batch_id)
        recent = SensorRepository.list_for_batch(batch_id, limit=20)
        active_alerts = AlertRepository.list_by_batch(batch_id, status="active")

        risk = "normal"
        if any(a.get("severity") == "critical" for a in active_alerts):
            risk = "critical"
        elif any(a.get("severity") == "warning" for a in active_alerts):
            risk = "moderate"

        freshness = "no_data"
        if latest:
            freshness = "online"

        return MonitoringSummaryOut(
            batch_id=batch_id,
            crop_name=crop_profile.get("crop_name", batch.get("custom_batch_name", "Crop")),
            current_temperature_c=latest.get("temperature_c") if latest else None,
            current_humidity_percent=latest.get("relative_humidity_percent") if latest else None,
            current_moisture_percent=latest.get("crop_moisture_percent") if latest else None,
            current_co2_ppm=latest.get("co2_ppm") if latest else None,
            current_air_velocity_m_s=latest.get("air_velocity_m_s") if latest else None,
            current_pressure_kpa=latest.get("pressure_kpa") if latest else None,
            current_light_lux=latest.get("light_lux") if latest else None,
            target_temperature_min_c=crop_profile.get("recommended_temperature_min_c", 15.0),
            target_temperature_max_c=crop_profile.get("recommended_temperature_max_c", 25.0),
            target_humidity_min_percent=crop_profile.get("recommended_relative_humidity_min_percent", 50.0),
            target_humidity_max_percent=crop_profile.get("recommended_relative_humidity_max_percent", 70.0),
            target_moisture_percent=crop_profile.get("recommended_crop_moisture_percent", 12.0),
            last_reading_time=latest.get("timestamp") if latest else None,
            reading_provenance=latest.get("provenance") if latest else None,
            sensor_freshness_status=freshness,
            risk_level=risk,
            active_alerts=active_alerts,
            recent_readings=[SensorReadingOut(**r) for r in recent],
        )
