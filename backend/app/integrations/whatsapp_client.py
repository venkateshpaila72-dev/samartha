"""WhatsApp Notification Client for FarmShield.
Sends alert notifications via WhatsApp Business API and maintains delivery logs.
"""

import datetime
import logging
import uuid
import httpx

from app.core.config import settings
from app.db.collection_names import NOTIFICATION_LOGS_COLLECTION
from app.db.mongo import get_db

logger = logging.getLogger(__name__)
_IN_MEMORY_NOTIF_LOGS: list[dict] = []


class WhatsAppClient:
    @classmethod
    async def send_alert_notification(
        cls,
        phone_number: str,
        crop_name: str,
        condition_type: str,
        measured_value: float,
        unit: str,
        recommended_action: str,
        batch_id: str,
    ) -> bool:
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        log_id = f"notif_{uuid.uuid4().hex[:10]}"
        api_token = settings.WHATSAPP_API_TOKEN.strip()
        phone_id = settings.WHATSAPP_PHONE_NUMBER_ID.strip()

        message_body = (
            f"🌾 *FARMSHIELD ALERT* 🌾\n\n"
            f"Batch: {crop_name} (ID: {batch_id})\n"
            f"Condition: *{condition_type.replace('_', ' ').upper()}*\n"
            f"Reading: *{measured_value} {unit}*\n\n"
            f"⚠️ Action Required:\n{recommended_action}\n\n"
            f"Check your FarmShield Dashboard for live updates."
        )

        status = "simulated_success"
        err_msg = None

        if api_token and phone_id and not api_token.startswith("your_"):
            try:
                url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
                headers = {
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "messaging_product": "whatsapp",
                    "to": phone_number,
                    "type": "text",
                    "text": {"body": message_body},
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code in [200, 201]:
                        status = "delivered"
                    else:
                        status = "provider_error"
                        err_msg = f"HTTP {resp.status_code}: {resp.text}"
            except Exception as e:
                status = "failed"
                err_msg = str(e)
        else:
            status = "pending_whatsapp_credentials"

        log_doc = {
            "log_id": log_id,
            "batch_id": batch_id,
            "recipient_masked": phone_number[:4] + "****" if len(phone_number) > 4 else "unknown",
            "provider": settings.WHATSAPP_PROVIDER,
            "status": status,
            "error": err_msg,
            "created_at": now_iso,
        }

        _IN_MEMORY_NOTIF_LOGS.append(log_doc.copy())
        db = get_db()
        if db is not None:
            db[NOTIFICATION_LOGS_COLLECTION].insert_one(log_doc.copy())

        logger.info(f"WhatsApp alert log recorded: status={status} for batch={batch_id}")
        return status in ["delivered", "simulated_success", "pending_whatsapp_credentials"]
