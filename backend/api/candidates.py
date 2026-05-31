import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select, text

from api.deps import RequireOwner, TenantDb
from models import Candidate
from schemas.candidate import CandidateDeletionRequest
from core.audit import log_audit_event, pseudonymize_audit_logs

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
