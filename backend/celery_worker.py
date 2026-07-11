import os
import sys
import uuid
import logging
from pathlib import Path
from sqlalchemy import select, delete

# Add backend directory to python import path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Initialize structured logging configuration
from core.logging_config import setup_logging
setup_logging()

# Initialize Sentry Error Monitoring if DSN is configured
import sentry_sdk

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
    )
    print("Sentry SDK initialized successfully for Celery worker")

from core.celery_app import celery_app
from db.session import tenant_context, SessionLocal
from pipeline import process_candidate
from models import Candidate, Application, Job, CandidateEmbedding
from models.enums import ApplicationStatus
from core.embeddings import EmbeddingService
from core.audit import log_audit_event
from core.workflow_engine import execute_workflow_run_task
from core.integration_health import check_integration_health_task
from api.hris_imports import run_hris_import_task

logger = logging.getLogger("celery")





def invalidate_insights(db, application_id: uuid.UUID, insight_types: list[str]):
    """
    Soft-invalidates cached recruiter insights matching the types.
    Preserves lifecycle history, avoids row churn, and resets generation parameters.
    """
    from models.recruiter_insight import AIRecruiterInsight
    from datetime import datetime, timezone
    
    epoch = datetime.fromtimestamp(0, tz=timezone.utc)
    
    for it in insight_types:
        stmt = select(AIRecruiterInsight).where(
            AIRecruiterInsight.application_id == application_id,
            AIRecruiterInsight.insight_type == it
        )
        insight = db.scalar(stmt)
        if insight:
            insight.generation_status = "PENDING"
            insight.content = None
            insight.last_error = None
            insight.checksum = ""
            insight.generated_at = None
            insight.expires_at = epoch
            db.flush()


class GroqRateLimitError(Exception):
    """Raised when encountering rate-limiting or service capacity caps on LLM APIs."""
    pass


class TransientDatabaseLockError(Exception):
    """Raised when encountering database locking or concurrent transaction failures."""
    pass


