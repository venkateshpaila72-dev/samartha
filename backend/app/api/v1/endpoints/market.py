"""Agricultural Market Price Endpoints."""

from typing import Optional
import hmac
import datetime
import logging

from fastapi import APIRouter, Depends, Query, Header, HTTPException, status

from app.api.dependencies import get_current_user, get_owned_batch
from app.services.farmshield_agent import FarmShieldAgent
from app.repositories.crop_repository import CropRepository
from app.schemas.common import APIResponse
from app.schemas.market import MarketPriceReportOut
from app.core.config import settings
from app.integrations.market_ingestion_client import sync_market_prices
from app.db.mongo import get_db

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


@router.post("/market/sync-now", tags=["Market Prices"])
async def farmer_sync_market_prices(
    crop: str = Query(..., min_length=1, max_length=100),
    state: str = Query(..., min_length=1, max_length=100),
    district: Optional[str] = Query(None, max_length=100),
    current_user: dict = Depends(get_current_user),
):
    """Allow authenticated farmers to request a bounded, crop-specific import."""
    if not settings.MARKET_API_KEY.strip():
        raise HTTPException(status_code=503, detail="Market data sync is not configured.")
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Market database is unavailable.")
    now = datetime.datetime.now(datetime.timezone.utc)
    requests = db["market_sync_requests"]
    key = {"user_id": current_user["id"]}
    previous = requests.find_one(key, {"requested_at": 1})
    if previous and previous.get("requested_at"):
        try:
            last = datetime.datetime.fromisoformat(str(previous["requested_at"]).replace("Z", "+00:00"))
            if last.tzinfo is None:
                last = last.replace(tzinfo=datetime.timezone.utc)
            remaining = 900 - int((now - last).total_seconds())
            if remaining > 0:
                raise HTTPException(status_code=429, detail=f"Please wait {remaining // 60 + 1} minute(s) before syncing again.", headers={"Retry-After": str(remaining)})
        except ValueError:
            pass
    try:
        result = await sync_market_prices(crop=crop.strip(), state=state.strip(), district=district.strip() if district else None, max_pages=2, page_size=500)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Market provider is not configured or unavailable.") from exc
    except Exception as exc:
        logging.getLogger(__name__).error("Farmer market sync failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Market provider sync failed. Try again later.") from exc
    requests.update_one(key, {"$set": {"requested_at": now.isoformat(), "crop": crop.strip(), "state": state.strip(), "district": district}}, upsert=True)
    return {"success": True, "message": "Market sync completed.", "data": result}
