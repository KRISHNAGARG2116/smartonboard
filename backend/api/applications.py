import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.deps import CurrentUser, TenantDb, RequireRecruiter, has_job_access
from models import Application, Candidate, Job, CandidateEmbedding, StageDefinition, User
from models.enums import ApplicationStatus
from schemas.application import (
    ApplicationCreateRequest,
    ApplicationResponse,
    ApplicationUpdateRequest,
    CandidateBrief,
    JobBrief,
    BulkUpdatePreviewPayload,
    BulkUpdatePayload,
    BulkUpdatePreviewResponse,
    BulkPreviewWarning,
)

from fastapi import File, Form, UploadFile
from celery.result import AsyncResult
from celery_worker import (
    process_resume_async,
    track_stage_transition_async,
    track_recruiter_productivity_async,
)
from core.celery_app import celery_app
from core.malware import scan_file_for_malware
from core.signature import validate_file_signature
from core.storage import LocalStorageService
from core.embeddings import EmbeddingService
from pathlib import Path


STORAGE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"
storage_service = LocalStorageService(STORAGE_BASE_DIR)


router = APIRouter(prefix="/applications", tags=["applications"])


def _parse_application_status(value: str) -> ApplicationStatus:
    try:
        return ApplicationStatus(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid application status"
        ) from exc


def _application_response(application: Application) -> ApplicationResponse:
    return ApplicationResponse(
        id=application.id,
        company_id=application.company_id,
        job_id=application.job_id,
        candidate_id=application.candidate_id,
        status=application.status.value,
        source=application.source,
        created_at=application.created_at,
        updated_at=application.updated_at,
        match_score=application.match_score,
        candidate=CandidateBrief.model_validate(application.candidate) if application.candidate else None,
        job=JobBrief.model_validate(application.job) if application.job else None,
        current_stage_id=application.current_stage_id,
        owner_id=application.owner_id,
    )