@celery_app.task(bind=True, max_retries=5)
def process_resume_async(self, file_path: str, company_id: str, job_id: str, evaluation_id: str):
    """
    Idempotent background Celery task that parses a candidate's resume, executes
    the LangGraph recruitment graph, generates text embeddings, and updates the
    application state under strict RLS tenant isolation.
    """
    retry_cnt = self.request.retries

    # 1. Establish tenant boundary inside worker thread context
    with tenant_context(tenant_id=company_id):
        db = SessionLocal()
        try:
            # 2. Check if the Job exists
            job = db.scalar(select(Job).where(Job.id == uuid.UUID(job_id)))
            if job is None:
                raise ValueError(f"Terminal Error: Job with ID {job_id} does not exist.")

            # Enforce parsed candidate billing quota (retries excluded)
            if retry_cnt == 0:
                from core.quota import increment_quota_usage
                increment_quota_usage(db, uuid.UUID(company_id), "candidates_processed")

            # 3. Emit ai.evaluation_started compliance audit event
            log_audit_event(
                db=db,
                action="ai.evaluation_started",
                actor_type="UNAUTHENTICATED",
                company_id=uuid.UUID(company_id),
                metadata={
                    "evaluation_id": evaluation_id,
                    "job_role": job.title,
                    "department": job.department,
                    "file_path": file_path,
                }
            )

            # 4. Load the file from disk (shared volume structure)
            abs_path = Path(__file__).resolve().parent.parent / "storage" / file_path
            if not abs_path.exists():
                raise FileNotFoundError(f"Terminal Error: Resume document not found at {abs_path}")

            pdf_bytes = abs_path.read_bytes()

            # 5. Execute LangGraph Pipeline
            try:
                result = process_candidate(
                    pdf_bytes=pdf_bytes,
                    job_description=job.description,
                    role=job.title,
                    department=job.department,
                    start_date=""
                )
            except Exception as graph_exc:
                err_str = str(graph_exc)
                if "rate_limit" in err_str.lower() or "429" in err_str or "overloaded" in err_str.lower():
                    raise GroqRateLimitError(err_str) from graph_exc
                raise graph_exc

            # Check if internal nodes emitted failures
            if result.get("errors"):
                joined_errors = " ".join(result["errors"])
                if "rate_limit" in joined_errors.lower() or "429" in joined_errors or "overloaded" in joined_errors.lower():
                    raise GroqRateLimitError(joined_errors)
                raise ValueError(f"LangGraph execution error: {joined_errors}")

            candidate_data = result.get("candidate_data", {})
            cand_email = candidate_data.get("email", "unknown@example.com").lower()
            cand_name = candidate_data.get("name", "Unknown Candidate")
            cand_phone = candidate_data.get("phone", None)

            # 6. Idempotent Candidate Lookup & Upsert
            candidate = db.scalar(
                select(Candidate).where(
                    Candidate.company_id == uuid.UUID(company_id),
                    Candidate.email == cand_email
                )
            )
            if candidate is None:
                candidate = Candidate(
                    company_id=uuid.UUID(company_id),
                    email=cand_email,
                    full_name=cand_name,
                    phone=cand_phone
                )
                db.add(candidate)
                db.flush()
            else:
                candidate.full_name = cand_name
                if cand_phone:
                    candidate.phone = cand_phone
                db.flush()

            # 7. Idempotent Application Lookup & Mapping
            application = db.scalar(
                select(Application).where(
                    Application.job_id == uuid.UUID(job_id),
                    Application.candidate_id == candidate.id
                )
            )

            decision = result.get("decision_result", {}).get("decision", "REJECT")
            score = result.get("scoring_result", {}).get("total_score", 0)

            if application is None:
                application = Application(
                    company_id=uuid.UUID(company_id),
                    job_id=uuid.UUID(job_id),
                    candidate_id=candidate.id,
                    status=ApplicationStatus.SCREENING,
                    source="AI Application",
                    match_score=float(score)
                )
                db.add(application)
                db.flush()
            else:
                application.status = ApplicationStatus.SCREENING
                application.match_score = float(score)
                db.flush()

            # 8. Extract Plain Text & Create Idempotent Chunks Embeddings
            from core.signature import extract_text_from_file_bytes
            try:
                resume_text = extract_text_from_file_bytes(pdf_bytes, Path(file_path).name)
            except Exception:
                resume_text = ""

            if resume_text.strip():
                chunks = [chunk.strip() for chunk in resume_text.split("\n\n") if chunk.strip()]
                if not chunks:
                    chunks = [resume_text.strip()]

                # Idempotency: Delete pre-existing embeddings for this candidate to prevent UNIQUE constraint failures
                db.execute(delete(CandidateEmbedding).where(
                    CandidateEmbedding.company_id == uuid.UUID(company_id),
                    CandidateEmbedding.candidate_id == candidate.id
                ))
                db.flush()

                # Generate and write new embeddings
                embedder = EmbeddingService()
                for idx, chunk in enumerate(chunks[:20]):
                    vector = embedder.generate_embedding(chunk)
                    new_emb = CandidateEmbedding(
                        company_id=uuid.UUID(company_id),
                        candidate_id=candidate.id,
                        resume_embedding=vector,
                        chunk_text=chunk[:2000],
                        chunk_index=idx,
                        embedding_provider="huggingface",
                        embedding_model="BAAI/bge-small-en-v1.5",
                        embedding_version=1
                    )
                    db.add(new_emb)
                db.flush()
                
                # Invalidate cached recruiter insights due to candidate resume changes
                if application:
                    invalidate_insights(db, application.id, ["candidate_summary", "hiring_recommendation"])

            # 9. Emit compliance audit events inside tenant connection context
            log_audit_event(
                db=db,
                action="ai.match_score_generated",
                actor_type="UNAUTHENTICATED",
                company_id=uuid.UUID(company_id),
                metadata={"evaluation_id": evaluation_id, "score": score}
            )

            log_audit_event(
                db=db,
                action="ai.evaluation_completed",
                actor_type="UNAUTHENTICATED",
                company_id=uuid.UUID(company_id),
                metadata={
                    "evaluation_id": evaluation_id,
                    "score": score,
                    "recommendation": decision,
                    "model_version": "gemini-1.5-pro",
                    "summary": f"Candidate processed for {job.title} in {job.department}. Fit: {result.get('scoring_result', {}).get('overall_fit', 'N/A')}"
                }
            )

            db.commit()

            # Return serializable result payload
            return {
                "success": True,
                "candidate_id": str(candidate.id),
                "application_id": str(application.id),
                "decision": decision,
                "score": score,
                "candidate": candidate_data,
                "screening": result.get("screening_result", {}),
                "scoring": result.get("scoring_result", {}),
                "decision_result": result.get("decision_result", {}),
                "communication": result.get("communication_result", {})
            }

        except (GroqRateLimitError, TransientDatabaseLockError) as exc:
            db.rollback()
            base_delay = 5
            countdown = (2 ** retry_cnt) * base_delay
            logger.warning(f"Transient failure (retry {retry_cnt}/5) for task. Retrying in {countdown}s. Error: {exc}")
            raise self.retry(exc=exc, countdown=countdown)

        except Exception as exc:
            db.rollback()
            logger.error(f"Permanent failure in async evaluation processing: {exc}")

            # Emit ai.evaluation_failed compliance audit event
            try:
                with SessionLocal() as log_db:
                    log_audit_event(
                        db=log_db,
                        action="ai.evaluation_failed",
                        actor_type="UNAUTHENTICATED",
                        company_id=uuid.UUID(company_id) if company_id else None,
                        metadata={
                            "evaluation_id": evaluation_id,
                            "error_type": exc.__class__.__name__,
                            "retry_count": retry_cnt,
                            "error_message": str(exc)
                        }
                    )
                    log_db.commit()
            except Exception as log_exc:
                logger.error(f"Error logging ai.evaluation_failed audit event: {log_exc}")

            raise exc

        finally:
            db.close()


