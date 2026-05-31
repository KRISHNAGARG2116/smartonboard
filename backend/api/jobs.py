import uuid

from fastapi import APIRouter, HTTPException, Query, status, Request
from sqlalchemy import select

from api.deps import CurrentUser, TenantDb, RequireRecruiter
from models import Job, Candidate, CandidateEmbedding
from models.enums import JobStatus
from schemas.job import JobCreateRequest, JobResponse, JobUpdateRequest
from core.embeddings import EmbeddingService
from core.audit import log_audit_event


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


@router.post("/{job_id}/candidate-matches")
def get_candidate_matches(
    job_id: uuid.UUID,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb
):
    """
    Ranks the candidate pool semantically against job description criteria.
    Candidate ranking is calculated utilizing the average similarity score
    of the top N=3 chunks. Enforces multi-tenant vector RLS boundary.
    """
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.company_id == current_user.company_id
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    embedder = EmbeddingService()
    query_vector = embedder.generate_embedding(job.description or job.title)

    # Query all candidate embeddings joining candidates (RLS filtered)
    stmt = (
        select(CandidateEmbedding, Candidate.full_name)
        .join(Candidate, Candidate.id == CandidateEmbedding.candidate_id)
        .where(CandidateEmbedding.company_id == current_user.company_id)
    )
    embeddings_list = db.execute(stmt).all()

    # Group embeddings by candidate
    candidate_chunks = {}
    for emb, full_name in embeddings_list:
        score = embedder.compute_similarity(query_vector, emb.resume_embedding)
        cand_id = emb.candidate_id
        if cand_id not in candidate_chunks:
            candidate_chunks[cand_id] = {
                "full_name": full_name,
                "scores": [],
                "best_chunk": "",
                "best_score": -1.0,
                "best_chunk_idx": 0
            }
        candidate_chunks[cand_id]["scores"].append(score)
        if score > candidate_chunks[cand_id]["best_score"]:
            candidate_chunks[cand_id]["best_score"] = score
            candidate_chunks[cand_id]["best_chunk"] = emb.chunk_text
            candidate_chunks[cand_id]["best_chunk_idx"] = emb.chunk_index

    # Calculate average of the top N=3 chunks for ranking
    matches = []
    for cand_id, info in candidate_chunks.items():
        sorted_scores = sorted(info["scores"], reverse=True)
        top_n = sorted_scores[:3]
        avg_score = sum(top_n) / len(top_n) if top_n else 0.0

        matches.append({
            "candidate_id": str(cand_id),
            "full_name": info["full_name"],
            "similarity_score": round(avg_score, 4),
            "matched_chunk": info["best_chunk"],
            "chunk_index": info["best_chunk_idx"]
        })

    # Sort matches by average similarity score in descending order
    matches.sort(key=lambda x: x["similarity_score"], reverse=True)

    # Log ai.discovery_searched audit event
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="ai.discovery_searched",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="jobs",
        resource_id=str(job_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "job_id": str(job_id),
            "company_id": str(current_user.company_id),
            "candidate_match_count": len(matches)
        }
    )

    return matches