@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    db: TenantDb,
    job_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
):
    stmt = (
        select(Application)
        .options(selectinload(Application.candidate), selectinload(Application.job))
        .order_by(Application.created_at.desc())
    )
    if job_id:
        stmt = stmt.where(Application.job_id == job_id)
    if status_filter:
        stmt = stmt.where(Application.status == _parse_application_status(status_filter))
    return [_application_response(a) for a in db.scalars(stmt).all()]


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    body: ApplicationCreateRequest,
    request: Request,
    current_user: CurrentUser,
    db: TenantDb
):
    job = db.scalar(select(Job).where(Job.id == body.job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    candidate = db.scalar(
        select(Candidate).where(
            Candidate.company_id == current_user.company_id,
            Candidate.email == body.candidate_email.lower(),
        )
    )
    new_candidate_created = False
    if candidate is None:
        candidate = Candidate(
            company_id=current_user.company_id,
            email=body.candidate_email.lower(),
            full_name=body.candidate_name,
            phone=body.candidate_phone,
        )
        db.add(candidate)
        db.flush()
        new_candidate_created = True
    else:
        candidate.full_name = body.candidate_name
        if body.candidate_phone:
            candidate.phone = body.candidate_phone

    existing = db.scalar(
        select(Application).where(
            Application.job_id == body.job_id,
            Application.candidate_id == candidate.id,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate already applied to this job",
        )

    application = Application(
        company_id=current_user.company_id,
        job_id=body.job_id,
        candidate_id=candidate.id,
        status=ApplicationStatus.SUBMITTED,
        source=body.source,
    )
    db.add(application)
    db.commit()

    if new_candidate_created:
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="candidate.created",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            resource_type="candidates",
            resource_id=str(candidate.id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"email": candidate.email, "full_name": candidate.full_name, "phone": candidate.phone}
        )

    application = db.scalar(
        select(Application)
        .options(selectinload(Application.candidate), selectinload(Application.job))
        .where(Application.id == application.id)
    )
    return _application_response(application)


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(application_id: uuid.UUID, db: TenantDb):
    application = db.scalar(
        select(Application)
        .options(selectinload(Application.candidate), selectinload(Application.job))
        .where(Application.id == application_id)
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return _application_response(application)


@router.patch("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: uuid.UUID,
    body: ApplicationUpdateRequest,
    request: Request,
    current_user: CurrentUser,
    db: TenantDb
):
    from datetime import datetime, timezone, timedelta
    from models.enums import UserRole
    from core.workflows import transition_candidate_stage, ensure_job_stages
    from core.application_events import ApplicationEventService

    application = db.scalar(
        select(Application)
        .options(selectinload(Application.candidate), selectinload(Application.job))
        .where(Application.id == application_id)
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # 1. Optimistic Concurrency Check
    if body.client_updated_at is not None:
        db_updated = application.updated_at
        client_updated = body.client_updated_at
        if db_updated and client_updated:
            db_u_naive = db_updated.astimezone(timezone.utc).replace(tzinfo=None) if db_updated.tzinfo else db_updated
            cl_u_naive = client_updated.astimezone(timezone.utc).replace(tzinfo=None) if client_updated.tzinfo else client_updated
            if db_u_naive > cl_u_naive + timedelta(milliseconds=1):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Application has been modified by another user. Please reload and try again."
                )

    # 2. Ownership Restriction Check
    if application.owner_id is not None:
        if current_user.id != application.owner_id and current_user.role != UserRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only the application owner or a Company Owner can edit this application."
            )

    # Wrap writes in a transaction block
    with db.begin_nested():
        # 3. Handle owner assignment
        if body.owner_id is not None or (hasattr(body, 'owner_id') and body.owner_id is None and application.owner_id is not None):
            if body.owner_id is not None:
                target_user = db.scalar(select(User).where(User.id == body.owner_id, User.company_id == current_user.company_id))
                if not target_user:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned owner must belong to the same company.")
            
            old_owner_id = str(application.owner_id) if application.owner_id else None
            new_owner_id = str(body.owner_id) if body.owner_id else None
            if old_owner_id != new_owner_id:
                application.owner_id = body.owner_id
                db.flush()
                # Log timeline event
                ApplicationEventService.record_event(
                    db=db,
                    company_id=current_user.company_id,
                    application_id=application.id,
                    event_type="application.owner_assigned",
                    actor_id=current_user.id,
                    previous_value=old_owner_id,
                    new_value=new_owner_id,
                    metadata={
                        "previous_owner": old_owner_id,
                        "new_owner": new_owner_id
                    }
                )

        # 4. Handle stage transition
        if body.current_stage_id is not None:
            transition_candidate_stage(
                db=db,
                company_id=current_user.company_id,
                application_id=application.id,
                target_stage_id=body.current_stage_id,
                actor_id=current_user.id
            )
        elif body.status is not None:
            new_status = _parse_application_status(body.status)
            status_to_cat = {
                ApplicationStatus.SUBMITTED: "applied",
                ApplicationStatus.SCREENING: "screening",
                ApplicationStatus.INTERVIEW: "interviewing",
                ApplicationStatus.OFFER: "offered",
                ApplicationStatus.HIRED: "hired",
                ApplicationStatus.REJECTED: "rejected",
            }
            target_cat = status_to_cat.get(new_status, "screening")
            stages = ensure_job_stages(db, application.job_id, current_user.company_id)
            target_stage = next((s for s in stages if s.base_category == target_cat and s.deleted_at is None), None)
            if target_stage:
                transition_candidate_stage(
                    db=db,
                    company_id=current_user.company_id,
                    application_id=application.id,
                    target_stage_id=target_stage.id,
                    actor_id=current_user.id
                )

    db.commit()
    db.refresh(application)
    return _application_response(application)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: uuid.UUID,
    request: Request,
    current_user: RequireRecruiter, # Recruiter allowed
    db: TenantDb,
):
    # 1. Fetch Application under company context (RLS verified)
    application = db.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.company_id == current_user.company_id
        )
    )
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        
    actor_id = current_user.id
    company_id = current_user.company_id
    actor_role = current_user.role.value.upper()

    try:
        # 2. Log application.deleted audit event prior to cascade deletion
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="application.deleted",
            actor_type=actor_role,
            actor_id=actor_id,
            company_id=company_id,
            resource_type="applications",
            resource_id=str(application_id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "application_id": str(application_id),
                "actor_id": str(actor_id),
                "company_id": str(company_id)
            }
        )

        # 3. Delete Application (Cascades automatically to notes, interviews, scorecards, offers)
        db.delete(application)
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute application deletion workflow"
        ) from e


