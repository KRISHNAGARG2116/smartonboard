import uuid
from typing import Annotated
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select, text

from api.deps import RequireOwner, TenantDb, RequireRecruiter, RequirePermission, has_job_access
from models import Candidate, CandidateEmbedding, User
from models.rbac import UserPermission
from schemas.candidate import (
    CandidateDeletionRequest,
    CandidateAssignmentPayload,
    CandidateTagsPayload,
    CandidateMergePayload,
    CandidateTagCreate,
    CandidateTagUpdate,
    CandidateTagResponse,
)
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


@router.get("/{candidate_id}/timeline")
def get_candidate_timeline(
    candidate_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.VIEW_CANDIDATES))],
    db: TenantDb,
    event_type: str | None = None,
):
    """
    Returns chronological timeline events registered in ApplicationEvent for the candidate's applications.
    Enforces privacy-level checks for Note type events.
    """
    from models.application import Application
    from models.ats_models import ApplicationEvent
    from models.enums import UserRole

    # 1. Fetch applications for the candidate
    stmt = select(Application).where(
        Application.candidate_id == candidate_id,
        Application.company_id == current_user.company_id
    )
    apps = db.scalars(stmt).all()
    if not apps:
        return []

    app_ids = [app.id for app in apps]

    # 2. Fetch all events for these applications
    event_stmt = select(ApplicationEvent).where(
        ApplicationEvent.application_id.in_(app_ids)
    )
    if event_type:
        event_stmt = event_stmt.where(ApplicationEvent.event_type == event_type)
    
    event_stmt = event_stmt.order_by(ApplicationEvent.created_at.asc())
    events = db.scalars(event_stmt).all()

    # 3. Notes visibility check
    filtered_events = []
    for e in events:
        vis = e.metadata_json.get("visibility", "everyone")
        author_id = e.metadata_json.get("author_id")

        if vis == "private" and str(current_user.id) != str(author_id):
            continue
        elif vis == "hiring_team":
            app = next((a for a in apps if a.id == e.application_id), None)
            if app:
                is_hiring_team = (
                    current_user.role == UserRole.OWNER or
                    str(app.owner_id) == str(current_user.id) or
                    any(str(r.id) == str(current_user.id) for r in app.secondary_recruiters)
                )
                if not is_hiring_team:
                    continue
        filtered_events.append(e)

    return filtered_events


@router.post("/{candidate_id}/assign")
def assign_candidate(
    candidate_id: uuid.UUID,
    payload: CandidateAssignmentPayload,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MOVE_CANDIDATES))],
    db: TenantDb,
):
    """
    Links candidate primary owner, secondary recruiters, and watchers.
    """
    from models.application import Application
    from core.timeline import log_application_event

    # 1. Fetch latest active application
    app = db.scalar(
        select(Application).where(
            Application.candidate_id == candidate_id,
            Application.company_id == current_user.company_id
        ).order_by(Application.created_at.desc())
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active application found for this candidate")

    if not has_job_access(db, current_user, app.job_id, "write"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No write access to this job")

    # 2. Update primary owner
    if payload.owner_id:
        owner = db.get(User, payload.owner_id)
        if not owner or owner.company_id != current_user.company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner recruiter not found")
        app.owner_id = payload.owner_id
    else:
        app.owner_id = None

    # 3. Update secondary recruiters
    if payload.secondary_recruiters:
        secs = db.scalars(
            select(User).where(User.id.in_(payload.secondary_recruiters), User.company_id == current_user.company_id)
        ).all()
        app.secondary_recruiters = list(secs)
    else:
        app.secondary_recruiters = []

    # 4. Update watchers
    if payload.watchers:
        wats = db.scalars(
            select(User).where(User.id.in_(payload.watchers), User.company_id == current_user.company_id)
        ).all()
        app.watchers = list(wats)
    else:
        app.watchers = []

    db.commit()

    # Log timeline event
    log_application_event(
        db=db,
        application_id=app.id,
        event_type="application.assigned",
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        metadata={
            "owner_id": str(payload.owner_id) if payload.owner_id else None,
            "secondary_recruiters": [str(r) for r in payload.secondary_recruiters],
            "watchers": [str(w) for w in payload.watchers],
        }
    )

    return {"status": "success", "message": "Recruiters successfully assigned to candidate"}


@router.post("/{candidate_id}/tags")
def update_candidate_tags(
    candidate_id: uuid.UUID,
    payload: CandidateTagsPayload,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MOVE_CANDIDATES))],
    db: TenantDb,
):
    """
    Associates tags to the candidate.
    """
    from models.ats_models import CandidateTag

    candidate = db.scalar(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.company_id == current_user.company_id
        )
    )
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    tags = db.scalars(
        select(CandidateTag).where(
            CandidateTag.id.in_(payload.tag_ids),
            CandidateTag.company_id == current_user.company_id
        )
    ).all()

    candidate.tags = list(tags)
    db.commit()

    return {"status": "success", "message": "Tags updated successfully"}