@celery_app.task
def track_stage_transition_async(company_id: str, application_id: str, from_status: str, to_status: str, actor_id: str | None = None):
    """
    Asynchronously tracks candidate stage transition, calculates durations,
    and updates funnel aggregates under strict RLS isolation.
    """
    from models.stage_transition import CandidateStageTransition
    from models.funnel_aggregate import FunnelAggregate
    from datetime import datetime, timezone

    with tenant_context(tenant_id=company_id):
        db = SessionLocal()
        try:
            app_uuid = uuid.UUID(application_id)
            company_uuid = uuid.UUID(company_id)
            actor_uuid = uuid.UUID(actor_id) if actor_id else None

            # 1. Update the previous active transition's duration if exists
            stmt = (
                select(CandidateStageTransition)
                .where(
                    CandidateStageTransition.application_id == app_uuid,
                    CandidateStageTransition.to_status == from_status,
                    CandidateStageTransition.duration_seconds.is_(None)
                )
                .order_by(CandidateStageTransition.transitioned_at.desc())
                .limit(1)
            )
            last_t = db.scalar(stmt)
            now = datetime.now(timezone.utc)
            if last_t:
                duration = int((now - last_t.transitioned_at).total_seconds())
                last_t.duration_seconds = max(0, duration)
                db.flush()

            # 2. Insert new transition record
            new_t = CandidateStageTransition(
                company_id=company_uuid,
                application_id=app_uuid,
                from_status=from_status,
                to_status=to_status,
                actor_id=actor_uuid,
                transitioned_at=now
            )
            db.add(new_t)
            db.flush()

            # 3. Retrieve application to find associated job_id
            application = db.scalar(select(Application).where(Application.id == app_uuid))
            if application:
                job_id = application.job_id

                # Increment candidate_count for to_status
                agg_stmt = select(FunnelAggregate).where(
                    FunnelAggregate.company_id == company_uuid,
                    FunnelAggregate.job_id == job_id,
                    FunnelAggregate.stage == to_status
                )
                agg_to = db.scalar(agg_stmt)
                if agg_to is None:
                    agg_to = FunnelAggregate(
                        company_id=company_uuid,
                        job_id=job_id,
                        stage=to_status,
                        candidate_count=1
                    )
                    db.add(agg_to)
                else:
                    agg_to.candidate_count += 1

                # If advancing from an existing stage (not to rejected), increment conversion_count for from_status
                if from_status and to_status != "rejected" and to_status != from_status:
                    agg_from_stmt = select(FunnelAggregate).where(
                        FunnelAggregate.company_id == company_uuid,
                        FunnelAggregate.job_id == job_id,
                        FunnelAggregate.stage == from_status
                    )
                    agg_from = db.scalar(agg_from_stmt)
                    if agg_from is None:
                        agg_from = FunnelAggregate(
                            company_id=company_uuid,
                            job_id=job_id,
                            stage=from_status,
                            conversion_count=1
                        )
                        db.add(agg_from)
                    else:
                        agg_from.conversion_count += 1

            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error(f"Error in track_stage_transition_async: {exc}")
            raise exc
        finally:
            db.close()


@celery_app.task
def track_recruiter_productivity_async(company_id: str, recruiter_id: str, metric_type: str):
    """
    Asynchronously increments recruiter productivity aggregates under strict RLS isolation.
    """
    from models.recruiter_productivity import RecruiterProductivityAggregate

    with tenant_context(tenant_id=company_id):
        db = SessionLocal()
        try:
            company_uuid = uuid.UUID(company_id)
            recruiter_uuid = uuid.UUID(recruiter_id)

            stmt = select(RecruiterProductivityAggregate).where(
                RecruiterProductivityAggregate.company_id == company_uuid,
                RecruiterProductivityAggregate.recruiter_id == recruiter_uuid
            )
            prod = db.scalar(stmt)
            if prod is None:
                prod = RecruiterProductivityAggregate(
                    company_id=company_uuid,
                    recruiter_id=recruiter_uuid
                )
                db.add(prod)
                db.flush()

            if metric_type == "review":
                prod.applications_reviewed += 1
            elif metric_type == "advance":
                prod.candidates_advanced += 1
            elif metric_type == "interview":
                prod.interviews_scheduled += 1
            elif metric_type == "offer_create":
                prod.offers_created += 1
            elif metric_type == "offer_accept":
                prod.offers_accepted += 1

            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error(f"Error in track_recruiter_productivity_async: {exc}")
            raise exc
        finally:
            db.close()


@celery_app.task(bind=True, max_retries=3)
def generate_recruiter_insight_async(self, company_id: str, application_id: str, insight_type: str, checksum: str):
    """
    Asynchronously generates and caches recruiter insights (candidate summaries, scorecard consensus,
    or hiring recommendations) using bias-mitigated prompts.
    """
    from models.recruiter_insight import AIRecruiterInsight
    from core.intelligence import GenerativeIntelligenceService
    from datetime import datetime, timezone, timedelta
    
    retry_cnt = self.request.retries
    
    with tenant_context(tenant_id=company_id):
        db = SessionLocal()
        try:
            company_uuid = uuid.UUID(company_id)
            app_uuid = uuid.UUID(application_id)
            
            # Fetch or create insight record
            stmt = select(AIRecruiterInsight).where(
                AIRecruiterInsight.application_id == app_uuid,
                AIRecruiterInsight.insight_type == insight_type
            )
            insight = db.scalar(stmt)
            if not insight:
                insight = AIRecruiterInsight(
                    company_id=company_uuid,
                    application_id=app_uuid,
                    insight_type=insight_type,
                    checksum=checksum,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                    model_version="llama-3.3-70b-versatile"
                )
                db.add(insight)
                db.flush()
                
            insight.generation_status = "PROCESSING"
            db.commit()
            
            # Run the generative engine
            result = GenerativeIntelligenceService.generate_insight(db, app_uuid, insight_type)
            
            insight.content = result["content"]
            insight.confidence_score = result["confidence_score"]
            insight.confidence_reason = result["confidence_reason"]
            insight.candidate_embedding_ids = result["candidate_embedding_ids"]
            insight.scorecard_ids = result["scorecard_ids"]
            insight.checksum = checksum
            insight.generation_status = "COMPLETED"
            insight.last_error = None
            insight.generated_at = datetime.now(timezone.utc)
            insight.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            db.commit()

            # Emit billing usage events
            from core.workflow_engine import emit_billing_event
            if insight_type == "candidate_summary":
                emit_billing_event(db, company_uuid, "ai.candidate_summary.generated", str(insight.id))
            else:
                emit_billing_event(db, company_uuid, "ai.description.generated", str(insight.id))
            db.commit()

            
            # Log audit event
            action_map = {
                "candidate_summary": "ai.summary_generated",
                "scorecard_consensus": "ai.consensus_generated",
                "hiring_recommendation": "ai.recommendation_generated"
            }
            log_audit_event(
                db=db,
                action=action_map.get(insight_type, "ai.insight_generated"),
                actor_type="SYSTEM",
                company_id=company_uuid,
                metadata={
                    "application_id": application_id,
                    "prompt_version": 1,
                    "model_version": "llama-3.3-70b-versatile",
                    "confidence_score": result["confidence_score"]
                }
            )
            db.commit()
            
        except Exception as exc:
            db.rollback()
            # If rate limit or similar transient Groq error, retry
            err_str = str(exc).lower()
            is_transient = "429" in err_str or "rate limit" in err_str or "overloaded" in err_str or "503" in err_str
            if is_transient and retry_cnt < 3:
                countdown = (2 ** retry_cnt) * 15
                logger.warning(f"Transient error generating insight. Retrying in {countdown}s. Error: {exc}")
                raise self.retry(exc=exc, countdown=countdown)
            
            # Permanent failure
            insight = db.scalar(stmt)
            if insight:
                insight.generation_status = "FAILED"
                insight.last_error = str(exc)
                insight.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
                db.commit()
                
            # Log failure audit event
            try:
                with SessionLocal() as log_db:
                    log_audit_event(
                        db=log_db,
                        action="ai.summary_failed",
                        actor_type="SYSTEM",
                        company_id=company_uuid,
                        metadata={
                            "application_id": application_id,
                            "insight_type": insight_type,
                            "error_type": exc.__class__.__name__,
                            "prompt_version": 1
                        }
                    )
                    log_db.commit()
            except Exception as log_exc:
                logger.error(f"Error logging ai.summary_failed audit event: {log_exc}")
                
            raise exc
        finally:
            db.close()


