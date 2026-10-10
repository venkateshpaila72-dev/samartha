"""Farmer Diary Endpoints."""

import datetime
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.repositories.diary_repository import DiaryRepository
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.schemas.common import APIResponse
from app.schemas.diary import DiaryEntryCreate, DiaryEntryOut, DiaryEntryUpdate

router = APIRouter(tags=["Farmer Diary"])


@router.post("/batches/{batch_id}/diary", response_model=APIResponse[DiaryEntryOut])
async def create_diary_entry(
    batch_id: str,
    payload: DiaryEntryCreate,
    current_user: dict = Depends(get_current_user),
):
    batch = StorageBatchRepository.get_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage batch not found.")

    if current_user.get("role") != "admin" and batch["farmer_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    entry_id = f"diary_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    doc = {
        "entry_id": entry_id,
        "batch_id": batch_id,
        "farmer_id": current_user["id"],
        "observation_text": payload.observation_text,
        "observation_category": payload.observation_category,
        "photo_urls": payload.photo_urls,
        "voice_recording_url": payload.voice_recording_url,
        "voice_transcript": payload.voice_transcript,
        "severity_assessment": payload.severity_assessment,
        "provenance": payload.provenance,
        "ai_advisory_analysis": None,
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    DiaryRepository.create(doc)
    return APIResponse(
        success=True,
        message="Observation recorded in crop diary.",
        data=DiaryEntryOut(**doc),
    )


@router.get("/batches/{batch_id}/diary", response_model=APIResponse[list[DiaryEntryOut]])
async def list_batch_diary_entries(
    batch_id: str,
    current_user: dict = Depends(get_current_user),
):
    batch = StorageBatchRepository.get_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage batch not found.")

    if current_user.get("role") != "admin" and batch["farmer_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    entries = DiaryRepository.list_by_batch(batch_id)
    items = [DiaryEntryOut(**e) for e in entries]
    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} diary entries.",
        data=items,
        meta={"total": len(items)},
    )


@router.get("/diary/{entry_id}", response_model=APIResponse[DiaryEntryOut])
async def get_diary_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
):
    entry = DiaryRepository.get_by_id(entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found.")

    if current_user.get("role") != "admin" and entry["farmer_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return APIResponse(
        success=True,
        message="Diary entry retrieved.",
        data=DiaryEntryOut(**entry),
    )


@router.patch("/diary/{entry_id}", response_model=APIResponse[DiaryEntryOut])
async def update_diary_entry(
    entry_id: str,
    payload: DiaryEntryUpdate,
    current_user: dict = Depends(get_current_user),
):
    entry = DiaryRepository.get_by_id(entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found.")

    if current_user.get("role") != "admin" and entry["farmer_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    updated = DiaryRepository.update(entry_id, updates)

    return APIResponse(
        success=True,
        message="Diary entry updated.",
        data=DiaryEntryOut(**updated),
    )


@router.delete("/diary/{entry_id}", response_model=APIResponse[dict])
async def delete_diary_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
):
    entry = DiaryRepository.get_by_id(entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found.")

    if current_user.get("role") != "admin" and entry["farmer_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    success = DiaryRepository.delete(entry_id)
    return APIResponse(
        success=success,
        message="Diary entry deleted successfully.",
        data={"entry_id": entry_id},
    )
