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

    from app.integrations.cloudinary_client import CloudinaryClient
    from app.integrations.rag_adapter import RAGAdapter
    from app.integrations.whatsapp_client import WhatsAppClient

    integrations = [
        IntegrationStatus(
            name="MongoDB Database",
            status="healthy" if db_connected else "disconnected",
            provider="MongoDB Atlas" if "mongodb.net" in settings.MONGODB_URI else "MongoDB Local",
            is_operational=db_connected,
            notes=f"Database '{settings.MONGODB_DATABASE}'" if db_connected else "Running in fallback mode",
        ),
        IntegrationStatus(
            name="Groq LLM Reasoning",
            status="configured" if check_secret(settings.GROQ_API_KEY) else "pending_credentials",
            provider=f"Groq ({settings.GROQ_MODEL})",
            is_operational=check_secret(settings.GROQ_API_KEY),
            notes="Active for intelligent storage advisory" if check_secret(settings.GROQ_API_KEY) else "Using structured fallback",
        ),
        IntegrationStatus(
            name="Pinecone Vector RAG",
            status="configured" if RAGAdapter.is_pinecone_configured() else "pending_credentials",
            provider=f"Pinecone (Index: {settings.PINECONE_INDEX_NAME})",
            is_operational=RAGAdapter.is_pinecone_configured(),
            notes="Connected to live vector index 'sar' + ICAR ITK repository" if RAGAdapter.is_pinecone_configured() else "Local ITK storage repository active",
        ),
        IntegrationStatus(
            name="Weather Forecast API",
            status="configured",
            provider="Open-Meteo",
            is_operational=True,
            notes="Live meteorological forecast & ambient storage analysis active",
        ),
        IntegrationStatus(
            name="Agricultural Market Prices",
            status="configured",
            provider="AGMARKNET (APMC Mandis)",
            is_operational=True,
            notes="Mandi arrival & modal price tracking active",
        ),
        IntegrationStatus(
            name="Azure Translator",
            status="configured" if check_secret(settings.AZURE_TRANSLATOR_KEY) else "pending_credentials",
            provider=f"Microsoft Azure Translator ({settings.AZURE_TRANSLATOR_REGION})",
            is_operational=check_secret(settings.AZURE_TRANSLATOR_KEY),
            notes="Live multilingual neural translation active" if check_secret(settings.AZURE_TRANSLATOR_KEY) else "Offline agricultural glossary active",
        ),
        IntegrationStatus(
            name="WhatsApp Notifications",
            status="configured" if WhatsAppClient.is_configured() else "pending_credentials",
            provider="Twilio WhatsApp",
            is_operational=WhatsAppClient.is_configured(),
            notes=f"Twilio sender {settings.TWILIO_WHATSAPP_FROM} configured" if WhatsAppClient.is_configured() else "Pending Twilio credentials",
        ),
        IntegrationStatus(
            name="Media & Image Storage",
            status="configured" if CloudinaryClient.is_configured() else "local_fallback",
            provider=f"Cloudinary ({settings.CLOUDINARY_CLOUD_NAME})" if CloudinaryClient.is_configured() else "Local File Storage",
            is_operational=True,
            notes="Cloud media uploads active" if CloudinaryClient.is_configured() else "Local disk storage active",
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
