import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class FunnelStageMetric(BaseModel):
    stage: str
    candidate_count: int
    conversion_count: int
    conversion_rate: float
    drop_off_count: int
    drop_off_rate: float


class FunnelAnalyticsResponse(BaseModel):
    job_id: uuid.UUID | None = None
    stages: list[FunnelStageMetric]


class StageVelocityMetric(BaseModel):
    stage: str
    average_duration_seconds: float
    transition_count: int


class VelocityAnalyticsResponse(BaseModel):
    job_id: uuid.UUID | None = None
    stages: list[StageVelocityMetric]


class RecruiterProductivityMetric(BaseModel):
    recruiter_id: uuid.UUID
    recruiter_name: str
    applications_reviewed: int
    candidates_advanced: int
    interviews_scheduled: int
    offers_created: int
    offers_accepted: int
    updated_at: datetime


class RecruiterProductivityResponse(BaseModel):
    metrics: list[RecruiterProductivityMetric]
