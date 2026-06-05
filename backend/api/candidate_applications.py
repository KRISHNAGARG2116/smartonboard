from typing import Annotated
import uuid
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import CurrentCandidate, get_db
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
    current_candidate: CurrentCandidate,
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