@router.post("/async", status_code=status.HTTP_202_ACCEPTED)
async def create_application_async(
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb,
    job_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
):
    """
    Asynchronously parses a candidate's resume, executes LangGraph evaluation,
    generates embeddings, and creates/updates the application state.
    Returns 202 Accepted with a task identifier.
    """
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    # 1. Early Content-Length validation
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 5 MB.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 5 MB.")

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # 2. Magic Bytes Signature & Static Malware Validation in Request Thread
    from core.malware import EICAR_SIGNATURE
    if EICAR_SIGNATURE in pdf_bytes:
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="file.scan_failure",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            resource_type="quarantine",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"filename": file.filename, "error": "Malware detected: EICAR test signature found.", "event": "malware_detected"}
        )
        raise HTTPException(status_code=400, detail="Malware detected: EICAR test signature found.")

    try:
        validate_file_signature(pdf_bytes, file.filename or "")
    except ValueError as sig_err:
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="file.signature_failure",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            resource_type="quarantine",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"filename": file.filename, "error": str(sig_err), "event": "invalid_signature"}
        )
        raise HTTPException(status_code=400, detail=str(sig_err))

    # 3. Job Validation
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.company_id == current_user.company_id
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Enforce parsed candidate billing quota pre-flight check
    from core.quota import check_quota_pre_flight
    check_quota_pre_flight(db, current_user.company_id, "candidates_processed")

    # 4. Save to quarantine staging directory
    quarantine_path = storage_service.save_quarantine(pdf_bytes, file.filename or "file.dat")

    # 5. Write record in quarantined_files database table
    from models.quarantine import QuarantinedFile
    q_rec = QuarantinedFile(
        company_id=current_user.company_id,
        filename=file.filename or "file.dat",
        quarantine_path=str(quarantine_path),
        is_safe=None  # Pending
    )
    db.add(q_rec)
    db.flush()
    q_file_id = q_rec.id
    db.commit()

    # 6. Dispatch task to Celery worker queue
    from celery_worker import scan_and_promote_resume_task
    evaluation_id = str(uuid.uuid4())
    task = scan_and_promote_resume_task.delay(
        quarantine_file_id=str(q_file_id),
        job_id=str(job_id),
        evaluation_id=evaluation_id
    )

    return {
        "task_id": task.id,
        "quarantine_file_id": str(q_file_id),
        "status": "PENDING"
    }


