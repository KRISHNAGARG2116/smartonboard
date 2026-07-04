import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status, Request, Header
from sqlalchemy import select

from api.deps import CurrentUser, TenantDb, RequireRecruiter
from models import Job, Candidate, CandidateEmbedding
from models.enums import JobStatus
from schemas.job import (
    JobCreateRequest, JobResponse, JobUpdateRequest,
    JobDescriptionGenerateRequest, JobDescriptionGenerateResponse,
    SkillSuggestionsRequest, SkillSuggestionsResponse,
    JobRevisionListResponse, JobRevisionDetailResponse,
    JobQualityAnalyzeRequest, JobQualityAnalyzeResponse
)
from core.embeddings import EmbeddingService
from core.audit import log_audit_event
from core.limiter import limiter, recruiter_rate_limit_key


router = APIRouter(prefix="/jobs", tags=["jobs"])


def _parse_job_status(value: str) -> JobStatus:
    try:
        return JobStatus(value.lower())
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
    job_status = _parse_job_status(body.status)
    if job_status == JobStatus.OPEN:
        from core.quota import increment_quota_usage
        increment_quota_usage(db, current_user.company_id, "active_jobs_count", increment_by=1, request=request)

    settings_dict = body.settings.model_dump() if body.settings else {}
    job = Job(
        company_id=current_user.company_id,
        title=body.title,
        department=body.department,
        description=body.description,
        status=job_status,
        start_date=body.start_date,
        settings=settings_dict,
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

    # 1. Optimistic Concurrency check
    if body.client_updated_at is not None:
        db_updated_at = job.updated_at.replace(tzinfo=None)
        client_updated_at = body.client_updated_at.replace(tzinfo=None)
        if (db_updated_at - client_updated_at).total_seconds() > 1.0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This job posting has been updated by another user. Please reload the latest changes."
            )

    old_status = job.status
    changes = {}

    # 2. Check for meaningful changes to trigger a new revision
    has_meaningful_changes = False
    if body.title is not None and job.title != body.title:
        has_meaningful_changes = True
    if body.department is not None and job.department != body.department:
        has_meaningful_changes = True
    if body.description is not None and job.description != body.description:
        has_meaningful_changes = True

    new_settings_dict = {}
    if body.settings is not None:
        new_settings_dict = body.settings.model_dump()
        for key in ["required_skills", "preferred_skills", "salary_min", "salary_max", "workplace_type", "stages"]:
            if job.settings.get(key) != new_settings_dict.get(key):
                has_meaningful_changes = True

    # 3. Save a JobRevision snapshot of the PREVIOUS state if published and changed
    if old_status == JobStatus.OPEN and has_meaningful_changes:
        from sqlalchemy import func
        from models import JobRevision
        last_version = db.scalar(
            select(func.coalesce(func.max(JobRevision.version), 0))
            .where(JobRevision.job_id == job.id)
        ) or 0

        revision = JobRevision(
            job_id=job.id,
            version=last_version + 1,
            title=job.title,
            department=job.department,
            description=job.description,
            settings=job.settings,
            job_status=old_status,
            created_by=current_user.id,
            change_reason=body.change_reason or "Job details updated"
        )
        db.add(revision)

    # 4. Apply changes
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
    if body.settings is not None:
        current_settings = dict(job.settings)
        current_settings.update(new_settings_dict)
        job.settings = current_settings
        changes["settings"] = "edited"
    if body.status is not None:
        new_status = _parse_job_status(body.status)
        if old_status != new_status:
            if new_status == JobStatus.OPEN and old_status != JobStatus.OPEN:
                from core.quota import increment_quota_usage
                increment_quota_usage(db, current_user.company_id, "active_jobs_count", increment_by=1, request=request)
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


_job_description_cache = {}
_suggest_skills_cache = {}
_idempotency_cache = {}
_local_ai_usage = {}


def get_redis_connection():
    from core.config import get_settings
    import redis
    try:
        settings = get_settings()
        r = redis.from_url(settings.redis_url)
        r.ping()
        return r
    except Exception:
        return None


def check_ai_quota(recruiter_id: str, company_id: str) -> str | None:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    r = get_redis_connection()
    if r is not None:
        rec_key = f"ai_usage:recruiter:{recruiter_id}:{today}"
        comp_key = f"ai_usage:company:{company_id}:{today}"
        rec_count = int(r.get(rec_key) or 0)
        comp_count = int(r.get(comp_key) or 0)
        if rec_count >= 20:
            return "recruiter_limit_exceeded"
        if comp_count >= 100:
            return "company_limit_exceeded"
        r.incr(rec_key)
        r.expire(rec_key, 86400)
        r.incr(comp_key)
        r.expire(comp_key, 86400)
        return None
    else:
        global _local_ai_usage
        if recruiter_id not in _local_ai_usage or _local_ai_usage[recruiter_id]["date"] != today:
            _local_ai_usage[recruiter_id] = {"date": today, "count": 0}
        if _local_ai_usage[recruiter_id]["count"] >= 20:
            return "recruiter_limit_exceeded"
        if company_id not in _local_ai_usage or _local_ai_usage[company_id]["date"] != today:
            _local_ai_usage[company_id] = {"date": today, "count": 0}
        if _local_ai_usage[company_id]["count"] >= 100:
            return "company_limit_exceeded"
        _local_ai_usage[recruiter_id]["count"] += 1
        _local_ai_usage[company_id]["count"] += 1
        return None