@celery_app.task
def generate_analytics_export_async(company_id: str, user_id: str, job_id: str):
    """
    Asynchronously queries multi-tenant interaction analytics under RLS connection scoping,
    compiles to CSV in storage, and logs completion audit events.
    """
    from models.export_job import ExportJob
    from models.insight_interaction import AIInsightInteraction
    import csv
    import os
    
    with tenant_context(tenant_id=company_id):
        db = SessionLocal()
        try:
            company_uuid = uuid.UUID(company_id)
            user_uuid = uuid.UUID(user_id)
            job_uuid = uuid.UUID(job_id)
            
            job = db.scalar(select(ExportJob).where(ExportJob.id == job_uuid))
            if not job:
                logger.error(f"ExportJob {job_id} not found.")
                return
                
            job.status = "PROCESSING"
            db.commit()
            
            # Ensure exports directory exists inside workspace
            exports_dir = Path(__file__).resolve().parent.parent / "storage" / "exports" / company_id
            exports_dir.mkdir(parents=True, exist_ok=True)
            
            dest_file = exports_dir / f"{job_id}.csv"
            
            # Query and compile interactions
            stmt = select(AIInsightInteraction).where(
                AIInsightInteraction.company_id == company_uuid
            ).order_by(AIInsightInteraction.created_at.desc())
            rows = db.scalars(stmt).all()
            
            with open(dest_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Interaction ID", "User ID", "Application ID",
                    "Insight Type", "Interaction Type", "Snapshot", "Decision Date"
                ])
                for r in rows:
                    writer.writerow([
                        str(r.id), str(r.user_id), str(r.application_id),
                        r.insight_type, r.interaction_type, r.recommendation_snapshot or "", r.created_at.isoformat()
                    ])
                    
            job.file_path = str(dest_file)
            job.status = "COMPLETED"
            db.commit()
            
            # Log export completion event
            log_audit_event(
                db=db,
                action="security.analytics_export_generated",
                actor_type="SYSTEM",
                company_id=company_uuid,
                metadata={
                    "export_job_id": job_id,
                    "record_count": len(rows),
                    "format": "csv"
                }
            )
            
        except Exception as exc:
            db.rollback()
            logger.error(f"Error executing generate_analytics_export_async: {exc}")
            
            # Re-fetch under tenant context to write error state
            try:
                job = db.scalar(select(ExportJob).where(ExportJob.id == uuid.UUID(job_id)))
                if job:
                    job.status = "FAILED"
                    job.error_message = str(exc)
                    db.commit()
            except Exception as inner_exc:
                logger.error(f"Failed to record FAILED state: {inner_exc}")
        finally:
            db.close()


@celery_app.task
def cleanup_expired_exports_async():
    """
    Scheduled task that runs to prune expired generated export CSV files from disk
    and marks completed storage entities as EXPIRED.
    """
    from models.export_job import ExportJob
    from datetime import datetime, timezone
    import os
    
    # Run under bypass context to clear expired files across all tenants
    with tenant_context(auth_mode="true"):
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            stmt = select(ExportJob).where(
                ExportJob.expires_at < now,
                ExportJob.status == "COMPLETED"
            )
            expired_jobs = db.scalars(stmt).all()
            
            count = 0
            for job in expired_jobs:
                if job.file_path and os.path.exists(job.file_path):
                    try:
                        os.remove(job.file_path)
                    except Exception as fs_exc:
                        logger.error(f"Failed to remove file {job.file_path}: {fs_exc}")
                        
                job.status = "EXPIRED"
                job.file_path = None
                db.add(job)
                count += 1
                
            db.commit()
            logger.info(f"Cleaned up {count} expired analytics export jobs.")
        except Exception as exc:
            db.rollback()
            logger.error(f"Error running cleanup_expired_exports_async: {exc}")
        finally:
            db.close()


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def generate_delta_sync_async(self, credential_id: str, company_id: str):
    """
    Background sync runner for a specific calendar credential under strict RLS isolation.
    Handles rate limiting exceptions by registering exponential backoffs and retrying.
    """
    from tasks.calendar_sync import run_delta_sync_for_credential, ProviderRateLimitError
    
    with tenant_context(tenant_id=company_id):
        db = SessionLocal()
        try:
            run_delta_sync_for_credential(db=db, credential_id=uuid.UUID(credential_id))
        except ProviderRateLimitError as exc:
            db.rollback()
            retry_cnt = self.request.retries
            backoff_delay = (2 ** retry_cnt) * 60
            logger.warning(f"Rate limited by calendar provider. Retrying in {backoff_delay}s... Error: {exc}")
            raise self.retry(exc=exc, countdown=backoff_delay)
        except Exception as exc:
            db.rollback()
            logger.error(f"Sync failed for credential {credential_id}: {exc}")
        finally:
            db.close()


