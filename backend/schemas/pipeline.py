import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class AutomationRuleSchema(BaseModel):
    type: str
    config: dict = Field(default_factory=dict)

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        supported_types = {"send_email", "send_form", "trigger_assessment"}
        if v not in supported_types:
            raise ValueError(f"Unsupported automation type '{v}'. Supported: {supported_types}")
        return v


class StageDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sequence: int = Field(..., gt=0)
    base_category: str = Field(...)
    settings: dict = Field(default_factory=dict)
    automation_rules: list[AutomationRuleSchema] = Field(default_factory=list)

    @field_validator('base_category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        supported_categories = {'applied', 'screening', 'interviewing', 'offered', 'hired', 'rejected'}
        if v not in supported_categories:
            raise ValueError(f"Unsupported base category '{v}'. Supported: {supported_categories}")
        return v


class PipelineTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    stages: list[StageDefinitionCreate] = Field(..., min_length=1)


class PipelineTemplateResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StageDefinitionResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    pipeline_template_id: uuid.UUID | None = None
    pipeline_id: uuid.UUID | None = None
    name: str
    sequence: int
    base_category: str
    is_active: bool
    archived_at: datetime | None = None
    settings: dict
    automation_rules: list[dict]
    created_at: datetime
    updated_at: datetime
    job_id: uuid.UUID | None = None
    color: str | None = None
    icon: str | None = None
    position: int | None = None
    sla_hours: int | None = None
    sla_enabled: bool = True
    is_default: bool = False
    is_terminal: bool = False
    allowed_next_stage_ids: list[uuid.UUID] | None = None
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}


class StageDefinitionJobCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    base_category: str = Field(...)
    color: str | None = None
    icon: str | None = None
    position: int | None = None
    sla_hours: int | None = None
    sla_enabled: bool = True
    is_default: bool = False
    is_terminal: bool = False
    allowed_next_stage_ids: list[uuid.UUID] | None = Field(default_factory=list)

    @field_validator('base_category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        supported_categories = {'applied', 'screening', 'interviewing', 'offered', 'hired', 'rejected'}
        if v not in supported_categories:
            raise ValueError(f"Unsupported base category '{v}'. Supported: {supported_categories}")
        return v


class StageDefinitionJobUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    base_category: str | None = None
    color: str | None = None
    icon: str | None = None
    position: int | None = None
    sla_hours: int | None = None
    sla_enabled: bool | None = None
    is_default: bool | None = None
    is_terminal: bool | None = None
    allowed_next_stage_ids: list[uuid.UUID] | None = None

    @field_validator('base_category')
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is None:
            return v
        supported_categories = {'applied', 'screening', 'interviewing', 'offered', 'hired', 'rejected'}
        if v not in supported_categories:
            raise ValueError(f"Unsupported base category '{v}'. Supported: {supported_categories}")
        return v


class PipelineResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    description: str | None
    pipeline_version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StructuredRule(BaseModel):
    field: str = Field(..., min_length=1)
    operator: str = Field(...)
    value: str | int | float | bool = Field(...)
    target_stage_id: uuid.UUID = Field(...)

    @field_validator('operator')
    @classmethod
    def validate_operator(cls, v: str) -> str:
        supported = {'==', '>', '>=', '<', '<=', '!=', 'contains'}
        if v not in supported:
            raise ValueError(f"Unsupported operator '{v}'. Supported: {supported}")
        return v


class StageSLACreate(BaseModel):
    duration_seconds: int = Field(..., gt=0)
    escalation_action: str = Field(...)
    fallback_stage_id: uuid.UUID | None = None

    @field_validator('escalation_action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        supported = {'notify_recruiter', 'notify_manager', 'auto_reject', 'auto_advance'}
        if v not in supported:
            raise ValueError(f"Unsupported escalation action '{v}'. Supported: {supported}")
        return v


class StageSLAResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    stage_definition_id: uuid.UUID
    duration_seconds: int
    escalation_action: str
    fallback_stage_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PipelineUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    stages: list[StageDefinitionCreate] = Field(..., min_length=1)


class PipelineDetailsResponse(PipelineResponse):
    stages: list[StageDefinitionResponse]

