import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
import requests
from sqlalchemy import select, delete

from core.celery_app import celery_app
from core.vault import SecretVaultService
from core.audit import log_audit_event
from db.session import tenant_context, SessionLocal
from models.webhook import WebhookSubscription, WebhookDeliveryLog
from schemas.webhook import is_ssrf_safe_url

logger = logging.getLogger("celery")

MAX_PAYLOAD_SIZE_BYTES = 1024 * 1024 # 1MB Limit


@celery_app.task(bind=True, max_retries=5)
def dispatch_webhook_event_task(self, company_id: str, event_type: str, payload: dict):
    """
    Asynchronously queries active webhook subscriptions, validates payload constraints
    and destination URLs, signs payloads via HMAC-SHA256, and dispatches POST payloads.
    Increments consecutive failures and suspends subscriptions (circuit breaker) if needed.
    """
    retry_cnt = self.request.retries
    now = datetime.now(timezone.utc)

    # Calculate payload size
    payload_str = json.dumps(payload)
    payload_size = len(payload_str.encode("utf-8"))

    with tenant_context(tenant_id=company_id):
        db = SessionLocal()
        try:
            # Enforce unique triggered event quota (retries excluded)
            if retry_cnt == 0:
                from core.quota import increment_quota_usage
                increment_quota_usage(db, uuid.UUID(company_id), "webhooks_dispatched")

            # Query all active subscriptions for this company
            stmt = select(WebhookSubscription).where(
                WebhookSubscription.company_id == uuid.UUID(company_id),
                WebhookSubscription.status == "active"
            )
            subscriptions = db.scalars(stmt).all()

            for sub in subscriptions:
                # Check if subscribed to this event type
                if event_type not in sub.active_events:
                    continue

                # Circuit breaker check: check temporary suspensions
                if sub.disabled_until and sub.disabled_until > now:
                    logger.info(f"Skipping dispatch for suspended subscription {sub.id} (Circuit open).")
                    continue

                # SSRF Protection: Double check url at dispatch time
                if not is_ssrf_safe_url(sub.url):
                    logger.warning(f"Blocked webhook dispatch to SSRF-vulnerable host: {sub.url}")
                    # Log delivery failure instantly
                    log_failed_attempt(
                        db=db,
                        sub=sub,
                        event_type=event_type,
                        payload=payload,
                        status_code=400,
                        body="SSRF Protection: Blocked localhost or private network destination.",
                        elapsed=0.0,
                        attempt=retry_cnt + 1
                    )
                    continue

                # Payload Size check (minor hardening refinement)
                if payload_size > MAX_PAYLOAD_SIZE_BYTES:
                    logger.warning(f"Blocked webhook dispatch. Payload size ({payload_size} bytes) exceeds 1MB limit.")
                    log_failed_attempt(
                        db=db,
                        sub=sub,
                        event_type=event_type,
                        payload=payload,
                        status_code=413,
                        body=f"Payload Too Large: Size ({payload_size} bytes) exceeds 1MB limit.",
                        elapsed=0.0,
                        attempt=retry_cnt + 1
                    )
                    continue

                # Signature preparation
                vault = SecretVaultService()
                # Reconstruct encrypted JSON envelope to decrypt
                envelope = {
                    "ciphertext": sub.encrypted_secret,
                    "iv": sub.iv,
                    "tag": sub.tag,
                    "key_version": sub.key_version
                }
                raw_secret = vault.decrypt_secret(json.dumps(envelope))

                t = int(time.time())
                signature_msg = f"t={t}.{payload_str}"
                sig = hmac.new(
                    raw_secret.encode("utf-8"),
                    msg=signature_msg.encode("utf-8"),
                    digestmod=hashlib.sha256
                ).hexdigest()

                headers = {
                    "Content-Type": "application/json",
                    "X-SmartOnboard-Signature": f"t={t},v1={sig}",
                    "User-Agent": "SmartOnboard-Webhook-Dispatcher/1.0"
                }

                # HTTP delivery dispatch with timeout
                start_time = time.time()
                try:
                    response = requests.post(sub.url, json=payload, headers=headers, timeout=10)
                    elapsed = time.time() - start_time

                    if response.status_code >= 200 and response.status_code < 300:
                        # Success
                        sub.consecutive_failures = 0
                        sub.disabled_until = None
                        db.add(sub)

                        # Write delivery log
                        log_success_attempt(db, sub, event_type, payload, response.status_code, elapsed)
                    else:
                        # Response error code
                        elapsed = time.time() - start_time
                        handle_failed_attempt(
                            db=db,
                            sub=sub,
                            event_type=event_type,
                            payload=payload,
                            status_code=response.status_code,
                            body=response.text[:2000],
                            elapsed=elapsed,
                            attempt=retry_cnt + 1,
                            task_self=self,
                            exc=ValueError(f"Webhook receiver returned HTTP {response.status_code}")
                        )
                except requests.RequestException as req_exc:
                    # Connection / Timeout error
                    elapsed = time.time() - start_time
                    handle_failed_attempt(
                        db=db,
                        sub=sub,
                        event_type=event_type,
                        payload=payload,
                        status_code=None,
                        body=str(req_exc),
                        elapsed=elapsed,
                        attempt=retry_cnt + 1,
                        task_self=self,
                        exc=req_exc
                    )

            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error(f"Error executing dispatch_webhook_event_task: {exc}")
            raise exc
        finally:
            db.close()


