import uuid

from fastapi import APIRouter, HTTPException, Query, status, Request
from sqlalchemy import select

from api.deps import CurrentUser, TenantDb, RequireRecruiter
from models import Job
from models.enums import JobStatus
from schemas.job import JobCreateRequest, JobResponse, JobUpdateRequest

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _parse_job_status(value: str) -> JobStatus:
    try:
        return JobStatus(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid job status") from exc


@router.get("", response_model=list[JobResponse])
def list_jobs(db: TenantDb, status_filter: str | None = Query(default=None, alias="status")):
    stmt = select(Job).order_by(Job.created_at.desc())
    if status_filter:
        stmt = stmt.where(Job.status == _parse_job_status(status_filter))
    return list(db.scalars(stmt).all())


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    body: JobCreateRequest,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb
):
    job = Job(
        company_id=current_user.company_id,
        title=body.title,
        department=body.department,
        description=body.description,
        status=_parse_job_status(body.status),
        start_date=body.start_date,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Audit log job creation
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="job.created",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="jobs",
        resource_id=str(job.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "title": job.title,
            "department": job.department,
            "status": job.status.value
        }
    )
    
    return job


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid.UUID, db: TenantDb):
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: uuid.UUID,
    body: JobUpdateRequest,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb
):
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    old_status = job.status
    changes = {}
    if body.title is not None:
        if job.title != body.title:
            changes["title"] = {"old": job.title, "new": body.title}
            job.title = body.title
    if body.department is not None:
        if job.department != body.department:
            changes["department"] = {"old": job.department, "new": body.department}
            job.department = body.department
    if body.description is not None:
        if job.description != body.description:
            changes["description"] = "edited"
            job.description = body.description
    if body.status is not None:
        new_status = _parse_job_status(body.status)
        if old_status != new_status:
            changes["status"] = {"old": old_status.value, "new": new_status.value}
            job.status = new_status
    if body.start_date is not None:
        if job.start_date != body.start_date:
            changes["start_date"] = {"old": str(job.start_date), "new": str(body.start_date)}
            job.start_date = body.start_date

    db.commit()
    db.refresh(job)
    
    # Audit log edit or archival
    if changes:
        from core.audit import log_audit_event
        action = "job.edited"
        if "status" in changes and job.status == JobStatus.CLOSED:
            action = "job.archived"
            
        log_audit_event(
            db=db,
            action=action,
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            resource_type="jobs",
            resource_id=str(job.id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata=changes
        )
        
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: uuid.UUID,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb
):
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
    old_status = job.status
    if old_status != JobStatus.CLOSED:
        job.status = JobStatus.CLOSED
        db.commit()
        
        # Audit log archival
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="job.archived",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            resource_type="jobs",
            resource_id=str(job.id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"status": {"old": old_status.value, "new": "closed"}}
        )