@router.post("/generate-description", response_model=JobDescriptionGenerateResponse)
@limiter.limit("5/minute", key_func=recruiter_rate_limit_key)
def generate_job_description(
    body: JobDescriptionGenerateRequest,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")
):
    import json
    import time
    
    # 1. Idempotency Check
    r = get_redis_connection()
    if idempotency_key:
        idemp_key = f"idempotency:generate-description:{str(current_user.id)}:{idempotency_key}"
        if r is not None:
            cached_val = r.get(idemp_key)
            if cached_val:
                return JobDescriptionGenerateResponse(**json.loads(cached_val))
        else:
            global _idempotency_cache
            if idemp_key in _idempotency_cache:
                cached_time, cached_val = _idempotency_cache[idemp_key]
                if (time.time() - cached_time) < 300:
                    return JobDescriptionGenerateResponse(**cached_val)

    # 2. Cache Check
    from models import Company
    from core.intelligence import GenerativeIntelligenceService
    
    company = db.scalar(select(Company).where(Company.id == current_user.company_id))
    company_name = company.name if company else "Our Company"
    company_industry = body.industry or (company.settings.get("industry") if company and company.settings else None)

    cache_hash = f"{body.title.lower().strip()}:{body.department.lower().strip()}:{company_name.lower().strip()}:{body.section or 'all'}"
    if r is not None:
        cached_res = r.get(f"cache:generate-description:{cache_hash}")
        if cached_res:
            return JobDescriptionGenerateResponse(**json.loads(cached_res))
    else:
        global _job_description_cache
        if cache_hash in _job_description_cache:
            return JobDescriptionGenerateResponse(**_job_description_cache[cache_hash])

    # 3. Quota Check
    quota_err = check_ai_quota(str(current_user.id), str(current_user.company_id))
    if quota_err:
        limit_type = "recruiter daily limit (20 requests)" if quota_err == "recruiter_limit_exceeded" else "company daily limit (100 requests)"
        return JobDescriptionGenerateResponse(
            success=False,
            error_code="quota_exceeded",
            message=f"AI limit reached: you have exceeded your {limit_type}.",
            retryable=False
        )

    # 4. Invoke LLM and time it
    start_time = time.perf_counter()
    result = GenerativeIntelligenceService.generate_job_description_v2(
        title=body.title,
        department=body.department,
        company_name=company_name,
        industry=company_industry,
        workplace_type=body.workplace_type,
        employment_type=body.employment_type,
        seniority=body.seniority,
        required_skills=body.required_skills,
        preferred_skills=body.preferred_skills,
        section=body.section
    )
    latency = time.perf_counter() - start_time

    # 5. Log Audit Event
    audit_action = f"ai.generate_description.{result.get('error_code') or 'success'}"
    audit_metadata = {
        "latency_seconds": round(latency, 3),
        "success": result.get("success", False),
        "error_code": result.get("error_code"),
        "section": body.section or "all",
        "title": body.title,
        "department": body.department
    }
    log_audit_event(
        db=db,
        action=audit_action,
        actor_type="recruiter",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        metadata=audit_metadata
    )

    # 6. Save Caches
    if result.get("success", False):
        res_json = json.dumps(result)
        if r is not None:
            r.set(f"cache:generate-description:{cache_hash}", res_json, ex=3600)
            if idempotency_key:
                r.set(idemp_key, res_json, ex=300)
        else:
            _job_description_cache[cache_hash] = result
            if idempotency_key:
                _idempotency_cache[idemp_key] = (time.time(), result)

    return JobDescriptionGenerateResponse(**result)


@router.post("/suggest-skills", response_model=SkillSuggestionsResponse)
@limiter.limit("10/minute", key_func=recruiter_rate_limit_key)
def suggest_skills(
    body: SkillSuggestionsRequest,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb
):
    import json
    from core.intelligence import GenerativeIntelligenceService
    r = get_redis_connection()
    cache_hash = f"{body.title.lower().strip()}:{body.department.lower().strip() if body.department else 'general'}"
    if r is not None:
        cached_res = r.get(f"cache:suggest-skills:{cache_hash}")
        if cached_res:
            return SkillSuggestionsResponse(**json.loads(cached_res))
    else:
        global _suggest_skills_cache
        if cache_hash in _suggest_skills_cache:
            return SkillSuggestionsResponse(**_suggest_skills_cache[cache_hash])

    result = GenerativeIntelligenceService.suggest_skills_v2(
        title=body.title,
        department=body.department,
        existing_skills=body.existing_skills
    )

    if r is not None:
        r.set(f"cache:suggest-skills:{cache_hash}", json.dumps(result), ex=3600)
    else:
        _suggest_skills_cache[cache_hash] = result

    return SkillSuggestionsResponse(**result)


