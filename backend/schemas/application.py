import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ApplicationCreateRequest(BaseModel):
    job_id: uuid.UUID
    candidate_name: str = Field(min_length=1, max_length=255)
    candidate_email: EmailStr
    candidate_phone: str | None = Field(default=None, max_length=50)
    source: str = Field(default="manual", max_length=50)


class ApplicationUpdateRequest(BaseModel):
    status: str | None = None
    current_stage_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    client_updated_at: datetime | None = None


class CandidateBrief(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None

    model_config = {"from_attributes": True}


class JobBrief(BaseModel):
    id: uuid.UUID
    title: str
    department: str

    model_config = {"from_attributes": True}


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    status: str
    source: str
    created_at: datetime
    updated_at: datetime
    match_score: float | None = None
    candidate: CandidateBrief | None = None
    job: JobBrief | None = None
    current_stage_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class ApplicationEventResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    event_type: str
    actor_id: uuid.UUID | None = None
    actor_name: str | None = None
    metadata_json: dict = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class BulkUpdatePreviewPayload(BaseModel):
    application_ids: list[uuid.UUID]
    target_stage_id: uuid.UUID | None = None
    target_status: str | None = None
    target_owner_id: uuid.UUID | None = None


class BulkUpdatePayload(BaseModel):
    application_ids: list[uuid.UUID]
    target_stage_id: uuid.UUID | None = None
    target_status: str | None = None
    target_owner_id: uuid.UUID | None = None


class BulkPreviewWarning(BaseModel):
    application_id: uuid.UUID
    candidate_name: str
    warning_type: str
    message: str


class BulkUpdatePreviewResponse(BaseModel):
    total_applications: int
    warnings: list[BulkPreviewWarning]

