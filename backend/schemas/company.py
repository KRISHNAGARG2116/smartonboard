import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    status: str
    domain_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
