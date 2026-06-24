from typing import Annotated
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from api.deps import CurrentCandidate, get_db, VerifiedCandidate
from db.session import tenant_context
from models.candidate_resume import CandidateResume
from models.candidate_profile import CandidateProfile
from models.quarantine import QuarantinedFile
from core.signature import validate_file_signature
from core.storage import LocalStorageService
from core.malware import EICAR_SIGNATURE
from core.audit import log_audit_event

router = APIRouter(prefix="/auth", tags=["Candidate Resumes"])


@router.post("/candidate/resumes/upload", status_code=status.HTTP_202_ACCEPTED)
def candidate_upload_resume(
    request: Request,
    current_candidate: VerifiedCandidate,
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
):
    """Asynchronously uploads a candidate's resume, scans it for malware,
    promotes it to candidate storage, and parses profile information.
    """
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    # 1. Enforce max 3 resumes
    with tenant_context(auth_mode="true"):
        resume_count = db.scalar(
            select(func.count(CandidateResume.id)).where(CandidateResume.user_id == current_candidate.id)
        )
        if resume_count >= 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum limit of 3 resumes reached. Please delete an existing resume to upload a new one."
            )

    # 2. File size validation
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 5 MB.")

    file_bytes = file.file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 5 MB.")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # 3. Malware / EICAR pre-flight validation
    if EICAR_SIGNATURE in file_bytes:
        log_audit_event(
            db=db,
            action="file.scan_failure",
            actor_type="CANDIDATE",
            actor_id=current_candidate.id,
            resource_type="quarantine",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"filename": file.filename, "error": "Malware detected: EICAR test signature found.", "event": "malware_detected"}
        )
        raise HTTPException(status_code=400, detail="Malware detected: EICAR test signature found.")

    # 4. File signature validation
    try:
        validate_file_signature(file_bytes, file.filename or "")
    except ValueError as sig_err:
        log_audit_event(
            db=db,
            action="file.signature_failure",
            actor_type="CANDIDATE",
            actor_id=current_candidate.id,
            resource_type="quarantine",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"filename": file.filename, "error": str(sig_err), "event": "invalid_signature"}
        )
        raise HTTPException(status_code=400, detail=str(sig_err))

    # 5. Quarantine Phase
    STORAGE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"
    storage_service = LocalStorageService(STORAGE_BASE_DIR)
    quarantine_path = storage_service.save_quarantine(file_bytes, file.filename or "file.dat")

    # 6. Create QuarantinedFile record
    with tenant_context(auth_mode="true"):
        q_rec = QuarantinedFile(
            company_id=None,
            user_id=current_candidate.id,
            filename=file.filename or "file.dat",
            quarantine_path=str(quarantine_path),
            is_safe=None  # Pending
        )
        db.add(q_rec)
        db.flush()
        q_file_id = q_rec.id
        db.commit()

    # 7. Dispatch to Celery scanner task
    from celery_worker import scan_and_promote_resume_task
    task = scan_and_promote_resume_task.delay(
        quarantine_file_id=str(q_file_id)
    )

    return {
        "task_id": task.id,
        "quarantine_file_id": str(q_file_id),
        "status": "PENDING"
    }


@router.get("/candidate/resumes")
def candidate_list_resumes(
    current_candidate: VerifiedCandidate,
    db: Annotated[Session, Depends(get_db)],
):
    """Retrieve all resumes uploaded by the authenticated candidate."""
    with tenant_context(auth_mode="true"):
        resumes = db.scalars(
            select(CandidateResume)
            .where(CandidateResume.user_id == current_candidate.id)
            .order_by(CandidateResume.created_at.desc())
        ).all()
        
    return [
        {
            "id": str(r.id),
            "filename": r.filename,
            "file_path": r.file_path,
            "is_active": r.is_active,
            "parsed_skills": r.parsed_skills or [],
            "parsed_summary": r.parsed_summary or "",
            "created_at": r.created_at.isoformat(),
        }
        for r in resumes
    ]


@router.post("/candidate/resumes/{resume_id}/toggle-active")
def candidate_toggle_resume_active(
    resume_id: uuid.UUID,
    current_candidate: VerifiedCandidate,
    db: Annotated[Session, Depends(get_db)],
):
    """Set specified resume as the active one and update the profile data (provenance sync)."""
    with tenant_context(auth_mode="true"):
        # 1. Fetch resume and verify ownership
        resume = db.scalar(
            select(CandidateResume).where(
                CandidateResume.id == resume_id,
                CandidateResume.user_id == current_candidate.id
            )
        )
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        # 2. Set all candidate's resumes to inactive
        db.execute(
            update(CandidateResume)
            .where(CandidateResume.user_id == current_candidate.id)
            .values(is_active=False)
        )
        db.flush()

        # 3. Activate target resume
        resume.is_active = True
        db.add(resume)
        db.flush()

        # 4. Synchronize profile values
        profile = db.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == current_candidate.id)
        )
        if profile:
            profile.skills = resume.parsed_skills or []
            profile.summary = resume.parsed_summary or ""
            db.add(profile)
            
        db.commit()

    return {"success": True, "message": "Active resume updated successfully"}


@router.delete("/candidate/resumes/{resume_id}")
def candidate_delete_resume(
    resume_id: uuid.UUID,
    current_candidate: VerifiedCandidate,
    db: Annotated[Session, Depends(get_db)],
):
    """Delete a resume from library database and disk storage."""
    with tenant_context(auth_mode="true"):
        # 1. Fetch and verify ownership
        resume = db.scalar(
            select(CandidateResume).where(
                CandidateResume.id == resume_id,
                CandidateResume.user_id == current_candidate.id
            )
        )
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        was_active = resume.is_active

        # 2. Delete file from disk storage
        STORAGE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"
        storage_service = LocalStorageService(STORAGE_BASE_DIR)
        try:
            storage_service.delete_file(STORAGE_BASE_DIR / resume.file_path)
        except Exception:
            pass

        # 3. Delete from DB
        db.delete(resume)
        db.flush()

        # 4. If the deleted resume was active, promote another one if available
        if was_active:
            remaining = db.scalars(
                select(CandidateResume)
                .where(CandidateResume.user_id == current_candidate.id)
                .order_by(CandidateResume.created_at.desc())
            ).first()
            
            profile = db.scalar(
                select(CandidateProfile).where(CandidateProfile.user_id == current_candidate.id)
            )
            
            if remaining and profile:
                remaining.is_active = True
                db.add(remaining)
                profile.skills = remaining.parsed_skills or []
                profile.summary = remaining.parsed_summary or ""
                db.add(profile)
            elif profile:
                profile.skills = []
                profile.summary = ""
                db.add(profile)

        db.commit()

    return {"success": True, "message": "Resume deleted successfully"}
