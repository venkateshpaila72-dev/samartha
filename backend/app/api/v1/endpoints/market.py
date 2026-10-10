"""Agricultural Market Price Endpoints."""

from typing import Optional
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.dependencies import get_current_user, get_owned_batch
from app.services.farmshield_agent import FarmShieldAgent
from app.repositories.crop_repository import CropRepository
from app.schemas.common import APIResponse
from app.schemas.market import MarketPriceReportOut
from app.core.config import settings
from app.integrations.market_ingestion_client import sync_market_prices

router = APIRouter(tags=["Market Prices"])


@router.get("/market/prices", response_model=APIResponse[MarketPriceReportOut])
async def get_market_prices(
    crop: str = Query(..., min_length=1, description="Farmer-selected crop"),
    state: Optional[str] = Query(None, description="Farmer state"),
    district: Optional[str] = Query(None, description="Farmer district"),
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    report = await FarmShieldAgent.market_advisory(
        crop_name=crop,
        language=current_user.get("preferred_language", "en"),
        state=state,
        district=district,
        limit=limit,
        skip=skip,
    )
    return APIResponse(
        success=True,
        message="Market price lookup completed.",
        data=report,
    )


@router.get("/batches/{batch_id}/market", response_model=APIResponse[MarketPriceReportOut])
async def get_batch_market_prices(
    batch_id: str,
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    batch = get_owned_batch(batch_id, current_user)
    crop_doc = CropRepository.get_by_id(batch.get("crop_id", ""))
    crop_name = crop_doc.get("crop_name") if crop_doc else batch.get("custom_batch_name")

    if not crop_name:
        raise ValueError("The selected batch does not have a crop assigned.")

    report = await FarmShieldAgent.market_advisory(
        crop_name=crop_name,
        language=current_user.get("preferred_language", "en"),
        state=state,
        district=district,
        limit=limit,
        skip=skip,
    )
    return APIResponse(
        success=True,
        message="Batch crop market-price lookup completed.",
        data=report,
    )


@router.post("/market/sync", tags=["Market Prices"])
async def sync_market_data(
    crop: Optional[str] = Query(None, min_length=1, max_length=100),
    state: Optional[str] = Query(None, max_length=100),
    district: Optional[str] = Query(None, max_length=100),
    max_pages: int = Query(10, ge=1, le=100),
    sync_secret: Optional[str] = Header(None, alias="X-Market-Sync-Secret"),
):
    """Authenticated ingestion hook for a daily scheduler (e.g. GitHub Actions).

    Keep the sync secret in deployment secrets; never expose it in the frontend.
    """
    configured_secret = settings.MARKET_SYNC_SECRET.strip()
    if not configured_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market sync is disabled because MARKET_SYNC_SECRET is not configured.",
        )
    if not sync_secret or not hmac.compare_digest(sync_secret, configured_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid market sync secret.")
    try:
        result = await sync_market_prices(
            crop=crop, state=state, district=district, max_pages=max_pages
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        # Do not leak provider responses, API keys, or request URLs into the client response.
        import logging
        logging.getLogger(__name__).error("Scheduled market-price ingestion failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Market provider ingestion failed. Check backend logs for the provider error.",
        ) from exc
    return {"success": True, "message": "Market-data ingestion completed.", "data": result}
