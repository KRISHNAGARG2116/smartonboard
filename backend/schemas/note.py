import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class NoteCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class NoteUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class NoteResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    application_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
