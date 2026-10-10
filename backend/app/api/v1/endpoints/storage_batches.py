"""Storage Batch Management Endpoints."""

import datetime
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user
from app.repositories.alert_repository import AlertRepository
from app.repositories.crop_repository import CropRepository
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.schemas.common import APIResponse
from app.schemas.crop_profile import CropProfileOut
from app.schemas.storage_batch import (
    LatestReadingSummary,
    StorageBatchCreate,
    StorageBatchOut,
    StorageBatchUpdate,
)

router = APIRouter(prefix="/batches", tags=["Storage Batches"])


def _hydrate_batch(batch_doc: dict) -> StorageBatchOut:
    crop_doc = CropRepository.get_by_id(batch_doc.get("crop_id", ""))
    crop_profile = CropProfileOut(**crop_doc) if crop_doc else None

    latest_doc = batch_doc.get("latest_reading")
    latest_reading = LatestReadingSummary(**latest_doc) if latest_doc else None

    active_alerts = AlertRepository.list_by_batch(batch_doc["batch_id"], status="active")

    return StorageBatchOut(
        batch_id=batch_doc["batch_id"],
        farmer_id=batch_doc["farmer_id"],
        crop_id=batch_doc["crop_id"],
        custom_batch_name=batch_doc["custom_batch_name"],
        quantity_kg=batch_doc["quantity_kg"],
        harvest_date=batch_doc["harvest_date"],
        storage_start_date=batch_doc["storage_start_date"],
        storage_structure_type=batch_doc.get("storage_structure_type", "Warehouse"),
        storage_location=batch_doc.get("storage_location", "Main Storage"),
        initial_crop_condition=batch_doc.get("initial_crop_condition", "Clean, dry"),
        status=batch_doc.get("status", "active"),
        notes=batch_doc.get("notes"),
        created_at=batch_doc.get("created_at", ""),
        updated_at=batch_doc.get("updated_at", ""),
        crop_profile=crop_profile,
        latest_reading=latest_reading,
        active_alerts_count=len(active_alerts),
    )


@router.post("", response_model=APIResponse[StorageBatchOut])
async def create_storage_batch(
    payload: StorageBatchCreate,
    current_user: dict = Depends(get_current_user),
):
    crop = CropRepository.get_by_id(payload.crop_id)
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Crop profile with ID '{payload.crop_id}' does not exist.",
        )

    batch_id = f"batch_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    doc = {
        "batch_id": batch_id,
        "farmer_id": current_user["id"],
        "crop_id": payload.crop_id,
        "custom_batch_name": payload.custom_batch_name,
        "quantity_kg": payload.quantity_kg,
        "harvest_date": payload.harvest_date,
        "storage_start_date": payload.storage_start_date,
        "storage_structure_type": payload.storage_structure_type,
        "storage_location": payload.storage_location,
        "initial_crop_condition": payload.initial_crop_condition,
        "status": "active",
        "notes": payload.notes,
        "created_at": now_iso,
        "updated_at": now_iso,
        "latest_reading": None,
    }

    StorageBatchRepository.create(doc)
    hydrated = _hydrate_batch(doc)
    return APIResponse(
        success=True,
        message=f"Storage batch '{payload.custom_batch_name}' created successfully with verified {crop['crop_name']} profile.",
        data=hydrated,
    )


@router.get("", response_model=APIResponse[list[StorageBatchOut]])
async def list_storage_batches(
    status: Optional[str] = Query(None, description="Filter by status (active, closed)"),
    current_user: dict = Depends(get_current_user),
):
    # If admin, can view all batches, else only user's batches
    if current_user.get("role") == "admin":
        raw_batches = StorageBatchRepository.list_all()
        if status:
            raw_batches = [b for b in raw_batches if b.get("status") == status]
    else:
        raw_batches = StorageBatchRepository.list_by_farmer(current_user["id"], status=status)

    items = [_hydrate_batch(b) for b in raw_batches]
    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} storage batches.",
        data=items,
        meta={"total": len(items)},
    )


@router.get("/{batch_id}", response_model=APIResponse[StorageBatchOut])
async def get_storage_batch(
    batch_id: str,
    current_user: dict = Depends(get_current_user),
):
    batch = StorageBatchRepository.get_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage batch not found.")

    if current_user.get("role") != "admin" and batch["farmer_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this storage batch.")

    return APIResponse(
        success=True,
        message="Storage batch retrieved.",
        data=_hydrate_batch(batch),
    )


@router.patch("/{batch_id}", response_model=APIResponse[StorageBatchOut])
async def update_storage_batch(
    batch_id: str,
    payload: StorageBatchUpdate,
    current_user: dict = Depends(get_current_user),
):
    batch = StorageBatchRepository.get_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage batch not found.")

    if current_user.get("role") != "admin" and batch["farmer_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    updated = StorageBatchRepository.update(batch_id, updates)
    return APIResponse(
        success=True,
        message="Storage batch updated successfully.",
        data=_hydrate_batch(updated),
    )


@router.post("/{batch_id}/close", response_model=APIResponse[StorageBatchOut])
async def close_storage_batch(
    batch_id: str,
    current_user: dict = Depends(get_current_user),
):
    batch = StorageBatchRepository.get_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage batch not found.")

    if current_user.get("role") != "admin" and batch["farmer_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    updated = StorageBatchRepository.update(batch_id, {"status": "closed", "updated_at": now_iso})
    return APIResponse(
        success=True,
        message="Storage batch closed.",
        data=_hydrate_batch(updated),
    )
