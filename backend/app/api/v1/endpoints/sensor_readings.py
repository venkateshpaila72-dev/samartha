"""Sensor Ingestion and Monitoring Endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user
from app.repositories.sensor_repository import SensorRepository
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.schemas.common import APIResponse
from app.schemas.sensor_reading import (
    MonitoringSummaryOut,
    SensorReadingCreate,
    SensorReadingOut,
)
from app.services.monitoring_service import MonitoringService

router = APIRouter(prefix="/batches", tags=["Monitoring & Sensors"])


@router.post("/{batch_id}/readings", response_model=APIResponse[SensorReadingOut])
async def ingest_sensor_reading(
    batch_id: str,
    payload: SensorReadingCreate,
    current_user: dict = Depends(get_current_user),
):
    batch = StorageBatchRepository.get_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage batch not found.")

    if current_user.get("role") != "admin" and batch["farmer_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this storage batch.")

    payload.batch_id = batch_id
    try:
        reading_out = MonitoringService.ingest_reading(payload)
        return APIResponse(
            success=True,
            message="Sensor measurement ingested and evaluated against verified crop limits.",
            data=reading_out,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{batch_id}/readings", response_model=APIResponse[list[SensorReadingOut]])
async def list_batch_readings(
    batch_id: str,
    limit: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    batch = StorageBatchRepository.get_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage batch not found.")

    if current_user.get("role") != "admin" and batch["farmer_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    readings = SensorRepository.list_for_batch(batch_id, limit=limit)
    items = [SensorReadingOut(**r) for r in readings]
    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} sensor readings.",
        data=items,
        meta={"total": len(items)},
    )


@router.get("/{batch_id}/monitoring", response_model=APIResponse[MonitoringSummaryOut])
async def get_monitoring_summary(
    batch_id: str,
    current_user: dict = Depends(get_current_user),
):
    batch = StorageBatchRepository.get_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage batch not found.")

    if current_user.get("role") != "admin" and batch["farmer_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    summary = MonitoringService.get_monitoring_summary(batch_id)
    return APIResponse(
        success=True,
        message="Monitoring summary retrieved.",
        data=summary,
    )
