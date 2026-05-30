import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    department: str = Field(default="General", max_length=100)
    description: str = Field(default="", max_length=20000)
    status: str = Field(default="draft")
    start_date: date | None = None


class JobUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    department: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=20000)
    status: str | None = None
    start_date: date | None = None


class JobResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    department: str
    description: str
    status: str
    start_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
