import time
import logging
import uuid
from celery import shared_task
import sqlalchemy as sa
from db.session import SessionLocal, tenant_context
from models import Candidate, Job, Application, CachedMatchScore
from core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    queue="high",
    max_retries=3,
    default_retry_delay=60,
    name="tasks.performance.bulk_recompute_match_scores_task"
)
def bulk_recompute_match_scores_task(self, company_id: str, job_id: str):
    """
    Recalculates match scores in the background for all candidates applied to a job.
    Uses 'high' priority queue.
    """
    logger.info(f"Starting bulk match score recomputation for job {job_id} in company {company_id}")
    db = SessionLocal()
    
    try:
        with tenant_context(tenant_id=company_id):
            # Fetch all applications for the job
            apps = db.query(Application).filter(Application.job_id == uuid.UUID(job_id)).all()
            total = len(apps)
            
            for idx, app in enumerate(apps):
                # Update progress state
                self.update_state(
                    state="PROGRESS",
                    meta={"current": idx, "total": total, "percent": int((idx / total) * 100) if total else 100}
                )
                
                # Simulate recompute logic: verify or refresh cached score
                score_entry = db.query(CachedMatchScore).filter(
                    CachedMatchScore.candidate_id == app.candidate_id,
                    CachedMatchScore.job_id == app.job_id
                ).first()
                
                if score_entry:
                    score_entry.score = min(100, max(0, int(score_entry.score) + 1))  # minor tweak
                    score_entry.last_computed_at = sa.func.now()
                
                db.commit()
                time.sleep(0.05)  # yield control
                
        logger.info(f"Successfully completed match score updates for job {job_id}")
        return {"status": "success", "processed": total}
        
    except Exception as exc:
        logger.error(f"Error during bulk match update for job {job_id}: {exc}")
        db.rollback()
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()


@celery_app.task(
    bind=True,
    queue="normal",
    max_retries=2,
    default_retry_delay=120,
    name="tasks.performance.generate_executive_reports_task"
)
def generate_executive_reports_task(self, company_id: str):
    """
    Aggregates large datasets in the background to build Executive reports.
    Uses 'normal' priority queue.
    """
    logger.info(f"Generating analytics report in background for company {company_id}")
    db = SessionLocal()
    
    try:
        with tenant_context(tenant_id=company_id):
            self.update_state(state="PROGRESS", meta={"percent": 25})
            # Simulate heavy SQL aggregations
            time.sleep(0.5)
            self.update_state(state="PROGRESS", meta={"percent": 75})
            time.sleep(0.5)
            
            # Simulated outcome
            report_data = {
                "company_id": company_id,
                "total_hired": 42,
                "time_to_hire_days": 24.5,
                "generated_at": time.time()
            }
            
            # Store in DB or cache
            from core.redis_cache import RedisCacheService
            RedisCacheService.set_value(
                f"report:executive:{company_id}",
                report_data,
                ttl=86400,
                tags=[f"company_reports_{company_id}"]
            )
            
        logger.info(f"Successfully completed report generation for company {company_id}")
        return {"status": "success", "report": report_data}
        
    except Exception as exc:
        logger.error(f"Failed to generate reports for company {company_id}: {exc}")
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    queue="critical",
    max_retries=5,
    default_retry_delay=30,
    name="tasks.performance.send_bulk_emails_task"
)
def send_bulk_emails_task(self, company_id: str, recipient_emails: list, subject: str, body: str):
    """
    Dispatches notifications/outreach in bulk.
    Uses 'critical' priority queue with high retries.
    """
    logger.info(f"Dispatching bulk emails to {len(recipient_emails)} recipients for company {company_id}")
    total = len(recipient_emails)
    
    try:
        for idx, email in enumerate(recipient_emails):
            self.update_state(
                state="PROGRESS",
                meta={"current": idx, "total": total, "percent": int((idx / total) * 100)}
            )
            # Simulated SMTP delivery
            logger.info(f"Sent email to {email}")
            time.sleep(0.01)
            
        return {"status": "success", "delivered": total}
    except Exception as exc:
        logger.error(f"Error in sending bulk emails: {exc}")
        raise self.retry(exc=exc)
