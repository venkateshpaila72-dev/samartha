
"""Agricultural market-price API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user, get_owned_batch
from app.integrations.market_client import MarketClient
from app.repositories.crop_repository import CropRepository
from app.schemas.common import APIResponse
from app.schemas.market import MarketPriceReportOut

router = APIRouter(tags=["Market Prices"])


@router.get(
    "/market/prices",
    response_model=APIResponse[MarketPriceReportOut],
)
async def get_market_prices(
    crop: str = Query("Wheat", min_length=1, description="Crop or commodity name"),
    state: Optional[str] = Query(None, description="User's state"),
    district: Optional[str] = Query(None, description="User's district"),
    current_user: dict = Depends(get_current_user),
):
    report = await MarketClient.get_market_prices(
        crop_name=crop,
        state=state,
        district=district,
    )

    return APIResponse(
        success=True,
        message=f"Market price lookup completed for {crop}.",
        data=report,
    )


@router.get(
    "/batches/{batch_id}/market",
    response_model=APIResponse[MarketPriceReportOut],
)
async def get_batch_market_prices(
    batch_id: str,
    state: Optional[str] = Query(None, description="User's state"),
    district: Optional[str] = Query(None, description="User's district"),
    current_user: dict = Depends(get_current_user),
):
    # Keep the existing batch-ownership check.
    batch = get_owned_batch(batch_id, current_user)

    crop_doc = CropRepository.get_by_id(batch.get("crop_id", ""))
    crop_name = (
        crop_doc.get("crop_name")
        if crop_doc
        else batch.get("custom_batch_name", "Wheat")
    )

    report = await MarketClient.get_market_prices(
        crop_name=crop_name,
        state=state,
        district=district,
    )

    return APIResponse(
        success=True,
        message=f"Market price lookup completed for batch crop '{crop_name}'.",
        data=report,
    )
