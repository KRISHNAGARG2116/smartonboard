import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class ApprovalTemplateStepCreate(BaseModel):
    sequence: int = Field(..., gt=0)
    parallel_group: int | None = None
    role_required: str | None = Field(default=None, max_length=50)
    approver_id: uuid.UUID | None = None


class ApprovalTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    target_type: str = Field(...)
    steps: list[ApprovalTemplateStepCreate] = Field(..., min_length=1)

    @field_validator('target_type')
    @classmethod
    def validate_target_type(cls, v: str) -> str:
        supported_targets = {'requisition', 'offer'}
        if v not in supported_targets:
            raise ValueError(f"Unsupported target type '{v}'. Supported: {supported_targets}")
        return v


class ApprovalTemplateResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    description: str | None
    target_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApprovalTemplateStepResponse(BaseModel):
    id: uuid.UUID
    approval_template_id: uuid.UUID
    sequence: int
    parallel_group: int | None
    role_required: str | None
    approver_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApprovalChainCreate(BaseModel):
    target_type: str = Field(...)
    approval_template_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    offer_id: uuid.UUID | None = None

    @field_validator('target_type')
    @classmethod
    def validate_target_type(cls, v: str) -> str:
        supported_targets = {'requisition', 'offer'}
        if v not in supported_targets:
            raise ValueError(f"Unsupported target type '{v}'. Supported: {supported_targets}")
        return v


class ApprovalChainResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    approval_template_id: uuid.UUID | None
    target_type: str
    job_id: uuid.UUID | None
    offer_id: uuid.UUID | None
    status: str
    current_step_sequence: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApprovalStepResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    approval_chain_id: uuid.UUID
    sequence: int
    parallel_group: int | None
    role_required: str | None
    approver_id: uuid.UUID | None
    status: str
    actioned_by: uuid.UUID | None
    actioned_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApprovalStepAction(BaseModel):
    action: str = Field(...)
    rejection_reason: str | None = None

    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        supported_actions = {'approve', 'reject'}
        if v not in supported_actions:
            raise ValueError(f"Unsupported action '{v}'. Supported: {supported_actions}")
        return v
