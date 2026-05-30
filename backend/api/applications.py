import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.deps import CurrentUser, TenantDb
from models import Application, Candidate, Job
from models.enums import ApplicationStatus
from schemas.application import (
    ApplicationCreateRequest,
    ApplicationResponse,
    ApplicationUpdateRequest,
    CandidateBrief,
    JobBrief,
)

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
def create_application(body: ApplicationCreateRequest, current_user: CurrentUser, db: TenantDb):
    job = db.scalar(select(Job).where(Job.id == body.job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    candidate = db.scalar(
        select(Candidate).where(
            Candidate.company_id == current_user.company_id,
            Candidate.email == body.candidate_email.lower(),
        )
    )
    if candidate is None:
        candidate = Candidate(
            company_id=current_user.company_id,
            email=body.candidate_email.lower(),
            full_name=body.candidate_name,
            phone=body.candidate_phone,
        )
        db.add(candidate)
        db.flush()
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
def update_application(application_id: uuid.UUID, body: ApplicationUpdateRequest, db: TenantDb):
    application = db.scalar(
        select(Application)
        .options(selectinload(Application.candidate), selectinload(Application.job))
        .where(Application.id == application_id)
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if body.status is not None:
        application.status = _parse_application_status(body.status)
    db.commit()
    db.refresh(application)
    return _application_response(application)
