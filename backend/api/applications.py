import uuid

from fastapi import APIRouter, HTTPException, Query, status, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.deps import CurrentUser, TenantDb, RequireRecruiter
from models import Application, Candidate, Job, CandidateEmbedding
from models.enums import ApplicationStatus
from schemas.application import (
    ApplicationCreateRequest,
    ApplicationResponse,
    ApplicationUpdateRequest,
    CandidateBrief,
    JobBrief,
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
        candidate=CandidateBrief.model_validate(application.candidate) if application.candidate else None,
        job=JobBrief.model_validate(application.job) if application.job else None,
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
    application = db.scalar(
        select(Application)
        .options(selectinload(Application.candidate), selectinload(Application.job))
        .where(Application.id == application_id)
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        
    old_status = application.status
    if body.status is not None:
        new_status = _parse_application_status(body.status)
        if old_status != new_status:
            application.status = new_status
            db.commit()
            db.refresh(application)
            
            # Dispatch background tracking tasks
            track_stage_transition_async.delay(
                str(current_user.company_id),
                str(application.id),
                old_status.value,
                new_status.value,
                str(current_user.id)
            )
            
            if old_status == ApplicationStatus.SUBMITTED:
                track_recruiter_productivity_async.delay(
                    str(current_user.company_id),
                    str(current_user.id),
                    "review"
                )
            
            order = [
                ApplicationStatus.SUBMITTED,
                ApplicationStatus.SCREENING,
                ApplicationStatus.INTERVIEW,
                ApplicationStatus.OFFER,
                ApplicationStatus.HIRED
            ]
            if old_status in order and new_status in order:
                if order.index(new_status) > order.index(old_status):
                    track_recruiter_productivity_async.delay(
                        str(current_user.company_id),
                        str(current_user.id),
                        "advance"
                    )
            
            # Log audit events for status updates
            from core.audit import log_audit_event
            
            # 1. Log recruiter override
            log_audit_event(
                db=db,
                action="ai.recruiter_override",
                actor_type="RECRUITER",
                actor_id=current_user.id,
                company_id=current_user.company_id,
                resource_type="applications",
                resource_id=str(application.id),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={
                    "application_id": str(application.id),
                    "candidate_id": str(application.candidate_id),
                    "old_status": old_status.value,
                    "new_status": new_status.value
                }
            )
            
            # 2. Log corresponding lifecycle state event
            action_lifecycle = "candidate.stage_changed"
            if new_status == ApplicationStatus.HIRED:
                action_lifecycle = "candidate.hired"
            elif new_status == ApplicationStatus.REJECTED:
                action_lifecycle = "candidate.rejected"
                
            log_audit_event(
                db=db,
                action=action_lifecycle,
                actor_type="RECRUITER",
                actor_id=current_user.id,
                company_id=current_user.company_id,
                resource_type="candidates",
                resource_id=str(application.candidate_id),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={
                    "application_id": str(application.id),
                    "old_status": old_status.value,
                    "new_status": new_status.value
                }
            )
            
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

    # 2. Synchronous Antivirus & Signature Validation (Quarantine Phase)
    quarantine_path = storage_service.save_quarantine(pdf_bytes, file.filename or "file.dat")
    try:
        # Malware Dynamic & Static Scan
        try:
            scan_file_for_malware(pdf_bytes)
        except ValueError as val_err:
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
                metadata={"filename": file.filename, "error": str(val_err), "event": "malware_detected"}
            )
            raise HTTPException(status_code=400, detail=str(val_err))
        except RuntimeError as run_err:
            raise HTTPException(status_code=500, detail="Security scanning service failure")

        # File Signature Verification
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

        # 3. Promotion Phase
        permanent_path = storage_service.promote_file(quarantine_path, str(current_user.company_id))
        
        # Log promotion compliance audit
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="file.promoted",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            resource_type="uploads",
            resource_id=permanent_path.name,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"filename": file.filename, "size": len(pdf_bytes)}
        )

    except HTTPException:
        raise
    except Exception as exc:
        storage_service.delete_file(quarantine_path)
        raise HTTPException(status_code=500, detail="Secure file handling failure") from exc

    # 4. Job Validation
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.company_id == current_user.company_id
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # 5. Dispatch task to Celery worker queue
    evaluation_id = str(uuid.uuid4())
    relative_path = f"uploads/{current_user.company_id}/{permanent_path.name}"
    
    task = process_resume_async.delay(
        relative_path,
        str(current_user.company_id),
        str(job_id),
        evaluation_id
    )

    return {
        "task_id": task.id,
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



