import uuid
import base64
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from api.deps import TenantDb, RequireRecruiter, has_job_access
from models import Application, Candidate, Job, StageDefinition
from models.ats_models import SavedSearch

router = APIRouter(prefix="/search", tags=["search"])


class SearchBreakdown(BaseModel):
    skills: int
    experience: int
    activity: int
    recency: int
    stage: int


class SearchResultItem(BaseModel):
    candidate_id: uuid.UUID
    full_name: str
    email: str | None
    phone: str | None
    match_score: float
    score_breakdown: SearchBreakdown
    created_at: datetime
    application_id: uuid.UUID


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    next_cursor: str | None


class SearchRequest(BaseModel):
    query: str | None = None
    job_id: uuid.UUID | None = None
    stage_id: uuid.UUID | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None


class SavedSearchCreate(BaseModel):
    name: str
    filters: dict


class SavedSearchResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    recruiter_id: uuid.UUID
    name: str
    filters: dict
    created_at: datetime

    model_config = {"from_attributes": True}


def compute_ranking_score(app: Application, db: TenantDb) -> tuple[float, dict]:
    # 1. AI Match
    ai_score = int((app.match_score or 0.5) * 100) if app.match_score is not None else 50

    # 2. Recruiter scorecard rating
    from models.scorecard import Scorecard
    scorecards = db.scalars(
        select(Scorecard).where(Scorecard.application_id == app.id, Scorecard.is_draft == False)
    ).all()
    if scorecards:
        total = 0
        for s in scorecards:
            rec = s.overall_recommendation.lower()
            if rec == "strong_yes":
                total += 100
            elif rec == "yes":
                total += 75
            elif rec == "no":
                total += 25
            else:
                total += 0
        scorecard_score = int(total / len(scorecards))
    else:
        scorecard_score = 50

    # 3. Recency
    delta = (datetime.now(timezone.utc) - app.created_at.replace(tzinfo=timezone.utc)).days
    recency_score = max(0, 100 - delta * 2)

    # 4. Pipeline Stage
    stage_score = 20
    if app.current_stage:
        cat = app.current_stage.base_category.lower()
        if cat == "applied":
            stage_score = 20
        elif cat == "screening":
            stage_score = 40
        elif cat == "interviewing":
            stage_score = 60
        elif cat == "offered":
            stage_score = 80
        elif cat == "hired":
            stage_score = 100
        elif cat == "rejected":
            stage_score = 0
    else:
        status_val = app.status.value.lower() if app.status else "submitted"
        if status_val == "submitted":
            stage_score = 20
        elif status_val == "screening":
            stage_score = 40
        elif status_val == "interview":
            stage_score = 60
        elif status_val == "offer":
            stage_score = 80
        elif status_val == "hired":
            stage_score = 100
        elif status_val == "rejected":
            stage_score = 0

    # 5. Activity
    from models.ats_models import ApplicationEvent
    events_count = db.scalar(
        select(func.count(ApplicationEvent.id)).where(ApplicationEvent.application_id == app.id)
    ) or 0
    activity_score = min(100, events_count * 10)

    # Weighted overall score
    overall = (
        ai_score * 0.40 +
        scorecard_score * 0.30 +
        recency_score * 0.10 +
        stage_score * 0.10 +
        activity_score * 0.10
    )

    breakdown = {
        "skills": ai_score,
        "experience": scorecard_score,
        "activity": activity_score,
        "recency": recency_score,
        "stage": stage_score
    }
    return round(overall, 2), breakdown


@router.post("/candidates", response_model=SearchResponse)
def search_candidates(
    payload: SearchRequest,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Enforces job-level RLS, filters applications, and performs cursor pagination.
    Returns candidate results ranked by weighted ATS scoring details.
    """
    # 1. Base Query
    stmt = (
        select(Application)
        .options(selectinload(Application.candidate), selectinload(Application.current_stage))
        .join(Candidate, Application.candidate_id == Candidate.id)
        .where(Application.company_id == current_user.company_id)
    )

    # 2. Query/Filters
    if payload.query:
        stmt = stmt.where(
            (Candidate.full_name.ilike(f"%{payload.query}%")) |
            (Candidate.email.ilike(f"%{payload.query}%")) |
            (Candidate.phone.ilike(f"%{payload.query}%"))
        )
    if payload.job_id:
        if not has_job_access(db, current_user, payload.job_id, "read"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this job")
        stmt = stmt.where(Application.job_id == payload.job_id)
    if payload.stage_id:
        stmt = stmt.where(Application.current_stage_id == payload.stage_id)
    if payload.status:
        from api.applications import _parse_application_status
        stmt = stmt.where(Application.status == _parse_application_status(payload.status))

    if payload.tags:
        from models.ats_models import CandidateTag, candidate_tag_associations
        stmt = stmt.join(candidate_tag_associations, Candidate.id == candidate_tag_associations.c.candidate_id).join(
            CandidateTag, CandidateTag.id == candidate_tag_associations.c.tag_id
        ).where(CandidateTag.name.in_(payload.tags))

    # 3. Cursor Pagination
    # Order strictly by created_at desc, id desc to prevent duplicate page issues
    if payload.cursor:
        try:
            cursor_str = base64.b64decode(payload.cursor.encode("utf-8")).decode("utf-8")
            cursor_time_str, cursor_id_str = cursor_str.split("|")
            cursor_time = datetime.fromisoformat(cursor_time_str)
            cursor_id = uuid.UUID(cursor_id_str)
            stmt = stmt.where(
                (Application.created_at < cursor_time) |
                ((Application.created_at == cursor_time) & (Application.id < cursor_id))
            )
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor token")

    stmt = stmt.order_by(Application.created_at.desc(), Application.id.desc())

    # Limit to payload.limit + 1 to check if there is a next page
    stmt = stmt.limit(payload.limit + 1)
    apps = db.scalars(stmt).all()

    has_next = len(apps) > payload.limit
    results_apps = apps[:payload.limit]

    # Rank results
    items = []
    for app in results_apps:
        overall_score, breakdown = compute_ranking_score(app, db)
        items.append(
            SearchResultItem(
                candidate_id=app.candidate.id,
                full_name=app.candidate.full_name,
                email=app.candidate.email,
                phone=app.candidate.phone,
                match_score=overall_score,
                score_breakdown=SearchBreakdown(**breakdown),
                created_at=app.created_at,
                application_id=app.id
            )
        )

    # Sort results by match_score descending
    items.sort(key=lambda x: x.match_score, reverse=True)

    next_cursor = None
    if has_next and results_apps:
        last_app = results_apps[-1]
        raw_cursor = f"{last_app.created_at.isoformat()}|{str(last_app.id)}"
        next_cursor = base64.b64encode(raw_cursor.encode("utf-8")).decode("utf-8")

    return SearchResponse(results=items, next_cursor=next_cursor)


@router.post("/saved", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
def create_saved_search(
    body: SavedSearchCreate,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Saves a filter search config in the database.
    """
    saved = SavedSearch(
        company_id=current_user.company_id,
        recruiter_id=current_user.id,
        name=body.name,
        filters=body.filters
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


@router.get("/saved", response_model=list[SavedSearchResponse])
def list_saved_searches(
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Lists saved search configs for the recruiter.
    """
    stmt = select(SavedSearch).where(
        SavedSearch.company_id == current_user.company_id,
        SavedSearch.recruiter_id == current_user.id
    )
    return db.scalars(stmt).all()
