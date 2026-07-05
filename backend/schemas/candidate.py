import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class CandidateDeletionRequest(BaseModel):
    confirm: bool = Field(
        ...,
        description="Explicit confirmation flag required to execute GDPR Right-to-Be-Forgotten candidate erasure."
    )

class CandidateAssignmentPayload(BaseModel):
    owner_id: uuid.UUID | None = None
    secondary_recruiters: list[uuid.UUID] = Field(default_factory=list)
    watchers: list[uuid.UUID] = Field(default_factory=list)

class CandidateTagsPayload(BaseModel):
    tag_ids: list[uuid.UUID]

class CandidateMergePayload(BaseModel):
    surviving_candidate_id: uuid.UUID


class CandidateTagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6b7280")
    icon: str | None = Field(default=None)


class CandidateTagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None)
    icon: str | None = Field(default=None)


class CandidateTagResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    color: str
    icon: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
