"""Monitoring Service for FarmShield.
Handles reading ingestion, rule evaluation, alert deduplication, recovery,
and farmer-specific WhatsApp delivery with verified scientific and traditional guidance.
"""

import datetime
import logging
import uuid
from typing import Optional

from app.integrations.whatsapp_client import WhatsAppClient
from app.monitoring.rules import (
    evaluate_measurement_rules,
    mask_phone_number,
    normalize_phone_number,
)
from app.repositories.alert_repository import AlertRepository
from app.repositories.crop_repository import CropRepository
from app.repositories.sensor_repository import SensorRepository
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.repositories.user_repository import UserRepository
from app.schemas.sensor_reading import (
    MonitoringSummaryOut,
    SensorReadingCreate,
    SensorReadingOut,
)

logger = logging.getLogger(__name__)

# Sensible alert notification cooldown (15 minutes = 900 seconds)
ALERT_COOLDOWN_SECONDS = 900


class MonitoringService:
    @classmethod
    async def ingest_reading(cls, payload: SensorReadingCreate) -> SensorReadingOut:
        """Asynchronously ingests a sensor reading, persists it, evaluates thresholds,
        manages alerts and dispatches WhatsApp notification to the batch owner.
        """
        batch = StorageBatchRepository.get_by_id(payload.batch_id)
        if not batch:
            raise ValueError(f"Storage batch '{payload.batch_id}' not found.")

        crop_profile = CropRepository.get_by_id(batch.get("crop_id", ""))
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

        # 1. Persist Reading immediately to MongoDB
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

        # 3. Identify Batch Owner (Farmer)
        owner_id = batch.get("farmer_id") or batch.get("user_id")
        owner = UserRepository.get_by_id(owner_id) if owner_id else None

        # 4. Evaluate Threshold Rules against Verified Scientific Limits
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

        # 5. Process Each Violation (Create / Debounce / Deliver)
        for v in violations:
            existing_alert = AlertRepository.get_active_condition(payload.batch_id, v.condition_type)

            if not existing_alert:
                # Fresh violation (or recurs after resolving)
                alert_id = f"alert_{uuid.uuid4().hex[:10]}"
                target_phone = None
                if owner:
                    prefs = owner.get("notification_preferences", {})
                    target_phone = prefs.get("whatsapp_phone_number") or owner.get("phone_number")

                alert_doc = {
                    "alert_id": alert_id,
                    "batch_id": payload.batch_id,
                    "farmer_id": owner_id,
                    "crop_name": crop_profile.get("crop_name", "Crop"),
                    "condition_type": v.condition_type,
                    "severity": v.severity,
                    "measured_value": v.measured_value,
                    "target_threshold": v.target_threshold,
                    "target_range_min": v.target_min,
                    "target_range_max": v.target_max,
                    "unit": v.unit,
                    "message": v.message,
                    "recommended_action": v.recommended_action,
                    "status": "active",
                    "whatsapp_notified": False,
                    "whatsapp_delivery_status": "pending",
                    "whatsapp_recipient_masked": mask_phone_number(target_phone),
                    "whatsapp_last_attempt_at": None,
                    "whatsapp_delivery_error": None,
                    "created_at": now_iso,
                    "resolved_at": None,
                }
                AlertRepository.create(alert_doc)

                # Auto-dispatch WhatsApp to farmer
                try:
                    await cls._dispatch_whatsapp_for_alert(batch, owner, alert_doc, crop_profile, v)
                except Exception as exc:
                    logger.error("WhatsApp auto-dispatch failed for alert %s: %s", alert_id, exc)
                    AlertRepository.update(
                        alert_id,
                        {
                            "whatsapp_notified": False,
                            "whatsapp_delivery_status": "failed",
                            "whatsapp_last_attempt_at": now_iso,
                            "whatsapp_delivery_error": str(exc),
                        },
                    )

            else:
                # Continuously active violation: update reading on existing alert
                alert_id = existing_alert["alert_id"]
                old_val = existing_alert.get("measured_value", v.measured_value)
                old_status = (existing_alert.get("whatsapp_delivery_status") or "").lower()

                # Update in-memory dict so dispatch uses latest sensor measurement
                existing_alert["measured_value"] = v.measured_value
                existing_alert["severity"] = v.severity
                existing_alert["message"] = v.message
                existing_alert["target_threshold"] = v.target_threshold
                existing_alert["target_range_min"] = v.target_min
                existing_alert["target_range_max"] = v.target_max
                existing_alert["recommended_action"] = v.recommended_action
                existing_alert["created_at"] = now_iso

                AlertRepository.update(
                    alert_id,
                    {
                        "measured_value": v.measured_value,
                        "severity": v.severity,
                        "message": v.message,
                        "target_threshold": v.target_threshold,
                        "target_range_min": v.target_min,
                        "target_range_max": v.target_max,
                        "recommended_action": v.recommended_action,
                    },
                )

                # Direct WhatsApp delivery on violation reading:
                # Renotify immediately if:
                # 1. Previous delivery attempt did not succeed (pending, failed, sandbox_not_opted_in, invalid_phone_number)
                # 2. Or the measured value changed significantly (abs(v.measured_value - old_val) >= 0.1)
                # 3. Or at least 60 seconds have elapsed since last attempt
                last_attempt_iso = existing_alert.get("whatsapp_last_attempt_at")
                should_renotify = False
                if not last_attempt_iso:
                    should_renotify = True
                elif old_status not in ("accepted", "queued", "sent", "delivered"):
                    should_renotify = True
                elif abs(v.measured_value - float(old_val)) >= 0.1:
                    should_renotify = True
                else:
                    try:
                        last_dt = datetime.datetime.fromisoformat(last_attempt_iso)
                        if last_dt.tzinfo is None:
                            last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)
                        now_dt = datetime.datetime.now(datetime.timezone.utc)
                        if (now_dt - last_dt).total_seconds() >= 60:
                            should_renotify = True
                    except Exception:
                        should_renotify = True

                if should_renotify:
                    try:
                        await cls._dispatch_whatsapp_for_alert(batch, owner, existing_alert, crop_profile, v)
                    except Exception as exc:
                        logger.error("WhatsApp renotify failed for alert %s: %s", alert_id, exc)

        # 6. Auto-resolve conditions that have recovered back to safe range
        for ea in existing_open:
            cond_type = ea["condition_type"]
            if cond_type not in active_triggered_types:
                # Reading returned to safe range! Auto-resolve alert
                AlertRepository.update_status(ea["alert_id"], status="resolved", resolved_at=now_iso)
                logger.info(
                    "Auto-resolved alert %s (%s) for batch %s after reading returned to safe range",
                    ea["alert_id"],
                    cond_type,
                    payload.batch_id,
                )

        return SensorReadingOut(**reading_doc)

    @classmethod
    def ingest_reading_sync(cls, payload: SensorReadingCreate) -> SensorReadingOut:
        """Synchronous wrapper for test fixtures or scripts."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(cls.ingest_reading(payload))

    @classmethod
    async def _dispatch_whatsapp_for_alert(
        cls,
        batch: dict,
        owner: Optional[dict],
        alert_doc: dict,
        crop_profile: dict,
        rule_result: Optional[object] = None,
    ):
        """Constructs and delivers actionable WhatsApp notification to the batch owner."""
        alert_id = alert_doc["alert_id"]
        batch_id = batch.get("batch_id", "")
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Check farmer preferences
        if not owner:
            status = "missing_phone_number"
            err_msg = "Storage batch has no registered owner profile."
            AlertRepository.update(
                alert_id,
                {
                    "whatsapp_notified": False,
                    "whatsapp_delivery_status": status,
                    "whatsapp_last_attempt_at": now_iso,
                    "whatsapp_delivery_error": err_msg,
                    "whatsapp_recipient_masked": "Not provided",
                },
            )
            return

        prefs = owner.get("notification_preferences", {})
        if not prefs.get("enable_whatsapp_alerts", True):
            status = "disabled_by_preferences"
            err_msg = "Farmer has disabled WhatsApp alert notifications in profile preferences."
            AlertRepository.update(
                alert_id,
                {
                    "whatsapp_notified": False,
                    "whatsapp_delivery_status": status,
                    "whatsapp_last_attempt_at": now_iso,
                    "whatsapp_delivery_error": err_msg,
                    "whatsapp_recipient_masked": mask_phone_number(owner.get("phone_number")),
                },
            )
            return

        target_phone = prefs.get("whatsapp_phone_number") or owner.get("phone_number")
        crop_name = crop_profile.get("crop_name", alert_doc.get("crop_name", "Crop"))
        cond_type = alert_doc.get("condition_type", "temperature_high")

        delivery_result = await WhatsAppClient.send_alert_notification(
            phone_number=target_phone,
            crop_name=crop_name,
            batch_name=batch.get("custom_batch_name"),
            batch_id=batch_id,
            condition_type=cond_type,
            severity=alert_doc.get("severity", "warning"),
            measured_value=alert_doc.get("measured_value", 0.0),
            unit=alert_doc.get("unit", "°C"),
            recommended_action=alert_doc.get("recommended_action", "Check storage conditions immediately."),
            preferred_language=owner.get("preferred_language", "en"),
            target_threshold=alert_doc.get("target_threshold"),
            target_range_min=alert_doc.get("target_range_min"),
            target_range_max=alert_doc.get("target_range_max"),
            reading_time=alert_doc.get("created_at"),
            alert_id=alert_id,
            is_sandbox_opted_in=owner.get("whatsapp_opt_in_completed"),
        )

        AlertRepository.update(
            alert_id,
            {
                "whatsapp_notified": delivery_result.success,
                "whatsapp_delivery_status": delivery_result.status,
                "whatsapp_last_attempt_at": now_iso,
                "whatsapp_delivery_error": delivery_result.error,
                "whatsapp_recipient_masked": delivery_result.recipient_masked,
            },
        )

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
