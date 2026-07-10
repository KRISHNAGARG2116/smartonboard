import uuid
import time
from datetime import datetime, timezone
from typing import Annotated, List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete, update
from sqlalchemy.orm import Session

from api.deps import TenantDb, RequirePermission
from models.rbac import UserPermission
from models import (
    Candidate,
    User,
    Job,
    Application,
    CandidateProfile
)
from models.crm_models import (
    CachedMatchScore,
    MatchScoreHistory,
    MatchFeedback
)
from core.intelligence import GenerativeIntelligenceService

router = APIRouter(prefix="/match", tags=["match-intelligence"])


# --- PYDANTIC SCHEMAS ---

class MatchFeedbackPayload(BaseModel):
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    rating: str = Field(..., description="'helpful' or 'not_helpful'")
    feedback_reason: Optional[str] = Field(None, description="'Very Accurate', 'Mostly Accurate', 'Missed Skills', 'Wrong Experience', 'Wrong Industry', 'Other'")


# --- CACHED MATCH COMPUTE ENGINE ---

def get_or_compute_match(db: Session, candidate_id: uuid.UUID, job_id: uuid.UUID, company_id: uuid.UUID) -> CachedMatchScore:
    # 1. Fetch Candidate, profile, and Job
    candidate = db.scalar(
        select(Candidate).where(Candidate.id == candidate_id, Candidate.company_id == company_id)
    )
    job = db.scalar(
        select(Job).where(Job.id == job_id, Job.company_id == company_id)
    )
    if not candidate or not job:
        raise HTTPException(status_code=404, detail="Candidate or Job not found")

    user = db.scalar(select(User).where(User.email == candidate.email))
    profile = None
    if user:
        profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))

    resume_version = profile.resume_version if profile else 1
    job_version = job.job_version

    # 2. Check Cache
    cache = db.scalar(
        select(CachedMatchScore).where(
            CachedMatchScore.candidate_id == candidate_id,
            CachedMatchScore.job_id == job_id,
            CachedMatchScore.resume_version == resume_version,
            CachedMatchScore.job_version == job_version
        )
    )
    if cache:
        return cache

    # 3. Cache Miss: Compute match score
    start_time = time.time()
    
    cand_profile_dict = {
        "skills": profile.skills if profile else [],
        "location": profile.location if profile else "",
        "experience_years": 4.5  # Simulated experience years parse
    }
    
    job_req_dict = {
        "required_skills": job.settings.get("required_skills", []) if job.settings else [],
        "location": job.settings.get("location", "") if job.settings else "",
        "required_experience_years": job.settings.get("required_experience_years", 0) if job.settings else 0
    }

    # Deterministic fit calculations
    score_data = GenerativeIntelligenceService.calculate_deterministic_match_score(cand_profile_dict, job_req_dict)
    overall_score = score_data["overall_score"]
    breakdown = score_data["breakdown"]

    # Deterministic confidence calculations
    confidence, confidence_explanation = GenerativeIntelligenceService.calculate_deterministic_confidence(overall_score, 0.90)

    # Summaries (LLM explainability)
    cand_summary = GenerativeIntelligenceService.generate_candidate_match_summary(cand_profile_dict, job_req_dict, overall_score)
    recruiter_analysis = GenerativeIntelligenceService.generate_recruiter_match_analysis(cand_profile_dict, job_req_dict, overall_score)

    comp_duration = int((time.time() - start_time) * 1000)

    # 4. Save Cache
    if cache:
        # Update existing
        cache.resume_version = resume_version
        cache.job_version = job_version
        cache.overall_score = overall_score
        cache.confidence = confidence
        cache.confidence_explanation = confidence_explanation
        cache.breakdown = breakdown
        cache.explanation = {"candidate": cand_summary, "recruiter": recruiter_analysis}
        cache.last_computed_at = datetime.now(timezone.utc)
        cache.computation_duration_ms = comp_duration
    else:
        # Create new
        cache = CachedMatchScore(
            candidate_id=candidate_id,
            job_id=job_id,
            resume_version=resume_version,
            job_version=job_version,
            overall_score=overall_score,
            confidence=confidence,
            confidence_explanation=confidence_explanation,
            breakdown=breakdown,
            explanation={"candidate": cand_summary, "recruiter": recruiter_analysis},
            generated_by_model=GenerativeIntelligenceService.MODEL_VERSION,
            last_computed_at=datetime.now(timezone.utc),
            computation_duration_ms=comp_duration
        )
        db.add(cache)

    # 5. Log History record
    history = MatchScoreHistory(
        candidate_id=candidate_id,
        job_id=job_id,
        score=overall_score,
        confidence=confidence,
        resume_version=resume_version,
        job_version=job_version,
        explanation_version=1,
        generated_by_model=GenerativeIntelligenceService.MODEL_VERSION
    )
    db.add(history)
    db.commit()
    db.refresh(cache)

    return cache


# --- ENDPOINTS ---

@router.get("/candidates/{candidate_id}/job/{job_id}")
def get_candidate_job_match(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.VIEW_TALENT_CRM))],
    db: TenantDb
):
    """Retrieve match score (recalculating if dirty) for recruiters."""
    cache = get_or_compute_match(db, candidate_id, job_id, current_user.company_id)
    return cache


@router.get("/applications/{application_id}/analysis")
def get_application_match_analysis(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.VIEW_TALENT_CRM))],
    db: TenantDb
):
    """Detailed fit analysis and considerations for a specific recruiter scorecard/application review."""
    app = db.scalar(
        select(Application).where(Application.id == application_id, Application.company_id == current_user.company_id)
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    cache = get_or_compute_match(db, app.candidate_id, app.job_id, current_user.company_id)
    return {
        "application_id": str(application_id),
        "overall_score": cache.overall_score,
        "confidence": cache.confidence,
        "confidence_explanation": cache.confidence_explanation,
        "breakdown": cache.breakdown,
        "recruiter_analysis": cache.explanation.get("recruiter", {})
    }


@router.post("/feedback")
def submit_match_feedback(
    body: MatchFeedbackPayload,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_CANDIDATE_RELATIONSHIPS))],
    db: TenantDb
):
    """Logs recruiter feedback regarding AI Match quality."""
    # Check if candidate and job exist
    cand = db.scalar(select(Candidate).where(Candidate.id == body.candidate_id, Candidate.company_id == current_user.company_id))
    job = db.scalar(select(Job).where(Job.id == body.job_id, Job.company_id == current_user.company_id))
    if not cand or not job:
        raise HTTPException(status_code=404, detail="Candidate or Job not found")

    feedback = MatchFeedback(
        company_id=current_user.company_id,
        candidate_id=body.candidate_id,
        job_id=body.job_id,
        recruiter_id=current_user.id,
        rating=body.rating,
        feedback_reason=body.feedback_reason
    )
    db.add(feedback)
    db.commit()
    return {"status": "success", "message": "Feedback submitted successfully"}


@router.post("/jobs/{job_id}/refresh-cache")
def refresh_job_match_cache(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    """Invalidates the caches for all candidates associated with a specific job, queueing recalculations."""
    job = db.scalar(select(Job).where(Job.id == job_id, Job.company_id == current_user.company_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Increment job requirements version
    job.job_version += 1
    db.commit()

    return {"status": "success", "message": f"Match cache invalidated for job {job_id}. Next lookup will force recalculation."}
