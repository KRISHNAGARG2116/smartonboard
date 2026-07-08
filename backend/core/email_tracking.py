import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.email import SentEmail
from models.integration_audit_log import IntegrationAuditLog

logger = logging.getLogger(__name__)

# 1x1 Transparent GIF bytes
TRANSPARENT_GIF = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
)


class EmailTrackingService:
    @classmethod
    def track_open(cls, db: Session, sent_email_id: uuid.UUID) -> bytes:
        """Increments open count and returns transparent pixel bytes."""
        sent_email = db.get(SentEmail, sent_email_id)
        if sent_email:
            sent_email.open_count += 1
            sent_email.updated_at = datetime.now(timezone.utc)
            db.add(sent_email)
            db.commit()
            logger.info(f"Email open tracked: SentEmail {sent_email_id} (count: {sent_email.open_count})")
        return TRANSPARENT_GIF

    @classmethod
    def track_click(cls, db: Session, sent_email_id: uuid.UUID, target_url: str) -> str:
        """Increments click count and returns redirect URL."""
        sent_email = db.get(SentEmail, sent_email_id)
        if sent_email:
            sent_email.click_count += 1
            sent_email.updated_at = datetime.now(timezone.utc)
            db.add(sent_email)
            db.commit()
            logger.info(f"Email click tracked: SentEmail {sent_email_id} -> {target_url} (count: {sent_email.click_count})")
        return target_url

    @classmethod
    def handle_webhook(cls, db: Session, provider: str, payload: dict):
        """Processes delivery and bounce events from provider webhook payloads."""
        event_type = payload.get("event") or payload.get("type")
        recipient = payload.get("email") or payload.get("recipient")
        message_id = payload.get("message_id")

        logger.info(f"Received email provider webhook: {provider} -> {event_type} for {recipient}")

        # Scan for matching SentEmail
        stmt = select(SentEmail).where(SentEmail.recipient == recipient).order_by(SentEmail.created_at.desc())
        sent_email = db.scalars(stmt).first()

        if sent_email:
            # Map events to status types: delivered, deferred, soft_bounce, hard_bounce, complaint, unsubscribe
            if event_type in ("delivered", "delivery"):
                sent_email.status = "delivered"
            elif event_type in ("bounce", "hard_bounce"):
                sent_email.status = "hard_bounce"
            elif event_type in ("soft_bounce", "transient"):
                sent_email.status = "soft_bounce"
            elif event_type in ("complaint", "spam"):
                sent_email.status = "complaint"
            elif event_type in ("unsubscribe", "opt_out"):
                sent_email.status = "unsubscribe"
            elif event_type in ("deferred", "delay"):
                sent_email.status = "deferred"

            sent_email.updated_at = datetime.now(timezone.utc)
            db.add(sent_email)

            # Log to integration audits
            audit = IntegrationAuditLog(
                company_id=sent_email.company_id,
                integration_type="email",
                action=f"email.{sent_email.status}",
                status="success",
                details_json={"recipient": recipient, "provider": provider, "event_type": event_type}
            )
            db.add(audit)
            db.commit()
            logger.info(f"Updated SentEmail {sent_email.id} status to '{sent_email.status}'")
        else:
            logger.warning(f"No SentEmail matched webhook recipient: {recipient}")
