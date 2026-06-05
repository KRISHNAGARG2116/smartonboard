from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from api.deps import CurrentCandidate, get_db
from db.session import tenant_context
from models import Job, CandidateProfile
from models.enums import JobStatus
from core.candidate_matching import calculate_candidate_job_match

router = APIRouter(prefix="/jobs", tags=["Candidate Jobs"])


@router.get("/feed")
def get_jobs_feed(
    current_candidate: CurrentCandidate,
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100)
):
    """Retrieve all open jobs with personalized applicability matching.
    
    Includes pagination. Matches using candidate active profile skills.
    """
    # 1. Fetch current candidate's active profile skills
    with tenant_context(auth_mode="true"):
        profile = db.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == current_candidate.id)
        )
    candidate_skills = profile.skills if profile else []

    # 2. Query open jobs
    offset = (page - 1) * limit
    stmt = select(Job).where(Job.status == JobStatus.OPEN).order_by(Job.created_at.desc())
    
    # Run under tenant_context with auth_mode to bypass company RLS for candidate listing
    with tenant_context(auth_mode="true"):
        total = db.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.OPEN))
        jobs = db.scalars(stmt.offset(offset).limit(limit)).all()
        
        # Build results with dynamic matching
        results = []
        for job in jobs:
            match = calculate_candidate_job_match(
                candidate_skills=candidate_skills,
                job_title=job.title,
                job_description=job.description,
                job_settings=job.settings
            )
            results.append({
                "id": str(job.id),
                "company_id": str(job.company_id),
                "company_name": job.company.name if job.company else "Unknown Company",
                "title": job.title,
                "department": job.department,
                "description": job.description,
                "status": job.status.value,
                "start_date": job.start_date.isoformat() if job.start_date else None,
                "applicability_score": match["applicability_score"],
                "matching_skills": match["matching_skills"],
                "missing_skills": match["missing_skills"]
            })

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "results": results
    }
