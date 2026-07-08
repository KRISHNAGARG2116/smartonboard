import logging
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from core.audit import log_audit_event
from models import Job
from models.enums import JobStatus
from models.enterprise import CompanySubscriptionPlan, CompanyUsageLedger

logger = logging.getLogger("app")


def get_or_initialize_subscription_plan(db: Session, company_id: uuid.UUID) -> CompanySubscriptionPlan:
    """
    Retrieves the active CompanySubscriptionPlan. If none exists, automatically initializes
    and returns a default 'free' plan for maximum system resilience.
    """
    stmt = select(CompanySubscriptionPlan).where(CompanySubscriptionPlan.company_id == company_id)
    plan = db.scalar(stmt)
    if not plan:
        now = datetime.now(timezone.utc)
        plan = CompanySubscriptionPlan(
            company_id=company_id,
            tier_name="free",
            candidate_limit=5,
            job_limit=3,
            ai_limit=5,
            webhook_limit=10,
            billing_cycle_start=now,
            billing_cycle_end=now + timedelta(days=30)
        )
        db.add(plan)
        db.flush()
    return plan


def get_or_initialize_usage_ledger(db: Session, company_id: uuid.UUID) -> CompanyUsageLedger:
    """
    Retrieves the active CompanyUsageLedger. If none exists, automatically initializes
    and returns a default ledger for maximum system resilience.
    """
    stmt = select(CompanyUsageLedger).where(CompanyUsageLedger.company_id == company_id)
    ledger = db.scalar(stmt)
    if not ledger:
        ledger = CompanyUsageLedger(
            company_id=company_id,
            candidates_processed=0,
            active_jobs_count=0,
            ai_screenings_run=0,
            webhooks_dispatched=0,
            last_reset_at=datetime.now(timezone.utc)
        )
        db.add(ledger)
        db.flush()
    return ledger

def _get_subscription_plan_read_only(db: Session, company_id: uuid.UUID) -> CompanySubscriptionPlan:
    stmt = select(CompanySubscriptionPlan).where(CompanySubscriptionPlan.company_id == company_id)
    plan = db.scalar(stmt)
    if not plan:
        now = datetime.now(timezone.utc)
        plan = CompanySubscriptionPlan(
            company_id=company_id,
            tier_name="free",
            candidate_limit=5,
            job_limit=3,
            ai_limit=5,
            webhook_limit=10,
            billing_cycle_start=now,
            billing_cycle_end=now + timedelta(days=30)
        )
    return plan


def _get_usage_ledger_read_only(db: Session, company_id: uuid.UUID) -> CompanyUsageLedger:
    stmt = select(CompanyUsageLedger).where(CompanyUsageLedger.company_id == company_id)
    ledger = db.scalar(stmt)
    if not ledger:
        ledger = CompanyUsageLedger(
            company_id=company_id,
            candidates_processed=0,
            active_jobs_count=0,
            ai_screenings_run=0,
            webhooks_dispatched=0,
            last_reset_at=datetime.now(timezone.utc)
        )
    return ledger


def check_quota_pre_flight(db: Session, company_id: uuid.UUID, resource_type: str):
    """
    Performs an early pre-flight check to block incoming requests if the quota limit is already exhausted.
    Does not increment values or trigger write operations.
    """
    plan = _get_subscription_plan_read_only(db, company_id)
    
    if resource_type == "active_jobs_count":
        # Check active jobs dynamically in the DB
        stmt = select(func.count(Job.id)).where(
            Job.company_id == company_id,
            Job.status == JobStatus.OPEN
        )
        active_jobs = db.scalar(stmt)
        if active_jobs >= plan.job_limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Billing Limit Exceeded: Active jobs cap ({plan.job_limit}) reached for subscription tier '{plan.tier_name}'."
            )
        return

    ledger = _get_usage_ledger_read_only(db, company_id)
    current_value = getattr(ledger, resource_type, 0)
    
    metric_limit_name = resource_type.replace("candidates_processed", "candidate_limit") \
                                     .replace("active_jobs_count", "job_limit") \
                                     .replace("ai_screenings_run", "ai_limit") \
                                     .replace("webhooks_dispatched", "webhook_limit")
    allowed_limit = getattr(plan, metric_limit_name, 0)

    if current_value >= allowed_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Billing Limit Exceeded: {resource_type.replace('_', ' ').capitalize()} cap ({allowed_limit}) reached for billing cycle."
        )


