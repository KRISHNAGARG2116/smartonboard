import uuid
from datetime import datetime
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    type: str
    status: str
    read_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
