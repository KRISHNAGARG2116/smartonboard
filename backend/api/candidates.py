import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select, text

from api.deps import RequireOwner, TenantDb, RequireRecruiter
from models import Candidate, CandidateEmbedding
from schemas.candidate import CandidateDeletionRequest
from core.audit import log_audit_event, pseudonymize_audit_logs
from core.embeddings import EmbeddingService


router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/{candidate_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: uuid.UUID,
    body: CandidateDeletionRequest,
    request: Request,
    current_user: RequireOwner, # Strictly enforces Owner only!
    db: TenantDb,
):
    # 1. Enforce Explicit Confirmation
    if not body.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit confirmation ('confirm': true) is required to execute candidate deletion"
        )

    # 2. Fetch Candidate (Strictly tenant-scoped via RLS and select)
    candidate = db.scalar(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.company_id == current_user.company_id
        )
    )
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    candidate_email = candidate.email
    actor_id = current_user.id
    company_id = current_user.company_id
    actor_role = current_user.role.value.upper() # Dynamically set to OWNER

    try:
        # STEP 1: Create candidate.deleted log (PII-free) prior to erasure
        log_audit_event(
            db=db,
            action="candidate.deleted",
            actor_type=actor_role, # Dynamically reflects authenticated user role (OWNER)
            actor_id=actor_id,
            company_id=company_id,
            resource_type="candidates",
            resource_id=str(candidate_id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "candidate_id": str(candidate_id),
                "actor_id": str(actor_id),
                "company_id": str(company_id)
            }
        )

        # STEP 2: Pseudonymize historical active audit logs without committing internally
        pseudonymize_audit_logs(
            db=db,
            candidate_id=candidate_id,
            candidate_email=candidate_email,
            commit=False # Disables internal commit to avoid nested transaction commits
        )

        # STEP 3: Delete candidate record (Triggering all database foreign key cascades)
        db.delete(candidate)

        # STEP 4: Commit entire changes atomically
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute candidate GDPR deletion workflow: {str(e)}"
        ) from e
    finally:
        # Always restore the bypass configuration to false for connection pool security isolation
        try:
            db.execute(text("SELECT set_config('app.bypass_audit_immutability', 'false', true)"))
        except Exception:
            pass


@router.post("/compare")
def compare_candidates(
    body: dict,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb
):
    """
    AI-assisted candidate comparison endpoint. Compares multiple candidates
    against job descriptions or resumes, returning a detailed comparative report.
    """
    candidate_ids_str = body.get("candidate_ids", [])
    job_desc = body.get("job_description", "").strip()

    if not candidate_ids_str:
        raise HTTPException(status_code=400, detail="candidate_ids list cannot be empty.")
    if len(candidate_ids_str) > 5:
        raise HTTPException(status_code=400, detail="Cannot compare more than 5 candidates simultaneously.")
    if not job_desc:
        raise HTTPException(status_code=400, detail="job_description cannot be empty.")

    candidate_ids = []
    for cid in candidate_ids_str:
        try:
            candidate_ids.append(uuid.UUID(cid))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid UUID string: {cid}")

    # Fetch Candidates (RLS isolated)
    stmt = (
        select(Candidate)
        .where(
            Candidate.company_id == current_user.company_id,
            Candidate.id.in_(candidate_ids)
        )
    )
    candidates = db.scalars(stmt).all()
    if not candidates:
        raise HTTPException(status_code=404, detail="No matching candidates found.")

    candidates_context = ""
    for cand in candidates:
        # Fetch chunk texts for the candidate
        ch_stmt = (
            select(CandidateEmbedding.chunk_text)
            .where(
                CandidateEmbedding.company_id == current_user.company_id,
                CandidateEmbedding.candidate_id == cand.id
            )
            .order_by(CandidateEmbedding.chunk_index.asc())
        )
        chunks = db.scalars(ch_stmt).all()
        resume_text = "\n".join(chunks) if chunks else "No resume content available."
        
        candidates_context += f"""
---
[Candidate ID: {cand.id}]
Full Name: {cand.full_name}
Email: {cand.email}
Resume Content:
{resume_text[:4000]}
---
"""

    prompt = f"""You are an expert AI recruiting assistant. Compare the following candidates for the job description below.
Provide a detailed comparison analysis including:
1. Candidate Strengths and Gaps relative to the job.
2. Comparative evaluation matrix.
3. A final hiring recommendation ranking the candidates.

Job Description:
{job_desc}

Candidates Context:
{candidates_context}

Deliver the report formatted in beautiful, readable markdown."""

    from langchain_groq import ChatGroq
    llm = ChatGroq(model_name="llama-3.3-70b-versatile")
    result = llm.invoke(prompt)
    report = result.content.strip()

    # Log ai.candidates_compared compliance audit event
    log_audit_event(
        db=db,
        action="ai.candidates_compared",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="candidates",
        resource_id=str(candidates[0].id) if candidates else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "compared_candidate_count": len(candidates),
            "candidate_ids": [str(c.id) for c in candidates]
        }
    )

    return {
        "comparison_report": report
    }