def increment_quota_usage(
    db: Session,
    company_id: uuid.UUID,
    resource_type: str,
    increment_by: int = 1,
    request: Request | None = None
) -> dict:
    """
    Performs a concurrency-safe atomic quota evaluation and increment using row-level locks (SELECT ... FOR UPDATE).
    Enforces caps (HTTP 402), detects warning thresholds (80%/90%/100%), and logs compliance audit warnings.
    """
    # 1. Fetch plan
    plan = get_or_initialize_subscription_plan(db, company_id)

    # 2. Lock the ledger row using SELECT FOR UPDATE
    stmt_ledger = select(CompanyUsageLedger).where(CompanyUsageLedger.company_id == company_id).with_for_update()
    ledger = db.scalar(stmt_ledger)
    if not ledger:
        # If ledger doesn't exist, initialize and lock it
        ledger = get_or_initialize_usage_ledger(db, company_id)
        db.flush()
        # Re-fetch with lock
        ledger = db.scalar(stmt_ledger)
    else:
        db.refresh(ledger)

    # 3. Resolve limits
    metric_limit_name = resource_type.replace("candidates_processed", "candidate_limit") \
                                     .replace("active_jobs_count", "job_limit") \
                                     .replace("ai_screenings_run", "ai_limit") \
                                     .replace("webhooks_dispatched", "webhook_limit")
    allowed_limit = getattr(plan, metric_limit_name, 0)

    # 4. Handle active jobs count dynamically or ledger metrics
    if resource_type == "active_jobs_count":
        stmt_count = select(func.count(Job.id)).where(
            Job.company_id == company_id,
            Job.status == JobStatus.OPEN
        )
        current_value = db.scalar(stmt_count)
    else:
        current_value = getattr(ledger, resource_type, 0)

    new_value = current_value + increment_by

    # 5. Enforce hard limits
    if new_value > allowed_limit:
        # Log quota.limit_exceeded compliance event and commit BEFORE raising
        # (HTTPException aborts the request, so we must commit now or the audit is lost)
        log_audit_event(
            db=db,
            action="quota.limit_exceeded",
            actor_type="RECRUITER",
            company_id=company_id,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            metadata={
                "resource_type": resource_type,
                "current_usage": current_value,
                "increment_by": increment_by,
                "limit": allowed_limit,
                "tier_name": plan.tier_name,
            }
        )
        db.commit()  # Must commit before raising — HTTPException prevents normal session cleanup
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Billing Limit Exceeded: {resource_type.replace('_', ' ').capitalize()} cap ({allowed_limit}) reached for your subscription tier."
        )

    # 6. Evaluate threshold warnings (80% and 90% and 100%)
    warning_trigger = None
    old_ratio = current_value / allowed_limit if allowed_limit > 0 else 0
    new_ratio = new_value / allowed_limit if allowed_limit > 0 else 0

    thresholds = [0.8, 0.9, 1.0]
    for t in thresholds:
        # Trigger audit logs only if this specific request crosses or hits the threshold
        if old_ratio < t <= new_ratio:
            warning_trigger = str(int(t * 100))
            # Log quota.warning_threshold_reached compliance event with threshold metadata
            log_audit_event(
                db=db,
                action="quota.warning_threshold_reached",
                actor_type="RECRUITER",
                company_id=company_id,
                ip_address=request.client.host if request and request.client else None,
                user_agent=request.headers.get("user-agent") if request else None,
                metadata={
                    "threshold_percent": int(t * 100),
                    "resource_type": resource_type,
                    "current_usage": new_value,
                    "limit": allowed_limit,
                    "tier_name": plan.tier_name,
                }
            )

    # 7. Apply the increment to the database ledger
    if resource_type != "active_jobs_count":
        setattr(ledger, resource_type, new_value)
    ledger.updated_at = datetime.now(timezone.utc)
    db.add(ledger)
    db.flush()

    if request and warning_trigger:
        request.state.quota_warning = warning_trigger

    return {
        "limit": allowed_limit,
        "current": new_value,
        "remaining": allowed_limit - new_value,
        "warning": warning_trigger
    }
