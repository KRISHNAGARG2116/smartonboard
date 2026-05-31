import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator

class SkillSchema(BaseModel):
    skill_key: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)
    weight: float = Field(..., gt=0.0, le=1.0)

class ScorecardTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    skills: list[SkillSchema] = Field(..., min_length=1)

    @model_validator(mode='after')
    def validate_weights(self) -> 'ScorecardTemplateCreate':
        total = sum(s.weight for s in self.skills)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"The sum of skill weights must be exactly 1.0. Got: {total}")
        return self

class ScorecardTemplateSkillResponse(BaseModel):
    id: uuid.UUID
    skill_key: str
    display_name: str
    weight: float
    created_at: datetime

    model_config = {"from_attributes": True}

class ScorecardTemplateResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    skills: list[ScorecardTemplateSkillResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class CommitteeMemberCreate(BaseModel):
    user_id: uuid.UUID
    role: str = Field(default="reviewer")
    reviewer_weight: float = Field(default=1.00, gt=0.0, le=10.0)

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        supported = {"reviewer", "chair"}
        if v not in supported:
            raise ValueError(f"Unsupported committee role '{v}'. Supported: {supported}")
        return v

class CommitteeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    quorum_percentage: int = Field(default=100, gt=0, le=100)
    min_score_threshold: float = Field(default=3.00, gt=1.0, le=5.0)
    consensus_sd_threshold: float = Field(default=0.75, gt=0.0, le=5.0)
    allow_veto: bool = Field(default=True)
    veto_skill_keys: list[str] = Field(default_factory=list)
    members: list[CommitteeMemberCreate] = Field(..., min_length=1)

class CommitteeMemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role: str
    reviewer_weight: float
    created_at: datetime

    model_config = {"from_attributes": True}

class CommitteeResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    description: str | None
    quorum_percentage: int
    min_score_threshold: float
    consensus_sd_threshold: float
    allow_veto: bool
    veto_skill_keys: list[str]
    members: list[CommitteeMemberResponse]
    created_at: datetime

    model_config = {"from_attributes": True}

class ReviewInitiate(BaseModel):
    hiring_committee_id: uuid.UUID
    scorecard_template_id: uuid.UUID
    review_due_at: datetime | None = None

class CommitteeReviewReviewerResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role: str
    reviewer_weight: float
    created_at: datetime

    model_config = {"from_attributes": True}

class CommitteeReviewResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    application_id: uuid.UUID
    hiring_committee_id: uuid.UUID
    scorecard_template_id: uuid.UUID
    status: str
    average_score: float | None = None
    reconciliation_notes: str | None = None
    review_due_at: datetime | None = None
    reviewers: list[CommitteeReviewReviewerResponse]
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}

class ReviewReconcile(BaseModel):
    resolution: str
    notes: str = Field(..., min_length=1)

    @field_validator('resolution')
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        supported = {"approve", "reject"}
        if v not in supported:
            raise ValueError(f"Unsupported reconciliation resolution '{v}'. Supported: {supported}")
        return v
