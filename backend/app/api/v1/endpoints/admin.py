"""Admin Portal Management and System Status Endpoints."""

import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_current_admin
from app.core.config import settings
from app.db.collection_names import NOTIFICATION_LOGS_COLLECTION
from app.db.mongo import MongoDBManager, get_db
from app.repositories.alert_repository import AlertRepository
from app.repositories.crop_repository import CropRepository
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import APIResponse

router = APIRouter(prefix="/admin", tags=["Admin Management"])


class IntegrationStatus(BaseModel):
    name: str
    status: str  # configured, pending_credentials, unavailable
    provider: str
    is_operational: bool
    notes: str


class AdminDashboardSummary(BaseModel):
    total_farmers: int
    total_crop_profiles: int
    total_active_batches: int
    total_active_alerts: int
    database_connected: bool
    database_name: str
    integrations: list[IntegrationStatus]
    recent_notification_logs: list[dict]
    system_time: str


@router.get("/dashboard", response_model=APIResponse[AdminDashboardSummary])
async def get_admin_dashboard(current_admin: dict = Depends(get_current_admin)):
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db_connected = MongoDBManager.is_healthy()

    users = UserRepository.list_all(limit=1000)
    farmers_count = len([u for u in users if u.get("role") == "farmer"])
    crops_count = CropRepository.count()
    batches = StorageBatchRepository.list_all()
    active_batches = len([b for b in batches if b.get("status") == "active"])
    active_alerts = len(AlertRepository.list_all(status="active"))

    # Check external integrations (safely without revealing secret keys)
    def check_secret(val: str) -> bool:
        return bool(val and not val.strip().startswith("your_"))

    integrations = [
        IntegrationStatus(
            name="MongoDB Database",
            status="healthy" if db_connected else "disconnected",
            provider="MongoDB",
            is_operational=db_connected,
            notes=f"Connected to {settings.MONGODB_DATABASE}" if db_connected else "Running in fallback mode",
        ),
        IntegrationStatus(
            name="Groq LLM Reasoning",
            status="configured" if check_secret(settings.GROQ_API_KEY) else "pending_credentials",
            provider=f"Groq ({settings.GROQ_MODEL})",
            is_operational=check_secret(settings.GROQ_API_KEY),
            notes="Active for intelligent advisory" if check_secret(settings.GROQ_API_KEY) else "Using intelligent structured fallback",
        ),
        IntegrationStatus(
            name="RAG Traditional Knowledge",
            status="active",
            provider="In-Memory Vector Knowledge Base",
            is_operational=True,
            notes="Loaded verified ICAR/CFTRI traditional methods",
        ),
        IntegrationStatus(
            name="Weather Forecast API",
            status="configured" if check_secret(settings.WEATHER_API_KEY) else "pending_credentials",
            provider="OpenWeatherMap",
            is_operational=check_secret(settings.WEATHER_API_KEY),
            notes="Live forecast active" if check_secret(settings.WEATHER_API_KEY) else "Using simulated seasonal weather",
        ),
        IntegrationStatus(
            name="Agricultural Market Prices",
            status="configured" if check_secret(settings.MARKET_API_KEY) else "benchmark_active",
            provider="AGMARKNET / DMI APMC Benchmarks",
            is_operational=True,
            notes="Real APMC market benchmark records active",
        ),
        IntegrationStatus(
            name="Azure Translator",
            status="configured" if check_secret(settings.AZURE_TRANSLATOR_KEY) else "pending_credentials",
            provider="Microsoft Azure Cognitive Services",
            is_operational=check_secret(settings.AZURE_TRANSLATOR_KEY),
            notes="Live cloud translation" if check_secret(settings.AZURE_TRANSLATOR_KEY) else "Using offline multilingual agricultural glossary",
        ),
        IntegrationStatus(
            name="WhatsApp Notifications",
            status="configured" if check_secret(settings.WHATSAPP_API_TOKEN) else "pending_credentials",
            provider=settings.WHATSAPP_PROVIDER.capitalize(),
            is_operational=check_secret(settings.WHATSAPP_API_TOKEN),
            notes="Direct WhatsApp alert dispatch" if check_secret(settings.WHATSAPP_API_TOKEN) else "Alert logging active; pending WhatsApp token",
        ),
    ]

    # Fetch notification logs
    notif_logs = []
    db = get_db()
    if db is not None:
        try:
            logs = list(db[NOTIFICATION_LOGS_COLLECTION].find().sort("created_at", -1).limit(10))
            for l in logs:
                l.pop("_id", None)
            notif_logs = logs
        except Exception:
            pass

    return APIResponse(
        success=True,
        message="Admin system monitoring dashboard data retrieved.",
        data=AdminDashboardSummary(
            total_farmers=farmers_count,
            total_crop_profiles=crops_count,
            total_active_batches=active_batches,
            total_active_alerts=active_alerts,
            database_connected=db_connected,
            database_name=settings.MONGODB_DATABASE,
            integrations=integrations,
            recent_notification_logs=notif_logs,
            system_time=now_iso,
        ),
    )


@router.get("/users", response_model=APIResponse[list[dict]])
async def list_registered_users(current_admin: dict = Depends(get_current_admin)):
    users = UserRepository.list_all(limit=100)
    # Strip password hash before returning
    safe_users = []
    for u in users:
        u_copy = u.copy()
        u_copy.pop("password_hash", None)
        safe_users.append(u_copy)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(safe_users)} users.",
        data=safe_users,
    )
