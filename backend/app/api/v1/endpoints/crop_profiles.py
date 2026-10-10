"""Crop Profiles Endpoints."""

import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_admin
from app.repositories.crop_repository import CropRepository
from app.schemas.common import APIResponse
from app.schemas.crop_profile import (
    CropProfileCreate,
    CropProfileOut,
    CropProfileUpdate,
    CropSelectionMatchResult,
    CropSelectionQuery,
)
from app.services.crop_profile_service import CropProfileService

router = APIRouter(tags=["Crop Profiles"])


@router.get("/crops", response_model=APIResponse[list[CropProfileOut]])
async def list_crops(
    category: Optional[str] = Query(None, description="Filter by crop category"),
    search: Optional[str] = Query(None, description="Search by crop name"),
):
    crops = CropProfileService.list_crops(category=category, search=search)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(crops)} crop profiles.",
        data=crops,
        meta={"total": len(crops)},
    )


@router.get("/crops/{crop_id}", response_model=APIResponse[CropProfileOut])
async def get_crop_profile(crop_id: str):
    profile = CropProfileService.get_profile_by_id(crop_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop profile '{crop_id}' not found.",
        )
    return APIResponse(
        success=True,
        message="Crop profile retrieved.",
        data=profile,
    )


@router.post("/crops/match", response_model=APIResponse[CropSelectionMatchResult])
async def match_crop_profile(query: CropSelectionQuery):
    result = CropProfileService.match_crop_profile(
        crop_name=query.crop_name,
        variety=query.variety,
        crop_form=query.crop_form,
        storage_type=query.storage_type,
        region=query.region,
        intended_duration=query.intended_storage_duration,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No matching verified crop profile found for '{query.crop_name}'.",
        )
    return APIResponse(
        success=True,
        message="Optimal crop profile matched successfully.",
        data=result,
    )


# --- Admin Crop Management Endpoints ---


@router.post("/admin/crops", response_model=APIResponse[CropProfileOut])
async def create_crop_profile(
    payload: CropProfileCreate,
    current_admin: dict = Depends(get_current_admin),
):
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    doc = payload.model_dump()
    doc["created_at"] = now_iso
    doc["updated_at"] = now_iso
    doc["is_admin_customized"] = True

    CropRepository.create_or_update(doc)
    return APIResponse(
        success=True,
        message="New crop profile created by administrator.",
        data=CropProfileOut(**doc),
    )


@router.patch("/admin/crops/{crop_id}", response_model=APIResponse[CropProfileOut])
async def update_crop_profile(
    crop_id: str,
    payload: CropProfileUpdate,
    current_admin: dict = Depends(get_current_admin),
):
    existing = CropRepository.get_by_id(crop_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop profile not found.")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    updates["is_admin_customized"] = True
    existing.update(updates)

    CropRepository.create_or_update(existing)
    return APIResponse(
        success=True,
        message="Crop profile updated.",
        data=CropProfileOut(**existing),
    )


@router.post("/admin/crops/{crop_id}/verify", response_model=APIResponse[CropProfileOut])
async def verify_crop_profile(
    crop_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    existing = CropRepository.get_by_id(crop_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop profile not found.")

    existing["verification_status"] = "verified"
    existing["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    existing["is_admin_customized"] = True
    CropRepository.create_or_update(existing)

    return APIResponse(
        success=True,
        message="Crop profile verified successfully.",
        data=CropProfileOut(**existing),
    )
