"""FarmShield FastAPI Main Application.
AI-powered crop storage monitoring and agricultural advisory backend.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.indexes import create_all_indexes
from app.db.mongo import MongoDBManager
from app.repositories.crop_repository import CropRepository

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("farmshield")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info("Initializing FarmShield API backend...")
    db = MongoDBManager.connect()
    if db is not None:
        try:
            create_all_indexes(db)
        except Exception as e:
            logger.warning(f"Notice on index creation: {e}")

    # Ensure crop database has seeded records
    seeded_count = CropRepository.count()
    logger.info(f"FarmShield Crop Storage Reference Database initialized with {seeded_count} verified profiles.")

    yield

    # Shutdown sequence
    logger.info("Shutting down FarmShield API backend...")
    MongoDBManager.close()


app = FastAPI(
    title="FarmShield API",
    description="AI-Powered Crop Storage Monitoring and Agricultural Advisory System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "app": "FarmShield",
        "description": "AI-Powered Crop Storage Monitoring & Agricultural Advisory Application",
        "docs": "/docs",
        "api_v1": "/api/v1",
        "status": "operational",
    }