@router.get("/{candidate_id}/duplicates")
def get_candidate_duplicates(
    candidate_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.VIEW_CANDIDATES))],
    db: TenantDb,
):
    """
    Checks for duplicate candidates, saves findings to the duplicate_warnings table,
    and returns matched fields evidence.
    """
    candidate = db.scalar(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.company_id == current_user.company_id
        )
    )
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    from models.ats_models import DuplicateWarning
    from models.candidate_resume import CandidateResume

    duplicates = []
    
    # 1. Email check
    if candidate.email:
        email_matches = db.scalars(
            select(Candidate).where(
                Candidate.email == candidate.email,
                Candidate.id != candidate.id,
                Candidate.company_id == candidate.company_id
            )
        ).all()
        for c in email_matches:
            confidence = 100
            fields = {"email": True, "phone": False, "resume_hash": False, "name_similarity": 1.0}
            reason = "Email address matches exactly."
            duplicates.append((c, confidence, fields, reason))

    # 2. Resume file hash check
    candidate_resumes = db.scalars(
        select(CandidateResume).where(CandidateResume.user_id == candidate.id, CandidateResume.is_active == True)
    ).all()
    hashes = [r.file_hash for r in candidate_resumes if r.file_hash]
    if hashes:
        hash_matches = db.scalars(
            select(CandidateResume).where(
                CandidateResume.file_hash.in_(hashes),
                CandidateResume.user_id != candidate.id
            )
        ).all()
        for r in hash_matches:
            c = db.get(Candidate, r.user_id)
            if c and c.company_id == candidate.company_id:
                confidence = 100
                fields = {"email": False, "phone": False, "resume_hash": True, "name_similarity": 1.0}
                reason = f"Resume file hash matches exactly ({r.filename})."
                duplicates.append((c, confidence, fields, reason))

    # 3. Phone check
    if candidate.phone:
        phone_matches = db.scalars(
            select(Candidate).where(
                Candidate.phone == candidate.phone,
                Candidate.id != candidate.id,
                Candidate.company_id == candidate.company_id
            )
        ).all()
        for c in phone_matches:
            confidence = 90
            fields = {"email": False, "phone": True, "resume_hash": False, "name_similarity": 1.0}
            reason = "Phone number matches exactly."
            duplicates.append((c, confidence, fields, reason))

    # Save to database
    for dup_candidate, confidence, fields, reason in duplicates:
        existing = db.scalar(
            select(DuplicateWarning).where(
                DuplicateWarning.company_id == candidate.company_id,
                (
                    (DuplicateWarning.candidate_id == candidate.id) & (DuplicateWarning.duplicate_candidate_id == dup_candidate.id)
                ) | (
                    (DuplicateWarning.candidate_id == dup_candidate.id) & (DuplicateWarning.duplicate_candidate_id == candidate.id)
                )
            )
        )
        if not existing:
            warning = DuplicateWarning(
                company_id=candidate.company_id,
                candidate_id=candidate.id,
                duplicate_candidate_id=dup_candidate.id,
                confidence_score=confidence,
                matched_fields=fields,
                reason=reason,
                status="pending"
            )
            db.add(warning)
            
    db.commit()

    # Query resolved/pending duplicate warnings for this candidate
    warnings = db.scalars(
        select(DuplicateWarning).where(
            DuplicateWarning.company_id == current_user.company_id,
            (DuplicateWarning.candidate_id == candidate_id) | (DuplicateWarning.duplicate_candidate_id == candidate_id)
        )
    ).all()

    response = []
    for w in warnings:
        other_id = w.duplicate_candidate_id if w.candidate_id == candidate_id else w.candidate_id
        other_cand = db.get(Candidate, other_id)
        if other_cand:
            response.append({
                "id": str(w.id),
                "candidate_id": str(other_cand.id),
                "full_name": other_cand.full_name,
                "email": other_cand.email,
                "phone": other_cand.phone,
                "confidence_score": w.confidence_score,
                "matched_fields": w.matched_fields,
                "reason": w.reason,
                "status": w.status,
                "resolved_at": w.resolved_at.isoformat() if w.resolved_at else None,
                "resolved_by": str(w.resolved_by) if w.resolved_by else None
            })

    return response


class DuplicateResolvePayload(BaseModel):
    status: str = Field(..., description="Target status: ignored, reviewed, merged")


