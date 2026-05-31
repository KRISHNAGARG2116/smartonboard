import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class InterviewCreateRequest(BaseModel):
    interviewer_id: uuid.UUID
    title: str = Field(min_length=1, max_length=150)
    stage: str = Field(min_length=1, max_length=50) # screening, technical_interview, behavioral_interview, partner_interview
    scheduled_at: datetime
    duration_minutes: int = Field(default=45, ge=5, le=480)
    video_link: str | None = Field(default=None, max_length=500)


class InterviewUpdateRequest(BaseModel):
    interviewer_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=150)
    stage: str | None = Field(default=None, min_length=1, max_length=50)
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    video_link: str | None = Field(default=None, max_length=500)
    is_cancelled: bool | None = None


class InterviewNotificationDraftResponse(BaseModel):
    recipient_email: str
    recipient_name: str
    subject: str
    body: str
    draft_payload: dict


class InterviewResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    application_id: uuid.UUID
    interviewer_id: uuid.UUID
    title: str
    stage: str
    scheduled_at: datetime
    duration_minutes: int
    video_link: str | None
    is_cancelled: bool
    created_at: datetime
    updated_at: datetime
    notification_draft: InterviewNotificationDraftResponse | None = None

    model_config = {"from_attributes": True}
