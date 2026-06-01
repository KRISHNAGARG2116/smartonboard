import uuid
from datetime import date, datetime
from pydantic import BaseModel, Field

class EmployeeConvertRequest(BaseModel):
    employment_type: str = Field(..., description="Employment type: e.g. full_time, part_time, contractor, intern")
    employee_number: str | None = Field(default=None, max_length=100, description="Employee assignment code")
    supervisor_id: uuid.UUID | None = Field(default=None, description="Manager employee ID")


class EmployeeConvertResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    job_title: str
    employment_type: str
    employee_number: str | None
    status: str
    start_date: date
    workflow_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class EmployeeResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    candidate_id: uuid.UUID | None = None
    email: str
    full_name: str
    phone: str | None = None
    job_title: str
    department: str | None = None
    employment_type: str
    employee_number: str | None = None
    status: str
    sync_status: str
    sync_error: str | None = None
    start_date: date
    supervisor_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HRISFieldMappingCreate(BaseModel):
    provider: str
    local_field: str
    provider_field: str
    is_custom: bool = False
    transform_rules: dict = {}


class HRISFieldMappingResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    provider: str
    local_field: str
    provider_field: str
    is_custom: bool
    transform_rules: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SyncMetricResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    provider: str
    metric_name: str
    metric_value: float
    timestamp: datetime

    model_config = {"from_attributes": True}


class DLQRecordResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    outbox_id: uuid.UUID
    provider: str
    error_message: str
    payload: dict
    status: str
    resolved_at: datetime | None = None
    resolved_by_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmployeeSyncHistoryResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    employee_id: uuid.UUID
    provider: str
    request_id: uuid.UUID
    sync_state: str
    attempt_number: int
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    error_message: str | None = None
    payload_hash: str
    created_at: datetime

    model_config = {"from_attributes": True}

