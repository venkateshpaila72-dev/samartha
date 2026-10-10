"""WhatsApp alert delivery with farmer-profile language localization and verified delivery tracking."""
import asyncio
import datetime
import logging
import uuid
from typing import Optional

from app.core.config import settings
from app.db.collection_names import NOTIFICATION_LOGS_COLLECTION
from app.db.mongo import get_db
from app.integrations.azure_translator_client import AzureTranslatorClient
from app.integrations.groq_client import GroqClient
from app.monitoring.rules import mask_phone_number, normalize_phone_number

logger = logging.getLogger(__name__)
_IN_MEMORY_NOTIF_LOGS: list[dict] = []


class WhatsAppDeliveryResult:
    """Encapsulates the delivery attempt result with boolean evaluation."""

    def __init__(
        self,
        success: bool,
        status: str,
        message_sid: Optional[str] = None,
        error: Optional[str] = None,
        recipient_masked: str = "unknown",
    ):
        self.success = success
        self.status = status
        self.message_sid = message_sid
        self.error = error
        self.recipient_masked = recipient_masked

    def __bool__(self) -> bool:
        return self.success

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "status": self.status,
            "message_sid": self.message_sid,
            "error": self.error,
            "recipient_masked": self.recipient_masked,
        }


class WhatsAppClient:
    """Twilio WhatsApp client; formats alerts with Groq AI or clean deterministic template,
    never leaks raw RAG or traditional research text, and tracks verified delivery.
    """

    @classmethod
    def is_configured(cls) -> bool:
        sid = settings.TWILIO_ACCOUNT_SID.strip()
        token = settings.TWILIO_AUTH_TOKEN.strip()
        sender = settings.TWILIO_WHATSAPP_FROM.strip()
        return bool(sid and token and sender and not sid.startswith("your_"))

    @classmethod
    def format_deterministic_storage_alert(
        cls,
        crop_name: str,
        batch_name: str,
        metric_name: str,
        metric_emoji: str,
        measured_value: float,
        unit: str,
        safe_limit_or_range_label: str,
        safe_limit_or_range_val: str,
        status_label: str,
        recommended_action: str,
        reading_time: Optional[str] = None,
    ) -> str:
        """Constructs a clean, deterministic WhatsApp alert template matching expected layout.
        Guarantees zero raw RAG text, research abstracts, or chunk citations.
        """
        lines = [
            "🚨 *FarmShield Storage Alert*",
            "",
            f"🌾 *Crop:* {crop_name}",
            f"📦 *Batch:* {batch_name}",
            "",
            f"{metric_emoji} *{metric_name}:* {measured_value:.1f}{unit}",
            f"✅ *{safe_limit_or_range_label}:* {safe_limit_or_range_val}",
            f"⚠️ *Status:* {status_label}",
        ]
        if reading_time:
            lines.append(f"⏱️ *Time:* {reading_time}")
        lines.extend([
            "",
            "*Recommended action:*",
            f"{recommended_action}",
            "",
            "Please monitor the storage conditions and follow the recommended safety procedure.",
        ])
        return "\n".join(lines)

    @classmethod
    async def send_alert_notification(
        cls,
        phone_number: Optional[str],
        crop_name: str,
        condition_type: str,
        measured_value: float,
        unit: str,
        recommended_action: str,
        batch_id: str,
        preferred_language: str = "en",
        batch_name: Optional[str] = None,
        severity: str = "warning",
        target_threshold: Optional[float] = None,
        target_range_min: Optional[float] = None,
        target_range_max: Optional[float] = None,
        alert_id: Optional[str] = None,
        is_sandbox_opted_in: Optional[bool] = None,
        reading_time: Optional[str] = None,
        # Backward compatibility for any remaining legacy callers
        traditional_guidance: Optional[str] = None,
    ) -> WhatsAppDeliveryResult:
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        log_id = f"notif_{uuid.uuid4().hex[:10]}"
        lang = (preferred_language or "en").lower().split("-")[0]
        if lang not in {"en", "hi", "te", "ta", "kn", "mr", "pa", "bn"}:
            lang = "en"

        # 1. Validate and normalize recipient phone number
        if not phone_number or not str(phone_number).strip():
            status = "missing_phone_number"
            err_msg = "Farmer profile does not have a registered WhatsApp phone number."
            logger.warning("WhatsApp alert skipped: %s (batch=%s)", err_msg, batch_id)
            result = WhatsAppDeliveryResult(False, status, None, err_msg, "Not provided")
            cls._record_log(log_id, batch_id, alert_id, "Not provided", None, status, err_msg, lang, now_iso)
            return result

        normalized_phone = normalize_phone_number(phone_number)
        masked_phone = mask_phone_number(normalized_phone or phone_number)

        if not normalized_phone:
            status = "invalid_phone_number"
            err_msg = f"Farmer phone number '{phone_number}' is not a valid E.164 phone number."
            logger.warning("WhatsApp alert skipped: %s (batch=%s)", err_msg, batch_id)
            result = WhatsAppDeliveryResult(False, status, None, err_msg, masked_phone)
            cls._record_log(log_id, batch_id, alert_id, masked_phone, None, status, err_msg, lang, now_iso)
            return result

        # 2. Check Twilio Sandbox opt-in if sandbox sender is in use
        sender_configured = settings.TWILIO_WHATSAPP_FROM.strip()
        is_sandbox_sender = "14155238886" in sender_configured

        if is_sandbox_sender and is_sandbox_opted_in is False:
            status = "sandbox_not_opted_in"
            err_msg = (
                f"Recipient {masked_phone} has not completed Twilio WhatsApp Sandbox opt-in. "
                f"Please send '{settings.TWILIO_WHATSAPP_JOIN_KEYWORD}' to "
                f"{sender_configured.replace('whatsapp:', '')} on WhatsApp."
            )
            logger.warning("WhatsApp alert skipped: %s (batch=%s)", err_msg, batch_id)
            result = WhatsAppDeliveryResult(False, status, None, err_msg, masked_phone)
            cls._record_log(log_id, batch_id, alert_id, masked_phone, None, status, err_msg, lang, now_iso)
            return result

        # 3. Derive verified parameter labels, emoji, and safe thresholds
        display_batch_name = batch_name or f"{crop_name} Batch"
        cond_label = condition_type.replace("_", " ").upper()

        metric_name = "Reading"
        metric_emoji = "📊"
        cond_lower = condition_type.lower()
        if "temperature" in cond_lower:
            metric_name = "Temperature"
            metric_emoji = "🌡️"
        elif "humidity" in cond_lower:
            metric_name = "Humidity"
            metric_emoji = "💧"
        elif "moisture" in cond_lower:
            metric_name = "Moisture"
            metric_emoji = "🌾"

        if target_range_min is not None and target_range_max is not None:
            if measured_value > target_range_max:
                limit_label = "Maximum safe limit"
                limit_val = f"{target_range_max:.1f}{unit}"
            elif measured_value < target_range_min:
                limit_label = "Minimum safe limit"
                limit_val = f"{target_range_min:.1f}{unit}"
            else:
                limit_label = "Safe range"
                limit_val = f"{target_range_min:.1f}{unit}–{target_range_max:.1f}{unit}"
        elif target_threshold is not None:
            limit_label = "Maximum safe limit" if "high" in cond_lower else "Minimum safe limit"
            limit_val = f"{target_threshold:.1f}{unit}"
        else:
            limit_label = "Safe threshold"
            limit_val = f"Verified scientific limits"

        # 4. Generate AI formatted message via Groq with deterministic fallback
        message_body: Optional[str] = None
        try:
            message_body = await GroqClient.format_whatsapp_storage_alert(
                crop_name=crop_name,
                batch_name=display_batch_name,
                metric_name=metric_name,
                metric_emoji=metric_emoji,
                measured_value=measured_value,
                unit=unit,
                safe_limit_or_range_label=limit_label,
                safe_limit_or_range_val=limit_val,
                status_label=cond_label,
                severity=severity,
                recommended_action=recommended_action,
                reading_time=reading_time,
            )
        except Exception as ai_err:
            logger.warning("Groq AI WhatsApp alert generation error: %s", ai_err)
            message_body = None

        # Clean fallback if AI fails or returns empty/invalid text
        if not message_body:
            message_body = cls.format_deterministic_storage_alert(
                crop_name=crop_name,
                batch_name=display_batch_name,
                metric_name=metric_name,
                metric_emoji=metric_emoji,
                measured_value=measured_value,
                unit=unit,
                safe_limit_or_range_label=limit_label,
                safe_limit_or_range_val=limit_val,
                status_label=cond_label,
                recommended_action=recommended_action,
                reading_time=reading_time,
            )

        # Enforce that raw RAG text is NEVER included in WhatsApp messages
        lower_body = message_body.lower()
        if "traditional guidance" in lower_body or "agricultural research record" in lower_body or "sar-" in lower_body:
            logger.warning("Detected forbidden RAG tokens in generated alert body; replacing with deterministic fallback.")
            message_body = cls.format_deterministic_storage_alert(
                crop_name=crop_name,
                batch_name=display_batch_name,
                metric_name=metric_name,
                metric_emoji=metric_emoji,
                measured_value=measured_value,
                unit=unit,
                safe_limit_or_range_label=limit_label,
                safe_limit_or_range_val=limit_val,
                status_label=cond_label,
                recommended_action=recommended_action,
                reading_time=reading_time,
            )

        # 4. Localize message into farmer's preferred language with safe fallback
        if lang != "en":
            try:
                translated = await AzureTranslatorClient.translate_text(
                    text=message_body, target_lang=lang, source_lang="en"
                )
                if translated and translated.strip():
                    message_body = translated
            except Exception as exc:
                logger.warning("WhatsApp translation to %s failed; using English fallback: %s", lang, exc)

        # 5. Dispatch via Twilio REST client
        status = "credentials_missing"
        err_msg = "Twilio credentials are not configured in backend environment."
        sid_or_id = None

        if cls.is_configured():
            try:
                from twilio.rest import Client

                account_sid = settings.TWILIO_ACCOUNT_SID.strip()
                auth_token = settings.TWILIO_AUTH_TOKEN.strip()
                from_num = sender_configured
                if not from_num.startswith("whatsapp:"):
                    from_num = f"whatsapp:{from_num}"
                to_num = normalized_phone
                if not to_num.startswith("whatsapp:"):
                    to_num = f"whatsapp:{to_num}"

                def _send_sync():
                    client = Client(account_sid, auth_token)
                    extra_kwargs = {}
                    if settings.PUBLIC_BASE_URL and not settings.PUBLIC_BASE_URL.startswith("http://localhost"):
                        extra_kwargs["status_callback"] = (
                            f"{settings.PUBLIC_BASE_URL.rstrip('/')}/api/v1/alerts/twilio-callback"
                        )
                    msg = client.messages.create(
                        body=message_body,
                        from_=from_num,
                        to=to_num,
                        **extra_kwargs,
                    )
                    return msg.sid, msg.status

                msg_sid, msg_status = await asyncio.to_thread(_send_sync)
                sid_or_id = msg_sid
                status = msg_status.lower() if msg_status else "accepted"
                err_msg = None
            except Exception as exc:
                exc_str = str(exc)
                exc_code = getattr(exc, "code", None)
                if exc_code in (63015, 21608) or "sandbox" in exc_str.lower() or "channel could not find a to address" in exc_str.lower():
                    status = "sandbox_not_opted_in"
                    err_msg = (
                        f"Twilio Sandbox opt-in required: recipient {masked_phone} has not joined the sandbox. "
                        f"Please send '{settings.TWILIO_WHATSAPP_JOIN_KEYWORD}' to "
                        f"{sender_configured.replace('whatsapp:', '')} on WhatsApp."
                    )
                elif exc_code == 21211:
                    status = "invalid_phone_number"
                    err_msg = f"Twilio rejected phone number {masked_phone} as invalid."
                else:
                    status = "failed"
                    err_msg = exc_str
                logger.error("Twilio WhatsApp notification failed: %s (code=%s)", exc_str, exc_code)

        cls._record_log(log_id, batch_id, alert_id, masked_phone, sid_or_id, status, err_msg, lang, now_iso)
        success = status in {"delivered", "queued", "sent", "accepted"}
        logger.info(
            "WhatsApp alert result: success=%s status=%s recipient=%s batch=%s",
            success,
            status,
            masked_phone,
            batch_id,
        )
        return WhatsAppDeliveryResult(success, status, sid_or_id, err_msg, masked_phone)

    @classmethod
    def _record_log(
        cls,
        log_id: str,
        batch_id: str,
        alert_id: Optional[str],
        recipient_masked: str,
        sid: Optional[str],
        status: str,
        error: Optional[str],
        lang: str,
        now_iso: str,
    ):
        log_doc = {
            "log_id": log_id,
            "batch_id": batch_id,
            "alert_id": alert_id,
            "recipient_masked": recipient_masked,
            "provider": "Twilio",
            "message_sid": sid,
            "status": status,
            "error": error,
            "language": lang,
            "created_at": now_iso,
        }
        _IN_MEMORY_NOTIF_LOGS.append(log_doc.copy())
        db = get_db()
        if db is not None:
            try:
                db[NOTIFICATION_LOGS_COLLECTION].insert_one(log_doc.copy())
            except Exception as db_err:
                logger.warning("Could not persist notification log: %s", db_err)