def log_success_attempt(db, sub, event_type: str, payload: dict, status_code: int, elapsed: float):
    delivery_log = WebhookDeliveryLog(
        company_id=sub.company_id,
        subscription_id=sub.id,
        event_type=event_type,
        payload=payload,
        attempt_number=1,
        response_status=status_code,
        response_body="Success",
        elapsed_seconds=round(elapsed, 3),
    )
    db.add(delivery_log)
    db.flush()

    # Log audit event
    log_audit_event(
        db=db,
        action="webhook.delivery_success",
        actor_type="SYSTEM",
        company_id=sub.company_id,
        resource_type="webhook_delivery_logs",
        resource_id=str(delivery_log.id),
        metadata={
            "subscription_id": str(sub.id),
            "event_type": event_type,
            "status_code": status_code,
            "elapsed_seconds": round(elapsed, 3)
        }
    )


def log_failed_attempt(db, sub, event_type: str, payload: dict, status_code: int | None, body: str, elapsed: float, attempt: int):
    delivery_log = WebhookDeliveryLog(
        company_id=sub.company_id,
        subscription_id=sub.id,
        event_type=event_type,
        payload=payload,
        attempt_number=attempt,
        response_status=status_code,
        response_body=body[:2000],
        elapsed_seconds=round(elapsed, 3),
    )
    db.add(delivery_log)
    db.flush()


def handle_failed_attempt(db, sub, event_type: str, payload: dict, status_code: int | None, body: str, elapsed: float, attempt: int, task_self, exc):
    # Log the failed try
    log_failed_attempt(db, sub, event_type, payload, status_code, body, elapsed, attempt)

    # Increment failures
    sub.consecutive_failures += 1
    db.add(sub)
    db.flush()

    if sub.consecutive_failures >= 10:
        # Trip the circuit breaker!
        sub.disabled_until = datetime.now(timezone.utc) + timedelta(hours=1)
        db.add(sub)
        db.flush()

        # Emit audit log for circuit opened
        log_audit_event(
            db=db,
            action="webhook.circuit_opened",
            actor_type="SYSTEM",
            company_id=sub.company_id,
            resource_type="webhook_subscriptions",
            resource_id=str(sub.id),
            metadata={
                "subscription_id": str(sub.id),
                "consecutive_failures": sub.consecutive_failures,
                "disabled_until": sub.disabled_until.isoformat(),
            }
        )

    # Trigger Celery retry with backoff if attempts remain
    if attempt < 5:
        db.commit() # Save state before retrying
        countdown = (2 ** attempt) * 15 # backoff: 30s, 60s, 120s, 240s
        logger.warning(f"Webhook dispatch failed (attempt {attempt}/5). Retrying in {countdown}s...")
        raise task_self.retry(exc=exc, countdown=countdown)
    else:
        # Permanent failure
        log_audit_event(
            db=db,
            action="webhook.delivery_failed",
            actor_type="SYSTEM",
            company_id=sub.company_id,
            resource_type="webhook_subscriptions",
            resource_id=str(sub.id),
            metadata={
                "subscription_id": str(sub.id),
                "event_type": event_type,
                "consecutive_failures": sub.consecutive_failures,
                "error_message": body[:200]
            }
        )


@celery_app.task
def purge_expired_delivery_logs():
    """
    Scheduled Celery task executing daily to purge delivery logs older than 30 days.
    """
    # Run under global bypass system context to prune historical log rows
    with tenant_context(auth_mode="true"):
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            retention_boundary = now - timedelta(days=30)

            stmt = delete(WebhookDeliveryLog).where(
                WebhookDeliveryLog.executed_at < retention_boundary
            )
            result = db.execute(stmt)
            db.commit()

            deleted_count = result.rowcount
            logger.info(f"Purged {deleted_count} expired webhook delivery logs (30-day retention).")
            return deleted_count
        except Exception as exc:
            db.rollback()
            logger.error(f"Failed to execute webhook delivery logs purge sweep: {exc}")
            raise exc
        finally:
            db.close()