# Import advanced automation tasks to ensure Celery registers them on startup
from tasks.escalations import check_sla_breaches_task, check_approval_escalations_task
from tasks.webhooks import dispatch_webhook_event_task, purge_expired_delivery_logs
from tasks.smtp import reverify_all_smtp_settings_task
from tasks.billing import aggregate_usage_billing_period_task


@celery_app.task(bind=True, max_retries=5)
def scan_and_promote_resume_task(self, quarantine_file_id: str, job_id: str = None, evaluation_id: str = None, job_role: str = None, job_description: str = None):
    """
    Asynchronously scans a quarantined file via ClamAV, promotes it if safe,
    and executes the screening or full recruitment parsing pipeline.
    """
    import time
    import signal
    from contextlib import contextmanager
    from db.session import SessionLocal, tenant_context
    from models.quarantine import QuarantinedFile
    from core.malware import scan_file_for_malware
    from core.signature import extract_text_from_file_bytes
    from core.storage import LocalStorageService
    from pathlib import Path
    import uuid

    @contextmanager
    def stage_timeout(stage_name: str, seconds: int = 30):
        t0 = time.time()
        logger.info(f"[TIMING] Starting stage: {stage_name}")
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Stage '{stage_name}' hung and timed out after {seconds} seconds!")
        
        has_signal = False
        try:
            original_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            has_signal = True
        except ValueError as e:
            logger.warning(f"Bypassing SIGALRM stage timeout for '{stage_name}' because: {e}")
        
        try:
            yield
            elapsed = time.time() - t0
            logger.info(f"[TIMING] Completed stage: {stage_name} in {elapsed:.3f}s")
        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"[TIMING] Failed stage: {stage_name} after {elapsed:.3f}s with error: {e}")
            raise
        finally:
            if has_signal:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, original_handler)

    db = SessionLocal()
    try:
        # 1. Fetch quarantine file
        with stage_timeout("Fetch Quarantine File Record", 30):
            q_file = db.get(QuarantinedFile, uuid.UUID(quarantine_file_id))
            if not q_file:
                logger.error(f"Quarantined file with ID {quarantine_file_id} not found.")
                return {"success": False, "error": "Quarantined file not found"}

            company_id = str(q_file.company_id)
            STORAGE_BASE_DIR = Path(__file__).resolve().parent.parent / "storage"
            storage_service = LocalStorageService(STORAGE_BASE_DIR)

            q_path = Path(q_file.quarantine_path)
            if not q_path.is_absolute():
                q_path = STORAGE_BASE_DIR / q_path

            if not q_path.exists():
                q_file.is_safe = False
                q_file.error_message = "File not found in quarantine storage"
                db.commit()
                return {"success": False, "error": "File not found"}

            file_bytes = q_path.read_bytes()

        # 2. Malware Scan
        with stage_timeout("Malware Scan (ClamAV)", 30):
            try:
                scan_file_for_malware(file_bytes)
                q_file.is_safe = True
                db.flush()
            except ValueError as val_err:
                q_file.is_safe = False
                q_file.error_message = str(val_err)
                db.commit()
                storage_service.delete_file(q_path)
                
                # Log audit event
                from core.audit import log_audit_event
                log_audit_event(
                    db=db,
                    action="file.scan_failure",
                    actor_type="UNAUTHENTICATED",
                    company_id=q_file.company_id,
                    resource_type="quarantine",
                    metadata={"filename": q_file.filename, "error": str(val_err), "event": "malware_detected"}
                )
                db.commit()
                return {"success": False, "error": str(val_err)}
            except Exception as exc:
                db.rollback()
                countdown = (2 ** self.request.retries) * 5
                logger.warning(f"Transient scan failure (retry {self.request.retries}/5) for task. Retrying in {countdown}s. Error: {exc}")
                raise self.retry(exc=exc, countdown=countdown)

        # 3. Role-aware branching after scan
        if q_file.user_id is not None:
            user_id = q_file.user_id
            
            with stage_timeout("Promote File to Candidate Storage", 30):
                permanent_path = storage_service.promote_file(q_path, f"candidates/{user_id}")
                
                # Log promotion audit event for candidate
                from core.audit import log_audit_event
                log_audit_event(
                    db=db,
                    action="file.promoted",
                    actor_type="CANDIDATE",
                    actor_id=user_id,
                    resource_type="uploads",
                    resource_id=permanent_path.name,
                    metadata={"filename": q_file.filename, "size": len(file_bytes)}
                )
                db.commit()

            # 4. Parse resume facts
            with stage_timeout("Parse Resume Facts (LLM)", 30):
                from agents.resume_parser import resume_parser_agent
                parsed_data = resume_parser_agent(file_bytes)

            # 5. Database Update (CandidateResume and CandidateProfile)
            with stage_timeout("Update Database Records", 30):
                with tenant_context(auth_mode="true"):
                    from models.candidate_resume import CandidateResume
                    from sqlalchemy import update
                    db.execute(
                        update(CandidateResume)
                        .where(CandidateResume.user_id == user_id)
                        .values(is_active=False)
                    )
                    db.flush()

                    relative_path = f"uploads/candidates/{user_id}/{permanent_path.name}"
                    new_resume = CandidateResume(
                        user_id=user_id,
                        filename=q_file.filename,
                        file_path=relative_path,
                        is_active=True,
                        parsed_skills=parsed_data.get("skills", []),
                        parsed_summary=parsed_data.get("summary", "")
                    )
                    db.add(new_resume)
                    db.flush()

                    from models.candidate_profile import CandidateProfile
                    profile = db.scalar(
                        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
                    )
                    if profile:
                        profile.skills = parsed_data.get("skills", [])
                        profile.summary = parsed_data.get("summary", "")
                        
                        parsed_name = parsed_data.get("name")
                        if parsed_name and (not profile.full_name or profile.full_name == "Unknown"):
                            profile.full_name = parsed_name
                            
                        parsed_phone = parsed_data.get("phone")
                        if parsed_phone and not profile.phone_number:
                            profile.phone_number = parsed_phone
                            
                        db.add(profile)
                    
                    db.commit()

            return {
                "success": True,
                "filename": q_file.filename,
                "resume_id": str(new_resume.id)
            }

        # Recruiter Flow
        with stage_timeout("Promote File to Recruiter Storage", 30):
            permanent_path = storage_service.promote_file(q_path, company_id)
            
            # Log promotion compliance audit
            from core.audit import log_audit_event
            log_audit_event(
                db=db,
                action="file.promoted",
                actor_type="UNAUTHENTICATED",
                company_id=q_file.company_id,
                resource_type="uploads",
                resource_id=permanent_path.name,
                metadata={"filename": q_file.filename, "size": len(file_bytes)}
            )
            db.commit()

        # Choose pipeline depending on job_id presence
        if job_id is None:
            # screening playground workflow
            with stage_timeout("Screen Resume Text (LLM)", 30):
                from agents.screening_agent import screen_resume_text as _screen_text
                resume_text = extract_text_from_file_bytes(file_bytes, q_file.filename)
                result = _screen_text(
                    resume_text=resume_text,
                    job_role=job_role or "Software Engineer",
                    job_description=job_description or "",
                )
                return {"success": True, "analysis": result, "filename": q_file.filename}
        else:
            # recruitment workflow: reuse process_resume_async logic
            with stage_timeout("Process Resume Async (Full Pipeline)", 30):
                relative_path = f"uploads/{company_id}/{permanent_path.name}"
                db.close() # Close current session since process_resume_async opens its own
                return process_resume_async.run(relative_path, company_id, str(job_id), str(evaluation_id))

    except Exception as exc:
        db.rollback()
        logger.error(f"Permanent failure in scan_and_promote_resume_task: {exc}", exc_info=True)
        try:
            with SessionLocal() as err_db:
                from models.quarantine import QuarantinedFile
                q_rec = err_db.get(QuarantinedFile, uuid.UUID(quarantine_file_id))
                if q_rec:
                    q_rec.is_safe = False
                    q_rec.error_message = f"Processing failed: {str(exc)}"
                    err_db.commit()
                    logger.info(f"Updated QuarantinedFile {quarantine_file_id} status to FAILED in the database.")
        except Exception as log_err:
            logger.error(f"Failed to update QuarantinedFile status to FAILED in the database: {log_err}", exc_info=True)
        raise exc
    finally:
        db.close()


