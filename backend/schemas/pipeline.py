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

    model_config = {"from_attributes": True}


class PipelineResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    description: str | None
    pipeline_version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
