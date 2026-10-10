"""Health and Readiness Check Endpoints."""

from fastapi import APIRouter
from app.db.mongo import MongoDBManager
from app.schemas.common import HealthStatus

router = APIRouter(tags=["System Health"])


@router.get("/health", response_model=HealthStatus)
async def health_check():
    db_ok = MongoDBManager.is_healthy()
    return HealthStatus(
        status="healthy" if db_ok else "degraded",
        database_connected=db_ok,
        version="1.0.0",
        services={
            "api": "healthy",
            "database": "connected" if db_ok else "disconnected",
            "rag": "active",
        },
    )


@router.get("/ready")
async def readiness_check():
    return {"ready": True, "app": "FarmShield API"}
