from typing import Annotated
import uuid
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import CurrentCandidate, get_db, VerifiedCandidate
from db.session import tenant_context
from models import Job, Candidate, Application, CandidateProfile, ApplicationSnapshot
from models.enums import JobStatus, ApplicationStatus
from models.candidate_resume import CandidateResume

router = APIRouter(prefix="/applications", tags=["Candidate Applications"])


class ApplyRequest(BaseModel):
    job_id: uuid.UUID
    resume_id: uuid.UUID


@router.post("/apply")
def apply_to_job(
    current_candidate: VerifiedCandidate,
    body: ApplyRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Submits a candidate's application to a job.
    
    Verifies resume ownership, checks for duplicates, creates recruiter-facing
    Candidate records if needed, and stores an immutable ApplicationSnapshot.
    """
    with tenant_context(auth_mode="true"):
        # 1. Fetch and validate job
        job = db.scalar(select(Job).where(Job.id == body.job_id))
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        if job.status != JobStatus.OPEN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job is not open for applications")

        # 2. Fetch and validate resume ownership
        resume = db.scalar(
            select(CandidateResume).where(
                CandidateResume.id == body.resume_id,
                CandidateResume.user_id == current_candidate.id
            )
        )
        if not resume:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resume selected")

        # 3. Fetch candidate profile
        profile = db.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == current_candidate.id)
        )

        # 4. Check if Candidate record already exists in the company scope
        candidate = db.scalar(
            select(Candidate).where(
                Candidate.company_id == job.company_id,
                Candidate.email == current_candidate.email
            )
        )

        # 5. Check duplicate application
        if candidate:
            existing = db.scalar(
                select(Application).where(
                    Application.job_id == job.id,
                    Application.candidate_id == candidate.id
                )
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="You have already applied to this job"
                )

        # 6. Create Candidate record if missing in target company scope
        if not candidate:
            candidate = Candidate(
                company_id=job.company_id,
                email=current_candidate.email,
                full_name=profile.full_name if profile else current_candidate.full_name,
                phone=profile.phone_number if profile else None
            )
            db.add(candidate)
            db.flush()

        # 7. Create Application
        application = Application(
            company_id=job.company_id,
            job_id=job.id,
            candidate_id=candidate.id,
            status=ApplicationStatus.SUBMITTED,
            source="candidate_portal"
        )
        db.add(application)
        db.flush()

        # 8. Create Immutable Snapshot
        resume_snapshot = {
            "id": str(resume.id),
            "filename": resume.filename,
            "file_path": resume.file_path,
            "parsed_skills": resume.parsed_skills or [],
            "parsed_summary": resume.parsed_summary or "",
            "created_at": resume.created_at.isoformat()
        }
        
        candidate_snapshot = {
            "full_name": profile.full_name if profile else current_candidate.full_name,
            "email": current_candidate.email,
            "phone_number": profile.phone_number if profile else None,
            "location": profile.location if profile else None,
            "skills": profile.skills if profile else [],
            "summary": profile.summary if profile else ""
        }
        
        snapshot = ApplicationSnapshot(
            application_id=application.id,
            resume_snapshot=resume_snapshot,
            candidate_snapshot=candidate_snapshot
        )
        db.add(snapshot)
        db.commit()

    return {
        "success": True,
        "application_id": str(application.id),
        "status": application.status.value
    }


@router.get("/me")
def get_my_applications(
    current_candidate: CurrentCandidate,
    db: Annotated[Session, Depends(get_db)]
):
    """Retrieve all applications submitted by the currently logged-in candidate.
    
    Includes snapshot data (resume details and profile fields), excluding risk
    scores, internal notes, and committee reviews.
    """
    from sqlalchemy.orm import selectinload
    
    with tenant_context(auth_mode="true"):
        # Query all candidate records matching current candidate's email address
        candidates = db.scalars(
            select(Candidate).where(Candidate.email == current_candidate.email.lower())
        ).all()
        candidate_ids = [c.id for c in candidates]
        
        if not candidate_ids:
            return []
            
        stmt = (
            select(Application)
            .options(
                selectinload(Application.job),
                selectinload(Application.company),
                selectinload(Application.snapshot)
            )
            .where(Application.candidate_id.in_(candidate_ids))
            .order_by(Application.created_at.desc())
        )
        applications = db.scalars(stmt).all()
        
        results = []
        for app in applications:
            snapshot_data = None
            if app.snapshot:
                # Exclude risk scores, notes, and committee review details
                snapshot_data = {
                    "id": str(app.snapshot.id),
                    "resume_snapshot": app.snapshot.resume_snapshot,
                    "candidate_snapshot": app.snapshot.candidate_snapshot,
                    "created_at": app.snapshot.generated_at.isoformat()
                }
                
            results.append({
                "id": str(app.id),
                "company_id": str(app.company_id),
                "company_name": app.company.name if app.company else "Unknown Company",
                "job_id": str(app.job_id),
                "job_title": app.job.title if app.job else "Unknown Job",
                "job_department": app.job.department if app.job else "",
                "status": app.status.value,
                "created_at": app.created_at.isoformat(),
                "updated_at": app.updated_at.isoformat(),
                "snapshot": snapshot_data
            })
            
        return results


@router.post("/{application_id}/withdraw")
def withdraw_application(
    application_id: uuid.UUID,
    current_candidate: CurrentCandidate,
    db: Annotated[Session, Depends(get_db)]
):
    """Withdraw an application and generate recruiter notification drafts."""
    from sqlalchemy.orm import selectinload
    from models import User
    from models.enums import UserRole
    
    with tenant_context(auth_mode="true"):
        app = db.scalar(
            select(Application)
            .options(selectinload(Application.candidate), selectinload(Application.job))
            .where(Application.id == application_id)
        )
        if not app or not app.candidate or app.candidate.email != current_candidate.email.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
            
        if app.status == ApplicationStatus.WITHDRAWN:
            return {"success": True, "message": "Application is already withdrawn"}
            
        old_status = app.status
        app.status = ApplicationStatus.WITHDRAWN
        db.add(app)
        db.commit()
        db.refresh(app)
        
        # Write audit event
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="application.withdrawn",
            actor_type="CANDIDATE",
            actor_id=current_candidate.id,
            company_id=app.company_id,
            resource_type="applications",
            resource_id=str(app.id),
            metadata={
                "application_id": str(app.id),
                "old_status": old_status.value,
                "new_status": "withdrawn"
            }
        )
        
        # Log activity feed event
        log_audit_event(
            db=db,
            action="candidate.stage_changed",
            actor_type="CANDIDATE",
            actor_id=current_candidate.id,
            company_id=app.company_id,
            resource_type="candidates",
            resource_id=str(app.candidate_id),
            metadata={
                "application_id": str(app.id),
                "old_status": old_status.value,
                "new_status": "withdrawn"
            }
        )
        
        # Create recruiter notification email draft
        recipient_email = "recruiter@smartonboard.com"
        company_user = db.scalar(
            select(User).where(User.company_id == app.company_id, User.role == UserRole.OWNER)
        )
        if company_user:
            recipient_email = company_user.email
            
        candidate_name = app.candidate.full_name
        job_title = app.job.title if app.job else "Job Role"
        
        draft_subject = f"Application Withdrawn: {candidate_name} - {job_title}"
        draft_body = (
            f"Hello Recruitment Team,\n\n"
            f"The candidate {candidate_name} has withdrawn their application for the position of '{job_title}'.\n\n"
            f"Application Status updated to: WITHDRAWN\n\n"
            f"Best regards,\n"
            f"SmartOnboard System"
        )
        
        return {
            "success": True,
            "message": "Application withdrawn successfully",
            "notification_draft": {
                "recipient_email": recipient_email,
                "subject": draft_subject,
                "body": draft_body
            }
        }

