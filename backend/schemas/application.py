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
    candidate: CandidateBrief | None = None
    job: JobBrief | None = None

    model_config = {"from_attributes": True}
