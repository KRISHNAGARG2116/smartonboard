import uuid
from datetime import datetime
from typing import Dict
from pydantic import BaseModel, Field, field_validator


class ScorecardSubmitRequest(BaseModel):
    criteria_scores: Dict[str, int] = Field(..., description="Map of criteria names to score grades (e.g., 1-5)")
    overall_recommendation: str = Field(..., description="Overall fit recommendation: strong_yes, yes, no, strong_no")
    notes: str | None = Field(default=None, max_length=20000)

    @field_validator("overall_recommendation")
    @classmethod
    def validate_recommendation(cls, v: str) -> str:
        allowed = {"strong_yes", "yes", "no", "strong_no", "strong_hire", "hire", "lean_hire", "lean_no", "no_hire"}
        if v.lower() not in allowed:
            raise ValueError("overall_recommendation must be one of: strong_yes, yes, no, strong_no, strong_hire, hire, lean_hire, lean_no, no_hire")
        return v.lower()

    @field_validator("criteria_scores")
    @classmethod
    def validate_scores(cls, v: Dict[str, int]) -> Dict[str, int]:
        for criteria, score in v.items():
            if score < 1 or score > 5:
                raise ValueError(f"Score for criteria '{criteria}' must be between 1 and 5 inclusive")
        return v


class ScorecardResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    application_id: uuid.UUID
    interview_id: uuid.UUID
    grader_id: uuid.UUID
    criteria_scores: Dict[str, int]
    overall_recommendation: str
    notes: str | None
    is_draft: bool
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScorecardDraftRequest(BaseModel):
    criteria_scores: Dict[str, int] = Field(default_factory=dict)
    overall_recommendation: str | None = None
    notes: str | None = None

