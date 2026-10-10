import datetime
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user, get_owned_batch
from app.repositories.alert_repository import AlertRepository
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.schemas.alert import AlertStatusUpdate, NotificationPreferencesUpdate, StorageAlertOut
from app.schemas.common import APIResponse

router = APIRouter(tags=["Alerts & Notifications"])

E164_REGEX = r"^\+[1-9]\d{7,14}$"


@router.get("/alerts/preferences", response_model=APIResponse[NotificationPreferencesUpdate])
async def get_notification_preferences(current_user: dict = Depends(get_current_user)):
    prefs = current_user.get("notification_preferences", {})
    return APIResponse(
        success=True,
        message="Notification preferences retrieved.",
        data=NotificationPreferencesUpdate(
            enable_whatsapp_alerts=prefs.get("enable_whatsapp_alerts", True),
            whatsapp_phone_number=prefs.get("whatsapp_phone_number") or current_user.get("phone_number"),
            alert_severity_threshold=prefs.get("alert_severity_threshold", "warning"),
        ),
    )


@router.put("/alerts/preferences", response_model=APIResponse[NotificationPreferencesUpdate])
async def update_notification_preferences(
    payload: NotificationPreferencesUpdate,
    current_user: dict = Depends(get_current_user),
):
    if payload.whatsapp_phone_number:
        from app.monitoring.rules import normalize_phone_number
        norm = normalize_phone_number(payload.whatsapp_phone_number)
        if not norm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone number format. Must follow E.164 standard (e.g., +919876543210).",
            )
        payload.whatsapp_phone_number = norm
    from app.repositories.user_repository import UserRepository
    UserRepository.update(
        current_user["id"],
        {"notification_preferences": payload.model_dump()},
    )
    return APIResponse(
        success=True,
        message="Notification preferences updated successfully.",
        data=payload,
    )


@router.get("/alerts", response_model=APIResponse[list[StorageAlertOut]])
async def list_alerts(
    batch_id: Optional[str] = Query(None, description="Filter by batch ID"),
    status: Optional[str] = Query(None, description="Filter by status (active, acknowledged, resolved)"),
    current_user: dict = Depends(get_current_user),
):
    if batch_id:
        get_owned_batch(batch_id, current_user)
        raw_alerts = AlertRepository.list_by_batch(batch_id, status=status)
    else:
        # If farmer, get alerts for all their batches
        if current_user.get("role") == "admin":
            raw_alerts = AlertRepository.list_all(status=status)
        else:
            user_batches = StorageBatchRepository.list_by_farmer(current_user["id"])
            batch_ids = {b["batch_id"] for b in user_batches}
            all_alerts = AlertRepository.list_all(status=status)
            raw_alerts = [a for a in all_alerts if a["batch_id"] in batch_ids]

    items = [StorageAlertOut(**a) for a in raw_alerts]
    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} storage alerts.",
        data=items,
        meta={"total": len(items)},
    )


@router.patch("/alerts/{alert_id}", response_model=APIResponse[StorageAlertOut])
async def update_alert_status(
    alert_id: str,
    payload: AlertStatusUpdate,
    current_user: dict = Depends(get_current_user),
):
    alert = AlertRepository.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    if alert.get("batch_id"):
        get_owned_batch(alert["batch_id"], current_user)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    resolved_at = now_iso if payload.status == "resolved" else None

    updated = AlertRepository.update_status(alert_id, status=payload.status, resolved_at=resolved_at)
    return APIResponse(
        success=True,
        message=f"Alert marked as '{payload.status}'.",
        data=StorageAlertOut(**updated),
    )