@celery_app.task(name="process_offer_acceptance_async")
def process_offer_acceptance_async(offer_id_str: str) -> dict:
    """Asynchronously handles offer acceptance events:
    1. Create audit event
    2. Dispatch notifications
    3. Update Recruiter Dashboard indicators
    4. Create Candidate Onboarding Tasks
    5. Trigger HRIS Workflow
    """
    logger.info(f"Starting process_offer_acceptance_async for offer {offer_id_str}")
    offer_id = uuid.UUID(offer_id_str)
    db = SessionLocal()
    # Bypass RLS to fetch the Offer and associated Application/Candidate/Company
    with tenant_context(auth_mode="true"):
        from models import Offer, Application, User, Notification, CandidateTask, OnboardingTask
        from models.enums import UserRole
        offer = db.get(Offer, offer_id)
        if not offer:
            logger.error(f"Offer {offer_id} not found")
            db.close()
            return {"success": False, "error": "Offer not found"}
        
        app = db.get(Application, offer.application_id)
        if not app:
            logger.error(f"Application {offer.application_id} not found")
            db.close()
            return {"success": False, "error": "Application not found"}

        candidate_user = db.scalar(
            select(User).where(User.id == app.candidate_id)
        )
        if not candidate_user:
            from models import Candidate
            cand_rec = db.get(Candidate, app.candidate_id)
            if cand_rec:
                candidate_user = db.scalar(
                    select(User).where(User.email == cand_rec.email)
                )

        if not candidate_user:
            logger.error(f"Candidate User for candidate {app.candidate_id} not found")
            db.close()
            return {"success": False, "error": "Candidate not found"}

        # 1. Audit Event Idempotency Check
        from models.audit import AuditLog
        audit_exists = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "offer.accepted",
                AuditLog.resource_type == "offers",
                AuditLog.resource_id == str(offer.id)
            )
        )
        if not audit_exists:
            log_audit_event(
                db=db,
                action="offer.accepted",
                actor_type="CANDIDATE",
                actor_id=candidate_user.id,
                company_id=offer.company_id,
                resource_type="offers",
                resource_id=str(offer.id),
                metadata={
                    "offer_id": str(offer.id),
                    "application_id": str(offer.application_id),
                    "salary": float(offer.salary)
                }
            )

        # Update application status to "hired"
        if app.status != ApplicationStatus.HIRED:
            app.status = ApplicationStatus.HIRED
            db.add(app)

        # 2. Dispatch Notifications Idempotency Check
        # Notify recruiter (owner/assigned)
        recruiter_id = app.owner_id
        if recruiter_id:
            notif_exists = db.scalar(
                select(Notification).where(
                    Notification.company_id == offer.company_id,
                    Notification.user_id == recruiter_id,
                    Notification.title == "Offer Accepted!",
                    Notification.type == "offer"
                )
            )
            if not notif_exists:
                notif = Notification(
                    company_id=offer.company_id,
                    user_id=recruiter_id,
                    title="Offer Accepted!",
                    message=f"Candidate {candidate_user.email} has accepted their employment offer.",
                    type="offer",
                    status="unread"
                )
                db.add(notif)

        # 3. Create Candidate Onboarding Tasks Idempotency Check
        onboarding_tasks = [
            {"title": "Submit emergency contact details", "description": "Provide name, phone number, and relationship.", "task_type": "text"},
            {"title": "Specify your equipment preferences", "description": "Choose between macOS (MacBook Pro) or Windows (ThinkPad).", "task_type": "choice"},
            {"title": "Select your T-shirt size", "description": "Choose size for company swag: S, M, L, XL.", "task_type": "choice"},
            {"title": "Upload Gov ID and tax documents", "description": "Upload a copy of your passport or driver license.", "task_type": "file_upload"}
        ]
        from datetime import datetime, date, timedelta, timezone
        for task_info in onboarding_tasks:
            task_exists = db.scalar(
                select(CandidateTask).where(
                    CandidateTask.company_id == offer.company_id,
                    CandidateTask.candidate_id == candidate_user.id,
                    CandidateTask.title == task_info["title"]
                )
            )
            if not task_exists:
                task = CandidateTask(
                    company_id=offer.company_id,
                    candidate_id=candidate_user.id,
                    title=task_info["title"],
                    description=task_info["description"],
                    status="pending",
                    task_type=task_info["task_type"],
                    due_date=date.today() + timedelta(days=7)
                )
                db.add(task)

        # 3.5. Setup Phase C.2 Onboarding Platform Workspace and assets
        # Promote candidate user to employee role
        candidate_user.role = UserRole.EMPLOYEE
        candidate_user.company_id = offer.company_id
        db.add(candidate_user)
        db.flush()

        from models.employees import Employee, OnboardingWorkflow
        employee = db.scalar(
            select(Employee).where(
                Employee.company_id == offer.company_id,
                Employee.email == candidate_user.email
            )
        )
        if not employee:
            employee = Employee(
                company_id=offer.company_id,
                candidate_id=app.candidate_id,
                email=candidate_user.email,
                full_name=candidate_user.full_name,
                job_title="Software Engineer",
                department="Engineering",
                employment_type="full_time",
                status="onboarding",
                start_date=date.today() + timedelta(days=14),
                user_id=candidate_user.id
            )
            db.add(employee)
            db.flush()

        workflow = db.scalar(
            select(OnboardingWorkflow).where(OnboardingWorkflow.employee_id == employee.id)
        )
        if not workflow:
            workflow = OnboardingWorkflow(
                company_id=offer.company_id,
                employee_id=employee.id,
                status="initiated",
                started_at=datetime.utcnow()
            )
            db.add(workflow)
            db.flush()

        from models.employee_onboarding import EmployeeOnboarding
        emp_onboarding = db.scalar(
            select(EmployeeOnboarding).where(EmployeeOnboarding.employee_id == employee.id)
        )
        if not emp_onboarding:
            emp_onboarding = EmployeeOnboarding(
                company_id=offer.company_id,
                employee_id=employee.id,
                template_name="Engineering Onboarding Template",
                template_version=2,
                template_snapshot_created_at=datetime.utcnow(),
                status="in_progress",
                started_at=datetime.utcnow()
            )
            db.add(emp_onboarding)
            db.flush()

        # Snapshot template tasks into onboarding tasks grouped in phases
        from models.onboarding_task_dependencies import OnboardingTaskDependency
        tasks_created = {}
        for title, phase, opt, t_type in [
            ("Sign NDA", "preboarding", False, "document_signature"),
            ("Upload Gov ID and tax documents", "preboarding", False, "file_upload"),
            ("Acknowledge Code of Conduct", "day_1", False, "policy_acknowledgement"),
            ("Request Laptop & Swag", "day_1", True, "equipment_request"),
            ("Attend Welcome Orientation", "day_1", False, "welcome_event")
        ]:
            t = db.scalar(
                select(OnboardingTask).where(
                    OnboardingTask.workflow_id == workflow.id,
                    OnboardingTask.title == title
                )
            )
            if not t:
                t = OnboardingTask(
                    company_id=offer.company_id,
                    workflow_id=workflow.id,
                    title=title,
                    status="pending",
                    task_type=t_type,
                    phase=phase,
                    is_optional=opt,
                    due_date=date.today() + timedelta(days=7)
                )
                db.add(t)
                db.flush()
            tasks_created[title] = t

        # Set up many-to-many task dependencies
        laptop_task = tasks_created.get("Request Laptop & Swag")
        nda_task = tasks_created.get("Sign NDA")
        id_task = tasks_created.get("Upload Gov ID and tax documents")
        if laptop_task and nda_task and id_task:
            for dep_task in [nda_task, id_task]:
                dep_exists = db.scalar(
                    select(OnboardingTaskDependency).where(
                        OnboardingTaskDependency.task_id == laptop_task.id,
                        OnboardingTaskDependency.depends_on_task_id == dep_task.id
                    )
                )
                if not dep_exists:
                    dep = OnboardingTaskDependency(
                        task_id=laptop_task.id,
                        depends_on_task_id=dep_task.id
                    )
                    db.add(dep)

        # Create NDA document entry in vault
        from models.employee_document import EmployeeDocument
        nda_doc = db.scalar(
            select(EmployeeDocument).where(
                EmployeeDocument.employee_id == employee.id,
                EmployeeDocument.document_type == "nda"
            )
        )
        if not nda_doc:
            nda_doc = EmployeeDocument(
                company_id=offer.company_id,
                employee_id=employee.id,
                document_type="nda",
                document_name="Standard Non-Disclosure Agreement",
                document_version="1.0",
                checksum="5a8f4c28d22ef142a7c73a71b12b5b141ea87d1ea21b8f141ea87d1ea21b8f41",
                uploaded_by_id=candidate_user.id,
                storage_key="templates/nda_v1.pdf"
            )
            db.add(nda_doc)

        # Create IT provisioning requests
        from models.employee_provisioning_request import EmployeeProvisioningRequest
        email_pr = db.scalar(
            select(EmployeeProvisioningRequest).where(
                EmployeeProvisioningRequest.employee_id == employee.id,
                EmployeeProvisioningRequest.service_name == "email"
            )
        )
        if not email_pr:
            email_pr = EmployeeProvisioningRequest(
                company_id=offer.company_id,
                employee_id=employee.id,
                service_name="email",
                status="pending",
                notes="Pending corporate email creation"
            )
            db.add(email_pr)
            db.flush()

        sso_pr = db.scalar(
            select(EmployeeProvisioningRequest).where(
                EmployeeProvisioningRequest.employee_id == employee.id,
                EmployeeProvisioningRequest.service_name == "sso"
            )
        )
        if not sso_pr:
            sso_pr = EmployeeProvisioningRequest(
                company_id=offer.company_id,
                employee_id=employee.id,
                service_name="sso",
                status="pending",
                depends_on_provisioning_id=email_pr.id,
                notes="Pending single sign-on setup"
            )
            db.add(sso_pr)
            db.flush()

        for svc in ["slack", "github"]:
            svc_pr = db.scalar(
                select(EmployeeProvisioningRequest).where(
                    EmployeeProvisioningRequest.employee_id == employee.id,
                    EmployeeProvisioningRequest.service_name == svc
                )
            )
            if not svc_pr:
                svc_pr = EmployeeProvisioningRequest(
                    company_id=offer.company_id,
                    employee_id=employee.id,
                    service_name=svc,
                    status="pending",
                    depends_on_provisioning_id=sso_pr.id,
                    notes=f"Pending {svc} workspace invitation"
                )
                db.add(svc_pr)

        # Create welcome events & check-ins
        from models.employee_welcome_event import EmployeeWelcomeEvent
        for name, desc, delta_days, hour, duration in [
            ("Orientation Day 1 Welcome", "Meet the HR team and get set up", 14, 9, 60),
            ("Manager Check-in", "Synchronize with your direct supervisor", 14, 13, 30),
            ("30-day Review", "First month onboarding review session", 44, 10, 30),
            ("60-day Review", "Second month onboarding review session", 74, 10, 30),
            ("90-day Review", "Third month onboarding review session", 104, 10, 30),
            ("Probation Review", "Final probation review check-in", 104, 14, 45)
        ]:
            evt_exists = db.scalar(
                select(EmployeeWelcomeEvent).where(
                    EmployeeWelcomeEvent.employee_id == employee.id,
                    EmployeeWelcomeEvent.event_name == name
                )
            )
            if not evt_exists:
                start_dt = datetime.combine(employee.start_date, datetime.min.time()) + timedelta(days=delta_days - 14) + timedelta(hours=hour)
                evt = EmployeeWelcomeEvent(
                    company_id=offer.company_id,
                    employee_id=employee.id,
                    event_name=name,
                    description=desc,
                    scheduled_at=start_dt.replace(tzinfo=timezone.utc),
                    duration_minutes=duration,
                    meeting_link="https://meet.google.com/abc-defg-hij"
                )
                db.add(evt)

        # Logging onboarding timeline audit milestone
        from models.employee_onboarding_audit import EmployeeOnboardingAudit
        audit_exists = db.scalar(
            select(EmployeeOnboardingAudit).where(
                EmployeeOnboardingAudit.employee_id == employee.id,
                EmployeeOnboardingAudit.action == "Offer Accepted"
            )
        )
        if not audit_exists:
            aud = EmployeeOnboardingAudit(
                company_id=offer.company_id,
                employee_id=employee.id,
                actor_id=candidate_user.id,
                actor_type="employee",
                action="Offer Accepted",
                details={"offer_id": str(offer.id)}
            )
            db.add(aud)

        # 4. Trigger HRIS Workflow / integration updates & Onboarding Outbox

        from models.employees import OnboardingEventOutbox
        outbox_exists = db.scalar(
            select(OnboardingEventOutbox).where(
                OnboardingEventOutbox.company_id == offer.company_id,
                OnboardingEventOutbox.event_type == "offer.accepted",
                OnboardingEventOutbox.payload["offer_id"].as_string() == str(offer.id)
            )
        )
        if not outbox_exists:
            outbox = OnboardingEventOutbox(
                company_id=offer.company_id,
                event_type="offer.accepted",
                payload={
                    "offer_id": str(offer.id),
                    "application_id": str(offer.application_id),
                    "candidate_email": candidate_user.email,
                    "hired_at": datetime.now(timezone.utc).isoformat()
                },
                status="pending"
            )
            db.add(outbox)
            logger.info(f"Triggered HRIS import/export sync outbox entry for candidate {candidate_user.email} into company {offer.company_id}")

        db.commit()
        db.close()
        return {"success": True}







