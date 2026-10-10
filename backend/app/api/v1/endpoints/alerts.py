"""Storage Alerts and Notification Endpoints."""

import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user
from app.repositories.alert_repository import AlertRepository
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.schemas.alert import AlertStatusUpdate, StorageAlertOut
from app.schemas.common import APIResponse

router = APIRouter(tags=["Alerts & Notifications"])


@router.get("/alerts", response_model=APIResponse[list[StorageAlertOut]])
async def list_alerts(
    batch_id: Optional[str] = Query(None, description="Filter by batch ID"),
    status: Optional[str] = Query(None, description="Filter by status (active, acknowledged, resolved)"),
    current_user: dict = Depends(get_current_user),
):
    if batch_id:
        batch = StorageBatchRepository.get_by_id(batch_id)
        if not batch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage batch not found.")
        if current_user.get("role") != "admin" and batch["farmer_id"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
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

    batch = StorageBatchRepository.get_by_id(alert["batch_id"])
    if batch and current_user.get("role") != "admin" and batch["farmer_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

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
    phone_number: Optional[str] = Query(None, description="Target WhatsApp phone number"),
    current_user: dict = Depends(get_current_user),
):
    """Dispatches a WhatsApp notification via Twilio for a specific alert."""
    from app.integrations.whatsapp_client import WhatsAppClient

    alert = AlertRepository.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    target_phone = phone_number or current_user.get("phone", "+919876543210")
    success = await WhatsAppClient.send_alert_notification(
        phone_number=target_phone,
        crop_name=alert.get("crop_name", "Stored Crop"),
        condition_type=alert.get("condition_type", "condition"),
        measured_value=alert.get("measured_value", 0.0),
        unit=alert.get("unit", ""),
        recommended_action=alert.get("recommended_action", "Check storage conditions immediately."),
        batch_id=alert.get("batch_id", ""),
    )

    if success:
        AlertRepository.update(alert_id, {"whatsapp_notified": True})

    return APIResponse(
        success=success,
        message="WhatsApp notification dispatched via Twilio." if success else "WhatsApp dispatch recorded with status.",
        data={
            "alert_id": alert_id,
            "provider": "Twilio",
            "dispatched": success,
            "recipient": target_phone[:4] + "****" if len(target_phone) > 4 else "unknown",
        },
    )

