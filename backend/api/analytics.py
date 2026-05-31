import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func

from api.deps import RequireRecruiter, TenantDb
from models.funnel_aggregate import FunnelAggregate
from models.stage_transition import CandidateStageTransition
from models.recruiter_productivity import RecruiterProductivityAggregate
from models.application import Application
from models.user import User
from models.job import Job
from schemas.analytics import (
    FunnelAnalyticsResponse,
    FunnelStageMetric,
    VelocityAnalyticsResponse,
    StageVelocityMetric,
    RecruiterProductivityResponse,
    RecruiterProductivityMetric,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

STANDARD_STAGES = ["submitted", "screening", "interview", "offer", "hired", "rejected"]


@router.get("/funnel", response_model=FunnelAnalyticsResponse)
def get_funnel_analytics(
    db: TenantDb,
    current_user: RequireRecruiter,
    job_id: uuid.UUID | None = Query(default=None),
):
    """
    Exposes conversion and drop-off analysis metrics for the recruiting funnel.
    Supports filtering by specific job and enforces strict company boundaries.
    """
    if job_id:
        # Enforce strict Python company boundary check
        job = db.scalar(
            select(Job).where(
                Job.id == job_id,
                Job.company_id == current_user.company_id
            )
        )
        if job is None:
            return FunnelAnalyticsResponse(
                job_id=job_id,
                stages=[
                    FunnelStageMetric(
                        stage=stage,
                        candidate_count=0,
                        conversion_count=0,
                        conversion_rate=0.0,
                        drop_off_count=0,
                        drop_off_rate=0.0
                    )
                    for stage in STANDARD_STAGES
                ]
            )

        stmt = select(FunnelAggregate).where(
            FunnelAggregate.job_id == job_id,
            FunnelAggregate.company_id == current_user.company_id
        )
        rows = db.scalars(stmt).all()
        stage_map = {r.stage: (r.candidate_count, r.conversion_count) for r in rows}
    else:
        stmt = (
            select(
                FunnelAggregate.stage,
                func.sum(FunnelAggregate.candidate_count).label("candidate_count"),
                func.sum(FunnelAggregate.conversion_count).label("conversion_count")
            )
            .where(FunnelAggregate.company_id == current_user.company_id)
            .group_by(FunnelAggregate.stage)
        )
        results = db.execute(stmt).all()
        stage_map = {r.stage: (r.candidate_count, r.conversion_count) for r in results}

    stages_data = []
    for stage in STANDARD_STAGES:
        cand_cnt, conv_cnt = stage_map.get(stage, (0, 0))
        cand_cnt = int(cand_cnt) if cand_cnt is not None else 0
        conv_cnt = int(conv_cnt) if conv_cnt is not None else 0
        
        conv_rate = (conv_cnt / cand_cnt) if cand_cnt > 0 else 0.0
        drop_cnt = max(0, cand_cnt - conv_cnt)
        drop_rate = (drop_cnt / cand_cnt) if cand_cnt > 0 else 0.0
        
        stages_data.append(FunnelStageMetric(
            stage=stage,
            candidate_count=cand_cnt,
            conversion_count=conv_cnt,
            conversion_rate=round(conv_rate, 4),
            drop_off_count=drop_cnt,
            drop_off_rate=round(drop_rate, 4)
        ))

    return FunnelAnalyticsResponse(job_id=job_id, stages=stages_data)


@router.get("/velocity", response_model=VelocityAnalyticsResponse)
def get_velocity_analytics(
    db: TenantDb,
    current_user: RequireRecruiter,
    job_id: uuid.UUID | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
):
    """
    Calculates historical time-in-stage statistics (velocity metrics) based on candidate stage transitions.
    Supports filtering by job and date ranges, enforcing company boundaries.
    """
    if job_id:
        # Enforce strict Python company boundary check
        job = db.scalar(
            select(Job).where(
                Job.id == job_id,
                Job.company_id == current_user.company_id
            )
        )
        if job is None:
            return VelocityAnalyticsResponse(
                job_id=job_id,
                stages=[
                    StageVelocityMetric(
                        stage=stage,
                        average_duration_seconds=0.0,
                        transition_count=0
                    )
                    for stage in STANDARD_STAGES
                ]
            )

    stmt = (
        select(
            CandidateStageTransition.to_status.label("stage"),
            func.avg(CandidateStageTransition.duration_seconds).label("avg_duration"),
            func.count(CandidateStageTransition.id).label("count")
        )
        .where(
            CandidateStageTransition.duration_seconds.isnot(None),
            CandidateStageTransition.company_id == current_user.company_id
        )
    )

    if job_id:
        stmt = stmt.join(
            Application,
            CandidateStageTransition.application_id == Application.id
        ).where(Application.job_id == job_id)

    if start_date:
        stmt = stmt.where(CandidateStageTransition.transitioned_at >= start_date)
    if end_date:
        stmt = stmt.where(CandidateStageTransition.transitioned_at <= end_date)

    stmt = stmt.group_by(CandidateStageTransition.to_status)
    rows = db.execute(stmt).all()
    stage_map = {r.stage: (r.avg_duration, r.count) for r in rows}

    stages_data = []
    for stage in STANDARD_STAGES:
        avg_dur, count = stage_map.get(stage, (0.0, 0))
        stages_data.append(StageVelocityMetric(
            stage=stage,
            average_duration_seconds=round(float(avg_dur), 2) if avg_dur else 0.0,
            transition_count=int(count) if count is not None else 0
        ))

    return VelocityAnalyticsResponse(job_id=job_id, stages=stages_data)


@router.get("/recruiter-productivity", response_model=RecruiterProductivityResponse)
def get_recruiter_productivity(
    db: TenantDb,
    current_user: RequireRecruiter,
    recruiter_id: uuid.UUID | None = Query(default=None),
):
    """
    Exposes key recruiter accomplishment statistics across the company.
    Supports filtering to a specific recruiter, enforcing company boundaries.
    """
    if recruiter_id:
        # Enforce strict Python company boundary check
        recruiter = db.scalar(
            select(User).where(
                User.id == recruiter_id,
                User.company_id == current_user.company_id
            )
        )
        if recruiter is None:
            return RecruiterProductivityResponse(metrics=[])

    stmt = (
        select(
            RecruiterProductivityAggregate,
            User.full_name.label("recruiter_name")
        )
        .join(User, RecruiterProductivityAggregate.recruiter_id == User.id)
        .where(RecruiterProductivityAggregate.company_id == current_user.company_id)
    )

    if recruiter_id:
        stmt = stmt.where(RecruiterProductivityAggregate.recruiter_id == recruiter_id)

    rows = db.execute(stmt).all()
    metrics = []
    for row in rows:
        agg = row.RecruiterProductivityAggregate
        metrics.append(RecruiterProductivityMetric(
            recruiter_id=agg.recruiter_id,
            recruiter_name=row.recruiter_name,
            applications_reviewed=agg.applications_reviewed,
            candidates_advanced=agg.candidates_advanced,
            interviews_scheduled=agg.interviews_scheduled,
            offers_created=agg.offers_created,
            offers_accepted=agg.offers_accepted,
            updated_at=agg.updated_at
        ))

    return RecruiterProductivityResponse(metrics=metrics)
