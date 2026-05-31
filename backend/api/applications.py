import uuid

from fastapi import APIRouter, HTTPException, Query, status, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.deps import CurrentUser, TenantDb, RequireRecruiter
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

