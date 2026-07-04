import uuid
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
