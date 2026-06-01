import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func

from core.celery_app import celery_app
from core.audit import log_audit_event
from db.session import tenant_context, SessionLocal
from models import Job
from models.enums import JobStatus
from models.enterprise import CompanySubscriptionPlan, CompanyUsageLedger, CompanyUsageHistory

logger = logging.getLogger("celery")


@celery_app.task
def aggregate_usage_billing_period_task():
    """
    Periodic daily/weekly background task that aggregates usage ledger snapshots and rolls over billing cycles.
    Preserves historical usage, executes scheduled tier downgrades, and clears accumulators cleanly.
    """
    # Use global bypass context to query across all tenants
    with tenant_context(auth_mode="true"):
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)

            # Query all companies whose billing cycle has expired
            stmt = select(CompanySubscriptionPlan).where(
                CompanySubscriptionPlan.billing_cycle_end <= now
            )
            expired_plans = db.scalars(stmt).all()

            logger.info(f"Billing Sweep: Found {len(expired_plans)} company subscription plans requiring rollover.")

            for plan in expired_plans:
                # 1. Fetch usage ledger
                stmt_ledger = select(CompanyUsageLedger).where(
                    CompanyUsageLedger.company_id == plan.company_id
                )
                ledger = db.scalar(stmt_ledger)
                if not ledger:
                    ledger = CompanyUsageLedger(
                        company_id=plan.company_id,
                        candidates_processed=0,
                        active_jobs_count=0,
                        ai_screenings_run=0,
                        webhooks_dispatched=0,
                        last_reset_at=plan.billing_cycle_start
                    )
                    db.add(ledger)
                    db.flush()

                # Sync live active job count
                stmt_jobs = select(func.count(Job.id)).where(
                    Job.company_id == plan.company_id,
                    Job.status == JobStatus.OPEN
                )
                live_active_jobs = db.scalar(stmt_jobs)
                ledger.active_jobs_count = live_active_jobs

                # 2. Snapshot historical usage before reset
                history_snapshot = CompanyUsageHistory(
                    company_id=plan.company_id,
                    tier_name=plan.tier_name,
                    billing_period_start=plan.billing_cycle_start,
                    billing_period_end=plan.billing_cycle_end,
                    candidates_processed=ledger.candidates_processed,
                    active_jobs_count=ledger.active_jobs_count,
                    ai_screenings_run=ledger.ai_screenings_run,
                    webhooks_dispatched=ledger.webhooks_dispatched,
                    created_at=now
                )
                db.add(history_snapshot)
                db.flush()

                # 3. Commit pending scheduled downgrades if effective
                old_tier = plan.tier_name
                downgraded = False
                if plan.pending_downgrade_tier:
                    is_effective = True
                    if plan.pending_downgrade_effective_at:
                        # Make effective_at timezone aware if needed
                        effective_at = plan.pending_downgrade_effective_at
                        if effective_at.tzinfo is None:
                            effective_at = effective_at.replace(tzinfo=timezone.utc)
                        is_effective = now >= effective_at

                    if is_effective:
                        plan.tier_name = plan.pending_downgrade_tier
                        
                        # Apply new limits for downgraded tier
                        if plan.tier_name == "free":
                            plan.candidate_limit = 5
                            plan.job_limit = 3
                            plan.ai_limit = 5
                            plan.webhook_limit = 10
                        elif plan.tier_name == "growth":
                            plan.candidate_limit = 100
                            plan.job_limit = 20
                            plan.ai_limit = 100
                            plan.webhook_limit = 200

                        plan.pending_downgrade_tier = None
                        plan.pending_downgrade_effective_at = None
                        downgraded = True

                # 4. Reset ledger metrics
                ledger.candidates_processed = 0
                ledger.ai_screenings_run = 0
                ledger.webhooks_dispatched = 0
                ledger.last_reset_at = now
                db.add(ledger)

                # 5. Roll over cycle periods (30 days rollover)
                plan.billing_cycle_start = plan.billing_cycle_end
                plan.billing_cycle_end = plan.billing_cycle_end + timedelta(days=30)
                plan.updated_at = now
                db.add(plan)
                db.flush()

                # 6. Log quota.limit_reset compliance audit event
                log_audit_event(
                    db=db,
                    action="quota.limit_reset",
                    actor_type="SYSTEM",
                    company_id=plan.company_id,
                    resource_type="company_usage_ledgers",
                    resource_id=str(ledger.id),
                    metadata={
                        "billing_cycle_start": plan.billing_cycle_start.isoformat(),
                        "billing_cycle_end": plan.billing_cycle_end.isoformat(),
                        "tier_name": plan.tier_name,
                        "old_tier": old_tier if downgraded else None,
                    }
                )

            db.commit()
            return len(expired_plans)

        except Exception as exc:
            db.rollback()
            logger.error(f"Failed to execute billing usage aggregation sweep: {exc}")
            raise exc
        finally:
            db.close()
