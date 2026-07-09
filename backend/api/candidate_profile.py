from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from api.deps import RequireCandidate, CandidateDb
from models import CandidateProfile, CandidateProfileRevision
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter(prefix="/candidate/profile", tags=["candidate-profile"])

class UpdateProfileSchema(BaseModel):
    full_name: str
    phone_number: str | None = None
    location: str | None = None
    summary: str | None = None
    experience: list | None = None
    education: list | None = None
    links: dict | None = None
    languages: list | None = None
    availability: str | None = None
    salary_expectations: str | None = None
    work_authorization: str | None = None
    client_updated_at: datetime

class UpdatePreferencesSchema(BaseModel):
    preferences: dict
    client_updated_at: datetime

@router.get("")
def get_profile(
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    profile = db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == current_candidate.id)
    )
    if not profile:
        # Create empty profile if none exists
        profile = CandidateProfile(
            user_id=current_candidate.id,
            full_name=current_candidate.email.split("@")[0],
            phone_verified=False,
            email_verified=True,
            preferences={},
            experience=[],
            education=[],
            links={},
            languages=[]
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return {
        "id": str(profile.id),
        "full_name": profile.full_name,
        "phone_number": profile.phone_number,
        "phone_verified": profile.phone_verified,
        "email_verified": profile.email_verified,
        "location": profile.location,
        "summary": profile.summary,
        "skills": profile.skills or [],
        "preferences": profile.preferences or {},
        "experience": profile.experience or [],
        "education": profile.education or [],
        "links": profile.links or {},
        "languages": profile.languages or [],
        "availability": profile.availability,
        "salary_expectations": profile.salary_expectations,
        "work_authorization": profile.work_authorization,
        "updated_at": profile.updated_at.isoformat()
    }

@router.put("")
def update_profile(
    body: UpdateProfileSchema,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    profile = db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == current_candidate.id)
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Optimistic Concurrency check
    if body.client_updated_at is not None:
        db_updated = profile.updated_at
        client_updated = body.client_updated_at
        if db_updated and client_updated:
            db_u_naive = db_updated.astimezone(timezone.utc).replace(tzinfo=None) if db_updated.tzinfo else db_updated
            cl_u_naive = client_updated.astimezone(timezone.utc).replace(tzinfo=None) if client_updated.tzinfo else client_updated
            if db_u_naive > cl_u_naive + timedelta(milliseconds=1):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Profile has been modified by another process. Please reload and try again."
                )

    # 1. Fetch highest revision version
    highest_version = db.scalar(
        select(func.max(CandidateProfileRevision.version))
        .where(CandidateProfileRevision.profile_id == profile.id)
    ) or 0
    new_version = highest_version + 1

    # 2. Save revision snapshot before updating
    snapshot = {
        "full_name": profile.full_name,
        "phone_number": profile.phone_number,
        "location": profile.location,
        "summary": profile.summary,
        "skills": profile.skills,
        "preferences": profile.preferences,
        "experience": profile.experience,
        "education": profile.education,
        "links": profile.links,
        "languages": profile.languages,
        "availability": profile.availability,
        "salary_expectations": profile.salary_expectations,
        "work_authorization": profile.work_authorization
    }
    revision = CandidateProfileRevision(
        profile_id=profile.id,
        version=new_version,
        changed_by=current_candidate.id,
        snapshot=snapshot
    )
    db.add(revision)

    # 3. Apply profile updates
    profile.full_name = body.full_name
    profile.phone_number = body.phone_number
    profile.location = body.location
    profile.summary = body.summary
    profile.experience = body.experience
    profile.education = body.education
    profile.links = body.links
    profile.languages = body.languages
    profile.availability = body.availability
    profile.salary_expectations = body.salary_expectations
    profile.work_authorization = body.work_authorization

    db.add(profile)
    db.commit()
    return {"status": "success", "version": new_version}

@router.put("/preferences")
def update_preferences(
    body: UpdatePreferencesSchema,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    profile = db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == current_candidate.id)
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Optimistic Concurrency check
    if body.client_updated_at is not None:
        db_updated = profile.updated_at
        client_updated = body.client_updated_at
        if db_updated and client_updated:
            db_u_naive = db_updated.astimezone(timezone.utc).replace(tzinfo=None) if db_updated.tzinfo else db_updated
            cl_u_naive = client_updated.astimezone(timezone.utc).replace(tzinfo=None) if client_updated.tzinfo else client_updated
            if db_u_naive > cl_u_naive + timedelta(milliseconds=1):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Profile preferences have been modified by another process. Please reload and try again."
                )

    # 1. Fetch highest revision version
    highest_version = db.scalar(
        select(func.max(CandidateProfileRevision.version))
        .where(CandidateProfileRevision.profile_id == profile.id)
    ) or 0
    new_version = highest_version + 1

    # 2. Save revision snapshot before updating
    snapshot = {
        "full_name": profile.full_name,
        "phone_number": profile.phone_number,
        "location": profile.location,
        "summary": profile.summary,
        "skills": profile.skills,
        "preferences": profile.preferences,
        "experience": profile.experience,
        "education": profile.education,
        "links": profile.links,
        "languages": profile.languages,
        "availability": profile.availability,
        "salary_expectations": profile.salary_expectations,
        "work_authorization": profile.work_authorization
    }
    revision = CandidateProfileRevision(
        profile_id=profile.id,
        version=new_version,
        changed_by=current_candidate.id,
        snapshot=snapshot
    )
    db.add(revision)

    # 3. Apply profile updates
    profile.preferences = body.preferences
    db.add(profile)
    db.commit()
    return {"status": "success", "version": new_version}

