import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class NoteCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    visibility: str | None = Field(default="everyone", description="Scope: everyone, hiring_team, interview_panel, private")
    attachments_json: list | None = Field(default_factory=list, description="List of note attachment metadata objects")


class NoteUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    visibility: str | None = Field(default=None, description="Scope: everyone, hiring_team, interview_panel, private")
    attachments_json: list | None = Field(default=None, description="List of note attachment metadata objects")


class NoteResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    application_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    visibility: str
    attachments_json: list
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
