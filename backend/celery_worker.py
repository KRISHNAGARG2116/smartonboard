import os
import sys
import uuid
import logging
from pathlib import Path
from sqlalchemy import select, delete

# Add backend directory to python import path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.celery_app import celery_app
from db.session import tenant_context, SessionLocal
from pipeline import process_candidate
from models import Candidate, Application, Job, CandidateEmbedding
from models.enums import ApplicationStatus
from core.embeddings import EmbeddingService
from core.audit import log_audit_event

logger = logging.getLogger("celery")


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
                    source="AI Application"
                )
                db.add(application)
                db.flush()
            else:
                application.status = ApplicationStatus.SCREENING
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
