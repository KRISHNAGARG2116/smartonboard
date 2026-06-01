import hashlib
import json
import logging
import random
import time
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from core.celery_app import celery_app
from core.hris import HRISAdapterFactory
from core.audit import log_audit_event
from db.session import tenant_context, SessionLocal
from models import (
    Employee,
    CompanyHRISIntegration,
    OnboardingEventOutbox,
    EmployeeSyncHistory,
    DLQRecord,
    SyncMetric
)

logger = logging.getLogger("celery")


def record_sync_metric(db: Session, company_id: uuid.UUID, provider: str, name: str, value: float):
    """Logs sync metrics directly to the database."""
    metric = SyncMetric(
        company_id=company_id,
        provider=provider,
        metric_name=name,
        metric_value=value,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(metric)
    db.flush()


def log_sync_history_record(
    db: Session,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    provider: str,
    request_id: uuid.UUID,
    state: str,
    attempt: int,
    started_at: datetime,
    completed_at: datetime | None = None,
    duration_ms: int | None = None,
    error_message: str | None = None,
    payload_hash: str = ""
) -> EmployeeSyncHistory:
    """Creates a new sync history state record."""
    history = EmployeeSyncHistory(
        company_id=company_id,
        employee_id=employee_id,
        provider=provider,
        request_id=request_id,
        sync_state=state,
        attempt_number=attempt,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        error_message=error_message[:2000] if error_message else None,
        payload_hash=payload_hash,
        created_at=datetime.now(timezone.utc)
    )
    db.add(history)
    db.flush()
    return history


@celery_app.task
def sweep_onboarding_outbox_task():
    """
    Periodic sweep daemon task scanning for pending outbox entries.
    Employs concurrent row locking (SKIP LOCKED) to distribute jobs safely across parallel queues.
    """
    db = SessionLocal()
    try:
        # Run under RLS bypass context to find all pending events across tenants
        with tenant_context(auth_mode="true"):
            stmt = select(OnboardingEventOutbox).where(
                OnboardingEventOutbox.status == 'pending',
                OnboardingEventOutbox.event_type == 'employee.created'
            ).order_by(OnboardingEventOutbox.created_at.asc()).limit(50).with_for_update(skip_locked=True)
            
            pending_events = db.scalars(stmt).all()
            
            for event in pending_events:
                # 1. Update status to queued
                event.status = "queued"
                db.add(event)
                
                # Retrieve employee_id from payload
                payload = event.payload
                employee_id_str = payload.get("employee_id")
                
                if employee_id_str:
                    employee_id = uuid.UUID(employee_id_str)
                    emp = db.scalar(select(Employee).where(Employee.id == employee_id))
                    if emp:
                        emp.sync_status = "queued"
                        db.add(emp)
                        
                        # Find provider
                        integration = db.scalar(select(CompanyHRISIntegration).where(
                            CompanyHRISIntegration.company_id == event.company_id,
                            CompanyHRISIntegration.status == "active"
                        ))
                        provider = integration.provider if integration else "unknown"
                        
                        # Calculate payload hash
                        payload_str = json.dumps(payload, sort_keys=True)
                        p_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
                        
                        # Create sync history transition record
                        log_sync_history_record(
                            db=db,
                            company_id=event.company_id,
                            employee_id=employee_id,
                            provider=provider,
                            request_id=event.id,
                            state="queued",
                            attempt=1,
                            started_at=datetime.now(timezone.utc),
                            payload_hash=p_hash
                        )

                # Commit status update to release row locks before dispatching synchronous task
                db.commit()

                # Dispatch asynchronous sync task
                sync_employee_to_hris_task.delay(str(event.id))
    except Exception as exc:
        db.rollback()
        logger.error(f"Error sweeping outbox events: {exc}")
        raise exc
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=5)
def sync_employee_to_hris_task(self, outbox_id_str: str):
    """
    Executes the sync pipeline for an individual candidate-to-employee transition.
    Features formal state machine checks, envelope secret decryptions, retry jitter,
    circuit breaker validation, metrics capture, and DLQ routing.
    """
    outbox_id = uuid.UUID(outbox_id_str)
    attempt_num = self.request.retries + 1
    started_at = datetime.now(timezone.utc)
    
    # 1. Scrape outbox entry using global bypass context
    with tenant_context(auth_mode="true"):
        db = SessionLocal()
        try:
            outbox = db.scalar(select(OnboardingEventOutbox).where(OnboardingEventOutbox.id == outbox_id))
            if not outbox:
                logger.error(f"Outbox entry {outbox_id} not found.")
                return

            company_id = outbox.company_id
            payload = outbox.payload
            employee_id_str = payload.get("employee_id")
            
            if not employee_id_str:
                outbox.status = "failed"
                outbox.last_error = "Missing employee_id in payload"
                db.add(outbox)
                db.commit()
                return

            employee_id = uuid.UUID(employee_id_str)
            employee = db.scalar(select(Employee).where(Employee.id == employee_id))
            if not employee:
                outbox.status = "failed"
                outbox.last_error = f"Employee {employee_id} not found"
                db.add(outbox)
                db.commit()
                return

            # Resolve provider integration
            integration = db.scalar(select(CompanyHRISIntegration).where(
                CompanyHRISIntegration.company_id == company_id,
                CompanyHRISIntegration.status.in_(["active", "error"])
            ))
            
            if not integration:
                # No active integration
                outbox.status = "failed"
                outbox.last_error = "No active HRIS integration configured"
                employee.sync_status = "failed"
                employee.sync_error = outbox.last_error
                db.add(outbox)
                db.add(employee)
                db.commit()
                return

            provider = integration.provider
            payload_str = json.dumps(payload, sort_keys=True)
            p_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

            # 2. Transition states to processing
            outbox.status = "processing"
            employee.sync_status = "processing"
            db.add(outbox)
            db.add(employee)
            db.flush()

            log_sync_history_record(
                db=db,
                company_id=company_id,
                employee_id=employee_id,
                provider=provider,
                request_id=outbox.id,
                state="processing",
                attempt=attempt_num,
                started_at=started_at,
                payload_hash=p_hash
            )
            db.commit()

            # 3. Circuit Breaker validation
            # If the integration experienced consecutive errors and is cooling down
            cooldown_period = datetime.now(timezone.utc) - timedelta(minutes=5)
            if integration.status == "error" and integration.last_sync_at and integration.last_sync_at > cooldown_period:
                # Breaker is OPEN. Defer and retry task later
                logger.warning(f"Circuit Breaker open for provider {provider}. Sync deferred.")
                raise ValueError("HRIS Sync Deferred: Circuit Breaker Open")

            # 4. Initialize Adapter & Execute Provisioning
            try:
                adapter = HRISAdapterFactory.get_adapter(db, integration)
                
                # Fetch provider latency and provision worker
                res = adapter.provision_employee(employee)
                
                # Sync completed successfully!
                employee.hris_id = res["hris_id"]
                employee.sync_status = "synced"
                employee.sync_error = None
                
                outbox.status = "processed"
                outbox.last_error = None
                
                # Reset circuit breaker on success
                integration.status = "active"
                integration.last_sync_at = datetime.now(timezone.utc)
                integration.settings = {**integration.settings, "consecutive_failures": 0}
                
                db.add(employee)
                db.add(outbox)
                db.add(integration)
                db.flush()

                completed_at = datetime.now(timezone.utc)
                duration = int((completed_at - started_at).total_seconds() * 1000)

                log_sync_history_record(
                    db=db,
                    company_id=company_id,
                    employee_id=employee_id,
                    provider=provider,
                    request_id=outbox.id,
                    state="synced",
                    attempt=attempt_num,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=duration,
                    payload_hash=p_hash
                )

                # Record sync metrics
                queue_lag = (started_at - outbox.created_at).total_seconds()
                record_sync_metric(db, company_id, provider, "sync_attempts", 1.0)
                record_sync_metric(db, company_id, provider, "sync_successes", 1.0)
                record_sync_metric(db, company_id, provider, "sync_duration", float(duration))
                record_sync_metric(db, company_id, provider, "provider_latency", float(res["latency_ms"]))
                record_sync_metric(db, company_id, provider, "queue_lag", float(queue_lag))

                log_audit_event(
                    db=db,
                    action="hris.sync_success",
                    actor_type="SYSTEM",
                    company_id=company_id,
                    resource_type="employees",
                    resource_id=str(employee.id),
                    metadata={"provider": provider, "hris_id": res["hris_id"], "duration_ms": duration}
                )

                db.commit()

            except Exception as exc:
                db.rollback()
                # Catch failures and execute recovery framework
                completed_at = datetime.now(timezone.utc)
                duration = int((completed_at - started_at).total_seconds() * 1000)
                error_msg = str(exc)

                # Update Circuit Breaker statistics
                failures = integration.settings.get("consecutive_failures", 0) + 1
                integration.settings = {**integration.settings, "consecutive_failures": failures}
                integration.last_sync_at = datetime.now(timezone.utc)

                if failures >= 5:
                    # Trip Circuit Breaker! Set status to error
                    integration.status = "error"
                    log_audit_event(
                        db=db,
                        action="hris.circuit_opened",
                        actor_type="SYSTEM",
                        company_id=company_id,
                        resource_type="company_hris_integrations",
                        resource_id=str(integration.id),
                        metadata={"provider": provider, "consecutive_failures": failures}
                    )

                db.add(integration)
                db.flush()

                # Determine if attempts remain
                if attempt_num < 5:
                    # Increment retries on outbox
                    outbox.status = "retrying"
                    outbox.retry_count = attempt_num
                    outbox.last_error = error_msg
                    
                    employee.sync_status = "retrying"
                    employee.sync_error = error_msg
                    
                    db.add(outbox)
                    db.add(employee)
                    db.flush()

                    log_sync_history_record(
                        db=db,
                        company_id=company_id,
                        employee_id=employee_id,
                        provider=provider,
                        request_id=outbox.id,
                        state="retrying",
                        attempt=attempt_num,
                        started_at=started_at,
                        completed_at=completed_at,
                        duration_ms=duration,
                        error_message=error_msg,
                        payload_hash=p_hash
                    )

                    # Record metrics
                    record_sync_metric(db, company_id, provider, "sync_attempts", 1.0)
                    record_sync_metric(db, company_id, provider, "sync_failures", 1.0)

                    db.commit()

                    # Trigger celery retry with backoff + random jitter
                    countdown = (2 ** attempt_num) * 15 + random.uniform(1, 5) # e.g. 30s + jitter
                    if celery_app.conf.task_always_eager:
                        countdown = 0.01
                    logger.warning(f"HRIS sync failed (attempt {attempt_num}/5). Retrying in {countdown:.1f}s...")
                    raise self.retry(exc=exc, countdown=int(countdown))
                else:
                    # Maximum attempts exceeded -> Route to Dead Letter Queue (DLQ)
                    outbox.status = "failed"
                    outbox.retry_count = attempt_num
                    outbox.last_error = f"Max retries exceeded: {error_msg}"
                    
                    employee.sync_status = "failed"
                    employee.sync_error = outbox.last_error

                    # Check if DLQ record already exists
                    dlq = db.scalar(select(DLQRecord).where(
                        DLQRecord.company_id == company_id,
                        DLQRecord.outbox_id == outbox.id
                    ))
                    if not dlq:
                        dlq = DLQRecord(
                            company_id=company_id,
                            outbox_id=outbox.id,
                            provider=provider,
                            error_message=outbox.last_error,
                            payload=payload,
                            status="failed"
                        )
                        db.add(dlq)

                    db.add(outbox)
                    db.add(employee)
                    db.flush()

                    log_sync_history_record(
                        db=db,
                        company_id=company_id,
                        employee_id=employee_id,
                        provider=provider,
                        request_id=outbox.id,
                        state="failed",
                        attempt=attempt_num,
                        started_at=started_at,
                        completed_at=completed_at,
                        duration_ms=duration,
                        error_message=outbox.last_error,
                        payload_hash=p_hash
                    )

                    # Record metrics
                    record_sync_metric(db, company_id, provider, "sync_attempts", 1.0)
                    record_sync_metric(db, company_id, provider, "sync_failures", 1.0)

                    log_audit_event(
                        db=db,
                        action="hris.sync_failed",
                        actor_type="SYSTEM",
                        company_id=company_id,
                        resource_type="employees",
                        resource_id=str(employee.id),
                        metadata={"provider": provider, "error": outbox.last_error}
                    )

                    db.commit()

        except Exception as exc:
            db.close()
            raise exc
        finally:
            db.close()
