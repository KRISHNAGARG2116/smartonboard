import uuid

from fastapi import APIRouter, HTTPException, Query, status
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
def create_job(body: JobCreateRequest, current_user: RequireRecruiter, db: TenantDb):
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
    return job


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid.UUID, db: TenantDb):
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(job_id: uuid.UUID, body: JobUpdateRequest, current_user: RequireRecruiter, db: TenantDb):
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if body.title is not None:
        job.title = body.title
    if body.department is not None:
        job.department = body.department
    if body.description is not None:
        job.description = body.description
    if body.status is not None:
        job.status = _parse_job_status(body.status)
    if body.start_date is not None:
        job.start_date = body.start_date

    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: uuid.UUID, current_user: RequireRecruiter, db: TenantDb):
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    job.status = JobStatus.CLOSED
    db.commit()
