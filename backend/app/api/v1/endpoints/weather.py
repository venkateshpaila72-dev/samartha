"""Weather API Endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user, get_owned_batch
from app.integrations.weather_client import WeatherClient
from app.schemas.common import APIResponse
from app.schemas.weather import WeatherReportOut

router = APIRouter(tags=["Weather Forecast"])


@router.get("/weather", response_model=APIResponse[WeatherReportOut])
async def get_general_weather(
    location: Optional[str] = Query(None, description="City/Location name to forecast"),
    current_user: dict = Depends(get_current_user),
):
    # Prioritize user-provided search location over profile default (fixes M1)
    target_loc = (location.strip() if location and location.strip() else None) or current_user.get("village_or_location") or "New Delhi, IN"
    try:
        weather = await WeatherClient.get_weather(location=target_loc)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Weather service temporarily unavailable: {str(e)}",
        )

    return APIResponse(
        success=True,
        message=f"Weather forecast for '{target_loc}' retrieved.",
        data=weather,
    )


@router.get("/batches/{batch_id}/weather", response_model=APIResponse[WeatherReportOut])
async def get_batch_weather(
    batch_id: str,
    current_user: dict = Depends(get_current_user),
):
    # Enforce batch ownership (fixes H4)
    batch = get_owned_batch(batch_id, current_user)

    loc = batch.get("storage_location") or current_user.get("village_or_location") or "New Delhi, IN"
    try:
        weather = await WeatherClient.get_weather(location=loc)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage location '{loc}' could not be resolved: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Weather service temporarily unavailable: {str(e)}",
        )

    return APIResponse(
        success=True,
        message=f"Weather forecast for storage batch location '{loc}' retrieved.",
        data=weather,
    )