@router.post("/analyze-quality", response_model=JobQualityAnalyzeResponse)
def analyze_job_quality(
    body: JobQualityAnalyzeRequest,
    current_user: RequireRecruiter
):
    score = 0
    warnings = []
    recommendations = []

    # 1. Job Title (15 points)
    title_len = len(body.title.strip())
    if title_len > 0:
        score += 10
        if 5 <= title_len <= 50:
            score += 5
        else:
            recommendations.append("Keep the job title concise (between 5 and 50 characters) to optimize search matches.")
    else:
        warnings.append("Job title is empty. A descriptive title is required before publishing.")

    # 2. Role Description (20 points)
    desc = body.description or ""
    overview_match = "### Role Overview" in desc
    responsibilities_match = "### Key Responsibilities" in desc
    requirements_match = "### Requirements & Qualifications" in desc or "### Requirements &amp; Qualifications" in desc
    
    if len(desc.strip()) > 300:
        score += 5
    else:
        recommendations.append("Expand the job description context (over 300 characters) to attract higher quality candidates.")

    if overview_match or len(desc.strip()) > 100:
        score += 5
    else:
        warnings.append("Add a detailed Role Overview paragraph.")

    if responsibilities_match:
        score += 5
    else:
        warnings.append("Outline the Key Responsibilities section clearly.")

    if requirements_match:
        score += 5
    else:
        warnings.append("Outline the Requirements & Qualifications section clearly.")

    # 3. Skills (20 points)
    req_skills = body.settings.get("required_skills", [])
    if req_skills:
        score += 15
        if len(req_skills) >= 3:
            score += 5
        else:
            recommendations.append("Add at least 3 required skills to enable the AI matching engine to rank candidates accurately.")
    else:
        warnings.append("No required skills added. At least 1 required skill is blocker before publishing.")

    # 4. Salary details (15 points)
    salary_min = body.settings.get("salary_min")
    salary_max = body.settings.get("salary_max")
    hide_salary = body.settings.get("hide_salary", False)
    if salary_min is not None or salary_max is not None:
        score += 10
        if not hide_salary:
            score += 5
        else:
            recommendations.append("Unhide the salary range to increase application conversion rate by up to 30%.")
    else:
        recommendations.append("Add a salary range (even if hidden) to help candidates assess fit.")

    # 5. Benefits (10 points)
    benefits = body.settings.get("benefits", [])
    if benefits:
        score += 10
    else:
        recommendations.append("Specify perks & benefits (e.g. Health Insurance, Remote settings) to stand out to top talent.")

    # 6. Hiring Manager (10 points)
    hm_id = body.settings.get("hiring_manager_id")
    if hm_id:
        score += 10
    else:
        warnings.append("Assign a Hiring Manager to this opening to manage candidate review workflows.")

    # 7. Logistics (workplace, openings) (10 points)
    workplace = body.settings.get("workplace_type", "On-site")
    office = body.settings.get("office_address", "")
    openings = body.settings.get("openings", 1)

    if workplace == "Remote" or office.strip():
        score += 5
    elif workplace in ["On-site", "Hybrid"] and not office.strip():
        warnings.append("Office address is missing for On-site or Hybrid workplace configuration.")

    if openings > 0:
        score += 5

    return JobQualityAnalyzeResponse(
        score=score,
        warnings=warnings,
        recommendations=recommendations
    )


@router.get("/{id}/revisions", response_model=list[JobRevisionListResponse])
def get_job_revisions(
    id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb
):
    job = db.scalar(select(Job).where(Job.id == id))
    if not job or job.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Job opening not found.")
        
    from models import JobRevision
    stmt = select(JobRevision).where(JobRevision.job_id == id).order_by(JobRevision.version.desc())
    revisions = db.scalars(stmt).all()
    return revisions


@router.get("/{id}/revisions/{version}", response_model=JobRevisionDetailResponse)
def get_job_revision_detail(
    id: uuid.UUID,
    version: int,
    current_user: RequireRecruiter,
    db: TenantDb
):
    job = db.scalar(select(Job).where(Job.id == id))
    if not job or job.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Job opening not found.")
        
    from models import JobRevision
    revision = db.scalar(select(JobRevision).where(JobRevision.job_id == id, JobRevision.version == version))
    if not revision:
        raise HTTPException(status_code=404, detail="Revision version not found.")
    return revision



