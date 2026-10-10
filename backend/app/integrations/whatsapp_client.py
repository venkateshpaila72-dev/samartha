"""WhatsApp alert delivery with farmer-profile language localization."""
import asyncio
import datetime
import logging
import uuid

from app.core.config import settings
from app.db.collection_names import NOTIFICATION_LOGS_COLLECTION
from app.db.mongo import get_db
from app.integrations.azure_translator_client import AzureTranslatorClient

logger = logging.getLogger(__name__)
_IN_MEMORY_NOTIF_LOGS: list[dict] = []


class WhatsAppClient:
    """Twilio WhatsApp client; messages follow the recipient's saved language."""

    @classmethod
    def is_configured(cls) -> bool:
        sid = settings.TWILIO_ACCOUNT_SID.strip()
        token = settings.TWILIO_AUTH_TOKEN.strip()
        sender = settings.TWILIO_WHATSAPP_FROM.strip()
        return bool(sid and token and sender and not sid.startswith("your_"))

    @classmethod
    async def send_alert_notification(
        cls, phone_number: str, crop_name: str, condition_type: str,
        measured_value: float, unit: str, recommended_action: str, batch_id: str,
        preferred_language: str = "en", traditional_guidance: str = "",
    ) -> bool:
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        log_id = f"notif_{uuid.uuid4().hex[:10]}"
        lang = (preferred_language or "en").lower().split("-")[0]
        if lang not in {"en", "hi", "te", "ta", "kn", "mr", "pa", "bn"}:
            lang = "en"

        message_body = (
            f"🌾 FARMSHIELD ALERT 🌾\n\n"
            f"Batch: {crop_name} (ID: {batch_id})\n"
            f"Condition: {condition_type.replace('_', ' ').upper()}\n"
            f"Reading: {measured_value} {unit}\n\n"
            f"Technical action: {recommended_action}\n\n"
            f"Traditional storage guidance: {traditional_guidance or 'Use the verified crop-specific storage guidance in your FarmShield dashboard.'}\n\n"
            f"Check your FarmShield dashboard for updates."
        )
        if lang != "en":
            try:
                message_body = await AzureTranslatorClient.translate_text(
                    text=message_body, target_lang=lang, source_lang="en"
                )
            except Exception:
                logger.exception("WhatsApp translation failed; sending English fallback")

        status = "credentials_missing"
        err_msg = "Twilio credentials are not configured in environment."
        sid_or_id = None
        if cls.is_configured():
            try:
                from twilio.rest import Client
                account_sid = settings.TWILIO_ACCOUNT_SID.strip()
                auth_token = settings.TWILIO_AUTH_TOKEN.strip()
                from_num = settings.TWILIO_WHATSAPP_FROM.strip()
                if not from_num.startswith("whatsapp:"):
                    from_num = f"whatsapp:{from_num}"
                to_num = phone_number.strip()
                if not to_num.startswith("whatsapp:"):
                    to_num = f"whatsapp:{to_num}"

                def _send_sync():
                    client = Client(account_sid, auth_token)
                    msg = client.messages.create(body=message_body, from_=from_num, to=to_num)
                    return msg.sid, msg.status

                msg_sid, msg_status = await asyncio.to_thread(_send_sync)
                sid_or_id = msg_sid
                status = msg_status.lower() if msg_status else "sent"
                err_msg = None
            except Exception as exc:
                status = "provider_error"
                err_msg = str(exc)
                logger.error("Twilio WhatsApp notification failed: %s", exc)

        log_doc = {
            "log_id": log_id, "batch_id": batch_id,
            "recipient_masked": phone_number[:4] + "****" if len(phone_number) > 4 else "unknown",
            "provider": "Twilio", "message_sid": sid_or_id, "status": status,
            "error": err_msg, "language": lang, "created_at": now_iso,
        }
        _IN_MEMORY_NOTIF_LOGS.append(log_doc.copy())
        db = get_db()
        if db is not None:
            try:
                db[NOTIFICATION_LOGS_COLLECTION].insert_one(log_doc.copy())
            except Exception as db_err:
                logger.warning("Could not persist notification log: %s", db_err)
        logger.info("WhatsApp alert status=%s batch=%s language=%s", status, batch_id, lang)
        return status in {"delivered", "queued", "sent", "accepted"}
