import uuid
from datetime import datetime
from pydantic import BaseModel

class AuditLogResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    actor_type: str
    action: str
    resource_type: str | None
    resource_id: str | None
    ip_address: str | None
    user_agent: str | None
    metadata_json: dict | None
    timestamp: datetime

    class Config:
        from_attributes = True