@router.post("/{candidate_id}/duplicates/{warning_id}/resolve")
def resolve_candidate_duplicate(
    candidate_id: uuid.UUID,
    warning_id: uuid.UUID,
    payload: DuplicateResolvePayload,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MOVE_CANDIDATES))],
    db: TenantDb,
):
    """
    Sets resolved status (ignored, reviewed, merged) on a candidate duplicate warning.
    """
    from models.ats_models import DuplicateWarning
    warning = db.scalar(
        select(DuplicateWarning).where(
            DuplicateWarning.id == warning_id,
            DuplicateWarning.company_id == current_user.company_id,
            (DuplicateWarning.candidate_id == candidate_id) | (DuplicateWarning.duplicate_candidate_id == candidate_id)
        )
    )
    if not warning:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Duplicate warning not found")

    allowed_status = {"ignored", "reviewed", "merged"}
    if payload.status not in allowed_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Status must be one of: {allowed_status}")

    warning.status = payload.status
    warning.resolved_at = datetime.now(timezone.utc)
    warning.resolved_by = current_user.id
    db.commit()

    return {"status": "success", "message": "Duplicate warning resolved successfully"}


@router.post("/{candidate_id}/merge")
def merge_candidate(
    candidate_id: uuid.UUID,
    payload: CandidateMergePayload,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MOVE_CANDIDATES))],
    db: TenantDb,
):
    """
    Merge Candidate stub: re-links applications, resumes, and notes of
    the merged candidate to the surviving candidate.
    """
    from models.application import Application
    from models.candidate_resume import CandidateResume
    from models.note import CandidateNote
    from core.timeline import log_application_event

    merged = db.scalar(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.company_id == current_user.company_id
        )
    )
    surviving = db.scalar(
        select(Candidate).where(
            Candidate.id == payload.surviving_candidate_id,
            Candidate.company_id == current_user.company_id
        )
    )
    if not merged or not surviving:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merged or surviving candidate not found")

    # 1. Re-link applications
    stmt_apps = select(Application).where(Application.candidate_id == merged.id)
    apps = db.scalars(stmt_apps).all()
    for app in apps:
        app.candidate_id = surviving.id

    # 2. Re-link resumes
    stmt_res = select(CandidateResume).where(CandidateResume.user_id == merged.id)
    resumes = db.scalars(stmt_res).all()
    for res in resumes:
        res.user_id = surviving.id

    # 3. Re-link notes
    stmt_notes = select(CandidateNote).where(CandidateNote.user_id == merged.id)
    notes = db.scalars(stmt_notes).all()
    for note in notes:
        note.user_id = surviving.id

    # 4. Mark merged candidate as merged (is_active = False and suffix to email)
    if merged.email:
        merged.email = f"{merged.email}.merged.{uuid.uuid4().hex[:6]}"
    merged.full_name = f"[Merged] {merged.full_name}"

    db.commit()

    # Log event on surviving applications
    for app in apps:
        log_application_event(
            db=db,
            application_id=app.id,
            event_type="candidate.merged",
            actor_id=current_user.id,
            actor_name=current_user.full_name,
            metadata={
                "merged_candidate_id": str(merged.id),
                "surviving_candidate_id": str(surviving.id),
            }
        )

    return {
        "status": "success",
        "message": f"Candidate {merged.id} successfully merged into candidate {surviving.id}."
    }


@router.get("/tags", response_model=list[CandidateTagResponse])
def list_company_tags(
    db: TenantDb,
    current_user: RequireRecruiter,
):
    from models.ats_models import CandidateTag
    return list(db.scalars(select(CandidateTag).where(CandidateTag.company_id == current_user.company_id)).all())


@router.post("/tags", response_model=CandidateTagResponse, status_code=status.HTTP_201_CREATED)
def create_company_tag(
    body: CandidateTagCreate,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    from models.ats_models import CandidateTag
    # Enforce tag uniqueness per company
    existing = db.scalar(
        select(CandidateTag).where(
            CandidateTag.company_id == current_user.company_id,
            CandidateTag.name.ilike(body.name)
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tag '{body.name}' already exists.")

    tag = CandidateTag(
        company_id=current_user.company_id,
        name=body.name,
        color=body.color,
        icon=body.icon
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.patch("/tags/{tag_id}", response_model=CandidateTagResponse)
def update_company_tag(
    tag_id: uuid.UUID,
    body: CandidateTagUpdate,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    from models.ats_models import CandidateTag
    tag = db.scalar(
        select(CandidateTag).where(
            CandidateTag.id == tag_id,
            CandidateTag.company_id == current_user.company_id
        )
    )
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")

    if body.name is not None:
        tag.name = body.name
    if body.color is not None:
        tag.color = body.color
    if body.icon is not None:
        tag.icon = body.icon

    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_tag(
    tag_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    from models.ats_models import CandidateTag
    tag = db.scalar(
        select(CandidateTag).where(
            CandidateTag.id == tag_id,
            CandidateTag.company_id == current_user.company_id
        )
    )
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")

    db.delete(tag)
    db.commit()