@router.get("/async/status/{task_id}")
def get_application_async_status(
    task_id: str,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    """
    Checks the status of the asynchronous recruitment task.
    """
    res = AsyncResult(task_id, app=celery_app)
    
    if res.state == "PENDING":
        return {"status": "PROCESSING"}
    elif res.state == "STARTED":
        return {"status": "PROCESSING"}
    elif res.state == "SUCCESS":
        return {"status": "COMPLETED", "result": res.result}
    elif res.state == "FAILURE":
        return {"status": "FAILED", "error": str(res.result)}
    elif res.state == "REVOKED":
        return {"status": "FAILED", "error": "Task was revoked or cancelled."}
    
    return {"status": res.state}


@router.post("/{application_id}/qa")
def qa_candidate_resume(
    application_id: uuid.UUID,
    body: dict,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb
):
    """
    Interactive conversational resume Q&A (RAG) assistant grounded securely on candidate resume chunks.
    Enforces a strict similarity threshold of 0.35. If all chunks fall below, returns a grounded refusal.
    Logs RAG compliance audit events with zero generated answers leakage.
    """
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
        
    application = db.scalar(
        select(Application)
        .options(selectinload(Application.candidate))
        .where(
            Application.id == application_id,
            Application.company_id == current_user.company_id
        )
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
        
    candidate = application.candidate
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    # Embed recruiter's question
    embedder = EmbeddingService()
    query_vector = embedder.generate_embedding(question)
    
    # Query candidate chunks (RLS filtered)
    stmt = (
        select(CandidateEmbedding)
        .where(
            CandidateEmbedding.company_id == current_user.company_id,
            CandidateEmbedding.candidate_id == candidate.id
        )
    )
    embeddings = db.scalars(stmt).all()
    
    # Rank chunks by similarity score
    scored_chunks = []
    for emb in embeddings:
        score = embedder.compute_similarity(query_vector, emb.resume_embedding)
        scored_chunks.append({
            "chunk_text": emb.chunk_text,
            "similarity_score": score,
            "chunk_index": emb.chunk_index
        })
        
    # Sort descending
    scored_chunks.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    THRESHOLD = 0.35
    top_chunks = [c for c in scored_chunks[:3] if c["similarity_score"] >= THRESHOLD]
    
    # Audit event: ai.rag_queried
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="ai.rag_queried",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="applications",
        resource_id=str(application_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "application_id": str(application_id),
            "candidate_id": str(candidate.id),
            "question_length": len(question)
        }
    )

    model_version = "llama-3.3-70b-versatile"

    if not top_chunks:
        answer = "I apologize, but the candidate's resume does not specify or contain information relevant to your question."
        
        # Audit event: ai.rag_answer_generated (Metadata only, no answer content)
        log_audit_event(
            db=db,
            action="ai.rag_answer_generated",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            resource_type="applications",
            resource_id=str(application_id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "application_id": str(application_id),
                "source_chunk_count": 0,
                "model_version": model_version,
                "threshold_blocked": True
            }
        )
        
        return {
            "answer": answer,
            "source_chunks": []
        }
        
    # Construct RAG Prompt
    context_str = ""
    for idx, chunk in enumerate(top_chunks):
        context_str += f"\n[Source Chunk {idx+1} (Index {chunk['chunk_index']})]\n{chunk['chunk_text']}\n"
        
    prompt = f"""You are an AI recruitment assistant. Answer the recruiter's question using ONLY the provided resume context.
If the context does not contain the answer, politely state that the resume does not specify this information.
Do not invent facts or extrapolate beyond the provided text.

Candidate: {candidate.full_name}
Question: {question}

Context:
{context_str}

Answer concisely and professionally."""

    from langchain_groq import ChatGroq
    llm = ChatGroq(model_name=model_version)
    result = llm.invoke(prompt)
    answer = result.content.strip()
    
    # Audit event: ai.rag_answer_generated (Metadata only, no answer content)
    log_audit_event(
        db=db,
        action="ai.rag_answer_generated",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="applications",
        resource_id=str(application_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "application_id": str(application_id),
            "source_chunk_count": len(top_chunks),
            "model_version": model_version,
            "threshold_blocked": False
        }
    )
    
    return {
        "answer": answer,
        "source_chunks": [
            {
                "chunk_text": c["chunk_text"],
                "similarity_score": round(c["similarity_score"], 4),
                "chunk_index": c["chunk_index"]
            }
            for c in top_chunks
        ]
    }


@router.post("/{application_id}/sla/pause")
def pause_application_sla(
    application_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    """
    Manually pauses the active SLA tracker for the application.
    """
    from models.sla import CandidateStageSLATracker
    from datetime import datetime, timezone

    tracker = db.scalar(
        select(CandidateStageSLATracker).where(
            CandidateStageSLATracker.application_id == application_id,
            CandidateStageSLATracker.status == "active",
            CandidateStageSLATracker.company_id == current_user.company_id
        )
    )
    if not tracker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active SLA tracker found to pause for this application."
        )

    tracker.paused_at = datetime.now(timezone.utc)
    tracker.status = "paused"
    db.commit()

    return {"status": "success", "message": "SLA timer paused successfully"}


@router.post("/{application_id}/sla/resume")
def resume_application_sla(
    application_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    """
    Manually resumes a paused SLA tracker for the application.
    """
    from models.sla import CandidateStageSLATracker
    from datetime import datetime, timezone, timedelta

    tracker = db.scalar(
        select(CandidateStageSLATracker).where(
            CandidateStageSLATracker.application_id == application_id,
            CandidateStageSLATracker.status == "paused",
            CandidateStageSLATracker.company_id == current_user.company_id
        )
    )
    if not tracker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No paused SLA tracker found to resume for this application."
        )

    now = datetime.now(timezone.utc)
    if tracker.paused_at:
        paused_duration = (now - tracker.paused_at.replace(tzinfo=timezone.utc)).total_seconds()
        tracker.total_paused_seconds += int(paused_duration)
        tracker.expires_at = tracker.expires_at.replace(tzinfo=timezone.utc) + timedelta(seconds=paused_duration)
    tracker.paused_at = None
    tracker.status = "active"
    db.commit()

    return {"status": "success", "message": "SLA timer resumed successfully"}


@router.post("/bulk-update/preview", response_model=BulkUpdatePreviewResponse)
def bulk_update_preview(
    payload: BulkUpdatePreviewPayload,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    """
    Simulates stage movement and validation, returning conflict/exit warnings.
    """
    apps = db.scalars(
        select(Application)
        .options(selectinload(Application.candidate))
        .where(
            Application.id.in_(payload.application_ids),
            Application.company_id == current_user.company_id
        )
    ).all()

    warnings = []
    actions = []
    
    if payload.target_stage_id:
        stage = db.get(StageDefinition, payload.target_stage_id)
        stage_name = stage.name if stage else "unknown"
        actions.append(f"Move {len(payload.application_ids)} candidates to stage '{stage_name}'")
    if payload.target_status:
        actions.append(f"Set status of {len(payload.application_ids)} candidates to '{payload.target_status}'")
    if payload.target_owner_id:
        actions.append(f"Assign {len(payload.application_ids)} candidates to new owner")
    if payload.add_tags:
        actions.append(f"Add tag(s): {', '.join(payload.add_tags)}")
    if payload.remove_tags:
        actions.append(f"Remove tag(s): {', '.join(payload.remove_tags)}")
    if payload.archive is True:
        actions.append(f"Archive {len(payload.application_ids)} candidates")
    elif payload.archive is False:
        actions.append(f"Restore {len(payload.application_ids)} candidates")

    if actions:
        actions.append("Undo available for 5 minutes.")

    for app in apps:
        if app.status == ApplicationStatus.REJECTED and payload.target_stage_id:
            warnings.append(
                BulkPreviewWarning(
                    application_id=app.id,
                    candidate_name=app.candidate.full_name,
                    warning_type="rejected",
                    message="Candidate is already rejected."
                )
            )

        from models.interview import Interview
        from sqlalchemy import func
        scheduled_count = db.scalar(
            select(func.count(Interview.id)).where(
                Interview.application_id == app.id,
                Interview.status == "scheduled"
            )
        ) or 0
        if scheduled_count > 0 and payload.target_stage_id:
            warnings.append(
                BulkPreviewWarning(
                    application_id=app.id,
                    candidate_name=app.candidate.full_name,
                    warning_type="interview_conflict",
                    message=f"Candidate has {scheduled_count} scheduled interview(s) in progress."
                )
            )

        if payload.target_stage_id and app.current_stage_id:
            current_stage = db.get(StageDefinition, app.current_stage_id)
            if current_stage:
                from core.workflows import validate_stage_exit_requirements
                try:
                    validate_stage_exit_requirements(db, app, current_stage)
                except ValueError as val_err:
                    warnings.append(
                        BulkPreviewWarning(
                            application_id=app.id,
                            candidate_name=app.candidate.full_name,
                            warning_type="exit_requirement_violation",
                            message=str(val_err)
                        )
                    )

    return BulkUpdatePreviewResponse(
        total_applications=len(apps),
        warnings=warnings,
        actions=actions
    )


@router.post("/bulk-update")
def bulk_update_applications(
    payload: BulkUpdatePayload,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    """
    Executes bulk updates (stage change, status change, owner change, tags add/remove, archiving/restoring) as a single transaction,
    logging previous states for potential Undos.
    """
    apps = db.scalars(
        select(Application)
        .options(selectinload(Application.candidate))
        .where(
            Application.id.in_(payload.application_ids),
            Application.company_id == current_user.company_id
        )
    ).all()

    if not apps:
        return {"status": "success", "updated_count": 0}

    for app in apps:
        if not has_job_access(db, current_user, app.job_id, "write"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No write access to job for application {app.id}")

    previous_states = {}
    for app in apps:
        previous_states[str(app.id)] = {
            "current_stage_id": str(app.current_stage_id) if app.current_stage_id else None,
            "status": app.status.value if app.status else None,
            "owner_id": str(app.owner_id) if app.owner_id else None,
            "is_archived": app.is_archived,
            "archived_at": app.archived_at.isoformat() if app.archived_at else None,
            "archived_by": str(app.archived_by) if app.archived_by else None,
            "tag_ids": [str(t.id) for t in app.candidate.tags] if (app.candidate and app.candidate.tags) else []
        }

    from models.ats_models import BulkOperationLog
    op_log = BulkOperationLog(
        company_id=current_user.company_id,
        recruiter_id=current_user.id,
        action_type="move_stage" if payload.target_stage_id else "update_fields",
        affected_application_ids=[str(a.id) for a in apps],
        previous_states=previous_states
    )
    db.add(op_log)
    db.flush()

    from core.workflows import transition_candidate_stage
    from core.timeline import log_application_event
    from models.ats_models import CandidateTag

    for app in apps:
        if payload.target_stage_id:
            try:
                transition_candidate_stage(
                    db=db,
                    company_id=current_user.company_id,
                    application_id=app.id,
                    target_stage_id=payload.target_stage_id,
                    actor_id=current_user.id
                )
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        if payload.target_status:
            app.status = _parse_application_status(payload.target_status)

        if payload.target_owner_id:
            owner = db.get(User, payload.target_owner_id)
            if not owner or owner.company_id != current_user.company_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target owner user not found")
            app.owner_id = payload.target_owner_id

        if payload.add_tags and app.candidate:
            for tag_name in payload.add_tags:
                tag = db.scalar(
                    select(CandidateTag).where(
                        CandidateTag.company_id == current_user.company_id,
                        CandidateTag.name.ilike(tag_name)
                    )
                )
                if not tag:
                    tag = CandidateTag(company_id=current_user.company_id, name=tag_name, color="#6b7280")
                    db.add(tag)
                    db.flush()
                if tag not in app.candidate.tags:
                    app.candidate.tags.append(tag)

        if payload.remove_tags and app.candidate:
            app.candidate.tags = [t for t in app.candidate.tags if t.name.lower() not in {rt.lower() for rt in payload.remove_tags}]

        if payload.archive is True:
            app.is_archived = True
            app.archived_at = datetime.now(timezone.utc)
            app.archived_by = current_user.id
        elif payload.archive is False:
            app.is_archived = False
            app.archived_at = None
            app.archived_by = None

        log_application_event(
            db=db,
            application_id=app.id,
            event_type="application.bulk_updated",
            actor_id=current_user.id,
            actor_name=current_user.full_name,
            metadata={
                "bulk_operation_id": str(op_log.id),
                "target_stage_id": str(payload.target_stage_id) if payload.target_stage_id else None,
                "target_status": payload.target_status,
                "target_owner_id": str(payload.target_owner_id) if payload.target_owner_id else None,
                "add_tags": payload.add_tags,
                "remove_tags": payload.remove_tags,
                "archive": payload.archive
            }
        )

    db.commit()
    return {"status": "success", "updated_count": len(apps), "operation_id": op_log.id}


@router.post("/bulk-undo")
def bulk_undo_operation(
    current_user: RequireRecruiter,
    db: TenantDb,
    operation_id: uuid.UUID | None = None,
):
    """
    Rolls back the last bulk operation executed within a 5-minute window.
    """
    from models.ats_models import BulkOperationLog
    from core.timeline import log_application_event
    from models.ats_models import CandidateTag

    if operation_id:
        op_log = db.scalar(
            select(BulkOperationLog).where(
                BulkOperationLog.id == operation_id,
                BulkOperationLog.company_id == current_user.company_id
            )
        )
    else:
        op_log = db.scalar(
            select(BulkOperationLog)
            .where(
                BulkOperationLog.company_id == current_user.company_id,
                BulkOperationLog.recruiter_id == current_user.id
            )
            .order_by(BulkOperationLog.executed_at.desc())
            .limit(1)
        )

    if not op_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No bulk operation log found to undo.")

    now = datetime.now(timezone.utc)
    delta = (now - op_log.executed_at.replace(tzinfo=timezone.utc)).total_seconds()
    if delta > 300:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot undo bulk operation: operation was executed {int(delta)} seconds ago, which is outside the 5-minute (300 seconds) window."
        )

    reverted_count = 0
    for app_id_str, prev_state in op_log.previous_states.items():
        app_id = uuid.UUID(app_id_str)
        app = db.scalar(
            select(Application)
            .options(selectinload(Application.candidate))
            .where(
                Application.id == app_id,
                Application.company_id == current_user.company_id
            )
        )
        if app:
            app.current_stage_id = uuid.UUID(prev_state["current_stage_id"]) if prev_state["current_stage_id"] else None
            app.status = _parse_application_status(prev_state["status"]) if prev_state["status"] else None
            app.owner_id = uuid.UUID(prev_state["owner_id"]) if prev_state["owner_id"] else None
            
            if "is_archived" in prev_state:
                app.is_archived = prev_state["is_archived"]
                app.archived_at = datetime.fromisoformat(prev_state["archived_at"]) if prev_state["archived_at"] else None
                app.archived_by = uuid.UUID(prev_state["archived_by"]) if prev_state["archived_by"] else None
                
            if "tag_ids" in prev_state and app.candidate:
                tags = db.scalars(
                    select(CandidateTag).where(
                        CandidateTag.id.in_([uuid.UUID(tid) for tid in prev_state["tag_ids"]]),
                        CandidateTag.company_id == current_user.company_id
                    )
                ).all()
                app.candidate.tags = list(tags)

            reverted_count += 1

            log_application_event(
                db=db,
                application_id=app.id,
                event_type="application.bulk_undone",
                actor_id=current_user.id,
                actor_name=current_user.full_name,
                metadata={"bulk_operation_id": str(op_log.id)}
            )

    db.delete(op_log)
    db.commit()

    return {"status": "success", "reverted_count": reverted_count}


# --- Phase B.3A ATS Endpoints ---
from schemas.application import ApplicationEventResponse
from pydantic import BaseModel

class MoveStageBody(BaseModel):
    target_stage_id: uuid.UUID
    client_updated_at: datetime | None = None

class AssignBody(BaseModel):
    owner_id: uuid.UUID | None = None
    client_updated_at: datetime | None = None

@router.post("/{application_id}/move-stage", response_model=ApplicationResponse)
def move_application_stage(
    application_id: uuid.UUID,
    body: MoveStageBody,
    current_user: CurrentUser,
    db: TenantDb
):
    """
    Moves an application to a different hiring stage.
    """
    from datetime import datetime, timezone, timedelta
    from models.enums import UserRole
    from core.workflows import transition_candidate_stage

    application = db.scalar(
        select(Application)
        .options(selectinload(Application.candidate), selectinload(Application.job))
        .where(Application.id == application_id)
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # 1. Optimistic Concurrency Check
    if body.client_updated_at is not None:
        db_updated = application.updated_at
        client_updated = body.client_updated_at
        if db_updated and client_updated:
            db_u_naive = db_updated.astimezone(timezone.utc).replace(tzinfo=None) if db_updated.tzinfo else db_updated
            cl_u_naive = client_updated.astimezone(timezone.utc).replace(tzinfo=None) if client_updated.tzinfo else client_updated
            if db_u_naive > cl_u_naive + timedelta(milliseconds=1):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Application has been modified by another user. Please reload and try again."
                )

    # 2. Ownership Restriction Check
    if application.owner_id is not None:
        if current_user.id != application.owner_id and current_user.role != UserRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only the application owner or a Company Owner can edit this application."
            )

    try:
        transition_candidate_stage(
            db=db,
            company_id=current_user.company_id,
            application_id=application.id,
            target_stage_id=body.target_stage_id,
            actor_id=current_user.id
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    return _application_response(application)


@router.post("/{application_id}/assign", response_model=ApplicationResponse)
def assign_application_owner(
    application_id: uuid.UUID,
    body: AssignBody,
    current_user: CurrentUser,
    db: TenantDb
):
    """
    Assigns or updates the primary owner of an application.
    """
    from datetime import datetime, timezone, timedelta
    from models.enums import UserRole
    from core.application_events import ApplicationEventService

    application = db.scalar(
        select(Application)
        .options(selectinload(Application.candidate), selectinload(Application.job))
        .where(Application.id == application_id)
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # 1. Optimistic Concurrency Check
    if body.client_updated_at is not None:
        db_updated = application.updated_at
        client_updated = body.client_updated_at
        if db_updated and client_updated:
            db_u_naive = db_updated.astimezone(timezone.utc).replace(tzinfo=None) if db_updated.tzinfo else db_updated
            cl_u_naive = client_updated.astimezone(timezone.utc).replace(tzinfo=None) if client_updated.tzinfo else client_updated
            if db_u_naive > cl_u_naive + timedelta(milliseconds=1):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Application has been modified by another user. Please reload and try again."
                )

    # 2. Ownership Restriction Check
    if application.owner_id is not None:
        if current_user.id != application.owner_id and current_user.role != UserRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only the application owner or a Company Owner can edit this application."
            )

    if body.owner_id is not None:
        target_user = db.scalar(select(User).where(User.id == body.owner_id, User.company_id == current_user.company_id))
        if not target_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned owner must belong to the same company.")

    with db.begin_nested():
        old_owner_id = str(application.owner_id) if application.owner_id else None
        new_owner_id = str(body.owner_id) if body.owner_id else None
        if old_owner_id != new_owner_id:
            application.owner_id = body.owner_id
            db.flush()
            # Log timeline event
            ApplicationEventService.record_event(
                db=db,
                company_id=current_user.company_id,
                application_id=application.id,
                event_type="application.owner_assigned",
                actor_id=current_user.id,
                previous_value=old_owner_id,
                new_value=new_owner_id,
                metadata={
                    "previous_owner": old_owner_id,
                    "new_owner": new_owner_id
                }
            )

    db.commit()
    db.refresh(application)
    return _application_response(application)


@router.get("/{application_id}/timeline", response_model=list[ApplicationEventResponse])
def get_application_timeline(
    application_id: uuid.UUID,
    db: TenantDb,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    """
    Returns the paginated chronological timeline history of events for a candidate's application.
    """
    from models.ats_models import ApplicationEvent

    # Verify candidate belongs to the company
    app = db.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.company_id == current_user.company_id
        )
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    offset = (page - 1) * page_size
    stmt = (
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application_id)
        .order_by(ApplicationEvent.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    return list(db.scalars(stmt).all())





