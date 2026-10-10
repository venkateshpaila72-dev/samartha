"""Agricultural Market Price Endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user, get_owned_batch
from app.integrations.market_client import MarketClient
from app.repositories.crop_repository import CropRepository
from app.schemas.common import APIResponse
from app.schemas.market import MarketPriceReportOut

router = APIRouter(tags=["Market Prices"])


@router.get("/market/prices", response_model=APIResponse[MarketPriceReportOut])
async def get_market_prices(
    crop: str = Query("Wheat", description="Crop name"),
    current_user: dict = Depends(get_current_user),
):
    report = await MarketClient.get_market_prices(crop_name=crop)
    return APIResponse(
        success=True,
        message=f"APMC market prices for {report.crop_name} retrieved.",
        data=report,
    )


@router.get("/batches/{batch_id}/market", response_model=APIResponse[MarketPriceReportOut])
async def get_batch_market_prices(
    batch_id: str,
    current_user: dict = Depends(get_current_user),
):
    # Enforce batch ownership check (fixes H4)
    batch = get_owned_batch(batch_id, current_user)

    crop_doc = CropRepository.get_by_id(batch.get("crop_id", ""))
    crop_name = crop_doc.get("crop_name") if crop_doc else batch.get("custom_batch_name", "Wheat")

    report = await MarketClient.get_market_prices(crop_name=crop_name)
    return APIResponse(
        success=True,
        message=f"APMC market prices for batch crop '{crop_name}' retrieved.",
        data=report,
    )
