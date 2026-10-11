"""FarmShield API v1 Main Router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    alerts,
    auth,
    chatbot,
    crop_profiles,
    diary,
    health,
    market,
    sensor_readings,
    speech,
    storage_batches,
    translation,
    uploads,
    weather,
    restaurant_management,
    orchard_management,
)

api_router = APIRouter(prefix="/api/v1")

# Include all sub-routers
api_router.include_router(auth.router)
api_router.include_router(crop_profiles.router)
api_router.include_router(storage_batches.router)
api_router.include_router(sensor_readings.router)
api_router.include_router(diary.router)
api_router.include_router(chatbot.router)
api_router.include_router(alerts.router)
api_router.include_router(weather.router)
api_router.include_router(market.router)
api_router.include_router(translation.router)
api_router.include_router(speech.router)
api_router.include_router(uploads.router)
api_router.include_router(admin.router)
api_router.include_router(health.router)
api_router.include_router(restaurant_management.router)
api_router.include_router(orchard_management.router)