@router.post("/alerts/{alert_id}/dispatch-whatsapp", response_model=APIResponse[dict])
async def dispatch_whatsapp_alert(
    alert_id: str,
    phone_number: Optional[str] = Query(None, description="Target WhatsApp phone number (admin override only)"),
    current_user: dict = Depends(get_current_user),
):
    """Dispatches a WhatsApp notification via Twilio for a specific alert using the farmer's registered profile."""
    from app.integrations.rag_adapter import RAGAdapter
    from app.integrations.whatsapp_client import WhatsAppClient
    from app.monitoring.rules import mask_phone_number, normalize_phone_number
    from app.repositories.crop_repository import CropRepository
    from app.repositories.user_repository import UserRepository

    alert = AlertRepository.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    batch_id = alert.get("batch_id")
    if not batch_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch for this alert not found.")

    batch = get_owned_batch(batch_id, current_user)
    owner_id = batch.get("farmer_id") or batch.get("user_id")
    owner = UserRepository.get_by_id(owner_id) if owner_id else current_user
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    is_admin = current_user.get("role") == "admin"
    if is_admin and phone_number:
        raw_phone = phone_number.strip()
    else:
        prefs = (owner or {}).get("notification_preferences", {})
        raw_phone = prefs.get("whatsapp_phone_number") or (owner or {}).get("phone_number")

    normalized_phone = normalize_phone_number(raw_phone)
    if not normalized_phone:
        err = f"A valid E.164 phone number (e.g. +919876543210) is required for WhatsApp dispatch. Received: '{raw_phone or ''}'."
        AlertRepository.update(
            alert_id,
            {
                "whatsapp_notified": False,
                "whatsapp_delivery_status": "invalid_phone_number" if raw_phone else "missing_phone_number",
                "whatsapp_last_attempt_at": now_iso,
                "whatsapp_delivery_error": err,
                "whatsapp_recipient_masked": mask_phone_number(raw_phone),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err,
        )

    crop_profile = CropRepository.get_by_id(batch.get("crop_id", "")) or {}
    crop_name = alert.get("crop_name") or crop_profile.get("crop_name", "Crop")

    delivery_res = await WhatsAppClient.send_alert_notification(
        phone_number=normalized_phone,
        crop_name=crop_name,
        batch_name=batch.get("custom_batch_name"),
        batch_id=batch_id,
        condition_type=alert.get("condition_type", "condition"),
        severity=alert.get("severity", "warning"),
        measured_value=alert.get("measured_value", 0.0),
        unit=alert.get("unit", "°C"),
        recommended_action=alert.get("recommended_action", "Check storage conditions immediately."),
        preferred_language=(owner or {}).get("preferred_language", "en"),
        target_threshold=alert.get("target_threshold"),
        target_range_min=alert.get("target_range_min"),
        target_range_max=alert.get("target_range_max"),
        reading_time=alert.get("created_at"),
        alert_id=alert_id,
        is_sandbox_opted_in=(owner or {}).get("whatsapp_opt_in_completed"),
    )

    AlertRepository.update(
        alert_id,
        {
            "whatsapp_notified": delivery_res.success,
            "whatsapp_delivery_status": delivery_res.status,
            "whatsapp_last_attempt_at": now_iso,
            "whatsapp_delivery_error": delivery_res.error,
            "whatsapp_recipient_masked": delivery_res.recipient_masked,
        },
    )

    return APIResponse(
        success=delivery_res.success,
        message="WhatsApp notification dispatched via Twilio." if delivery_res.success else f"WhatsApp notification failed: {delivery_res.error or delivery_res.status}",
        data={
            "alert_id": alert_id,
            "provider": "Twilio",
            "dispatched": delivery_res.success,
            "status": delivery_res.status,
            "recipient": delivery_res.recipient_masked,
            "error": delivery_res.error,
        },
    )


@router.post("/alerts/twilio-callback")
async def twilio_status_callback(
    MessageSid: Optional[str] = Query(None),
    MessageStatus: Optional[str] = Query(None),
    ErrorCode: Optional[str] = Query(None),
    ErrorMessage: Optional[str] = Query(None),
):
    """Twilio WhatsApp delivery status callback webhook to distinguish API acceptance from delivery."""
    from app.db.collection_names import NOTIFICATION_LOGS_COLLECTION, STORAGE_ALERTS_COLLECTION
    from app.db.mongo import get_db

    if not MessageSid:
        return {"status": "ignored"}

    status_str = (MessageStatus or "").lower()
    db = get_db()
    if db is not None:
        try:
            update_fields = {"whatsapp_delivery_status": status_str}
            if status_str in ("failed", "undelivered"):
                update_fields["whatsapp_notified"] = False
                update_fields["whatsapp_delivery_error"] = ErrorMessage or f"Twilio delivery failed (code {ErrorCode})"
            elif status_str in ("delivered", "read"):
                update_fields["whatsapp_notified"] = True
                update_fields["whatsapp_delivery_error"] = None

            # Update notification logs
            db[NOTIFICATION_LOGS_COLLECTION].update_many(
                {"message_sid": MessageSid},
                {"$set": {"status": status_str, "error": ErrorMessage if status_str in ("failed", "undelivered") else None}},
            )
        except Exception:
            pass

    return {"status": "recorded", "message_sid": MessageSid, "delivery_status": status_str}

