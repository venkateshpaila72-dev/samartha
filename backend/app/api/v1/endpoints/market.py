"""Agricultural Market Price Endpoints."""

from typing import Optional
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Security, status

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


from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.api.dependencies import get_current_user, get_owned_batch, security_scheme
from app.core.security import decode_access_token
from app.repositories.user_repository import UserRepository


async def get_current_user_or_sync_secret(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    sync_secret: Optional[str] = Header(None, alias="X-Market-Sync-Secret"),
) -> dict:
    configured_secret = settings.MARKET_SYNC_SECRET.strip()
    if sync_secret and configured_secret and hmac.compare_digest(sync_secret, configured_secret):
        return {"role": "scheduler", "preferred_language": "en"}

    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and payload.get("sub"):
            user = UserRepository.get_by_id(payload["sub"])
            if user:
                return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please log in or provide a valid market sync secret.",
    )


import datetime
from app.core.state_normalizer import normalize_state_name


@router.post("/market/sync", tags=["Market Prices"])
async def sync_market_data(
    crop: Optional[str] = Query(None, min_length=1, max_length=100),
    state: Optional[str] = Query(None, max_length=100),
    district: Optional[str] = Query(None, max_length=100),
    max_pages: int = Query(10, ge=1, le=100),
    caller: dict = Depends(get_current_user_or_sync_secret),
):
    """Sync today's market prices for a crop into the database.

    Strictly restricted to the farmer's profile state. Nationwide sync is disallowed.
    """
    if caller.get("role") != "scheduler":
        user_state = caller.get("state")
        if not user_state or not str(user_state).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Farmer state is not configured in your profile. Please set your state in your profile or detect your location before synchronizing market prices.",
            )
        sync_state = normalize_state_name(user_state)
        sync_district = district or caller.get("district")
        sync_crop = crop or caller.get("selected_crop")
    else:
        if not state or not str(state).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="State parameter is required for scheduled synchronization. Nationwide sync is not permitted.",
            )
        sync_state = normalize_state_name(state)
        sync_district = district
        sync_crop = crop

    try:
        sync_result = await sync_market_prices(
            crop=sync_crop, state=sync_state, district=sync_district, max_pages=max_pages
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Market-price ingestion failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Market provider ingestion failed. Check backend logs for the provider error.",
        ) from exc

    # Update user's last synchronization timestamp and summary
    if caller.get("id"):
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        UserRepository.update(caller["id"], {
            "last_market_sync_at": now_iso,
            "last_market_sync_summary": sync_result,
        })

    report = None
    if sync_crop and sync_crop.strip():
        report = await FarmShieldAgent.market_advisory(
            crop_name=sync_crop.strip(),
            language=caller.get("preferred_language", "en"),
            state=sync_state,
            district=sync_district,
        )

    return APIResponse(
        success=True,
        message=f"Market data synced successfully for {sync_crop or 'agricultural crops'} in {sync_state}.",
        data={"sync_result": sync_result, "report": report},
    )


@router.post("/batches/{batch_id}/market/sync", tags=["Market Prices"])
async def sync_batch_market_prices(
    batch_id: str,
    state: Optional[str] = Query(None, max_length=100),
    district: Optional[str] = Query(None, max_length=100),
    current_user: dict = Depends(get_current_user),
):
    """Sync today's market prices for a storage batch's assigned crop."""
    batch = get_owned_batch(batch_id, current_user)
    crop_doc = CropRepository.get_by_id(batch.get("crop_id", ""))
    crop_name = crop_doc.get("crop_name") if crop_doc else batch.get("custom_batch_name")

    if not crop_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected batch does not have a crop assigned.",
        )

    user_state = current_user.get("state")
    if not user_state or not str(user_state).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Farmer state is not configured in your profile. Please configure your state before syncing batch market prices.",
        )
    sync_state = normalize_state_name(user_state)
    sync_district = district or current_user.get("district")

    sync_result = await sync_market_prices(
        crop=crop_name, state=sync_state, district=sync_district
    )
    report = await FarmShieldAgent.market_advisory(
        crop_name=crop_name,
        language=current_user.get("preferred_language", "en"),
        state=sync_state,
        district=sync_district,
    )
    return APIResponse(
        success=True,
        message=f"Market data synced successfully for batch crop '{crop_name}' in {sync_state}.",
        data={"sync_result": sync_result, "report": report},
    )

