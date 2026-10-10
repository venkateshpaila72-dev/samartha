"""Weather API Endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user
from app.integrations.weather_client import WeatherClient
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.schemas.common import APIResponse
from app.schemas.weather import WeatherReportOut

router = APIRouter(tags=["Weather Forecast"])


@router.get("/weather", response_model=APIResponse[WeatherReportOut])
async def get_general_weather(
    location: str = Query("New Delhi, IN", description="City/Location name"),
    current_user: dict = Depends(get_current_user),
):
    user_loc = current_user.get("village_or_location") or location
    weather = await WeatherClient.get_weather(location=user_loc)
    return APIResponse(
        success=True,
        message="Weather forecast retrieved.",
        data=weather,
    )


@router.get("/batches/{batch_id}/weather", response_model=APIResponse[WeatherReportOut])
async def get_batch_weather(
    batch_id: str,
    current_user: dict = Depends(get_current_user),
):
    batch = StorageBatchRepository.get_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage batch not found.")

    loc = batch.get("storage_location", "Farm Main Granary")
    weather = await WeatherClient.get_weather(location=loc)
    return APIResponse(
        success=True,
        message=f"Weather forecast for storage batch location '{loc}' retrieved.",
        data=weather,
    )
