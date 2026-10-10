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
    if settings.APP_ENV != "test":
        db = MongoDBManager.connect()
        if db is not None:
            try:
                create_all_indexes(db)
            except Exception as e:
                logger.warning(f"Notice on index creation: {e}")
        else:
            if settings.APP_ENV == "production":
                raise RuntimeError(
                    f"Could not connect to MongoDB database at '{settings.MONGODB_URI}'. "
                    "A reachable MongoDB instance is required to start FarmShield in production."
                )
            else:
                logger.error(
                    f"Could not connect to MongoDB database at '{settings.MONGODB_URI}'. "
                    "API running in degraded state; database-dependent endpoints will return 503."
                )

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
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Mount API Routers
app.include_router(api_router)

# Mount local upload directory for media assets if present
import os
from fastapi.staticfiles import StaticFiles
os.makedirs(settings.STORAGE_UPLOAD_DIR, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=settings.STORAGE_UPLOAD_DIR), name="uploads")



@app.get("/", tags=["Root"])
def root():
    return {
        "app": "FarmShield",
        "description": "AI-Powered Crop Storage Monitoring & Agricultural Advisory Application",
        "docs": "/docs",
        "api_v1": "/api/v1",
        "status": "operational",
    }
