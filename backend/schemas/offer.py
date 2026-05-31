import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class OfferCreateRequest(BaseModel):
    salary: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    equity_grant: str | None = Field(default=None, max_length=100)
    start_date: date
    expires_at: datetime


class OfferDecideRequest(BaseModel):
    decision: str = Field(..., description="Decision must be signed or rejected")

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        allowed = {"signed", "rejected"}
        if v.lower() not in allowed:
            raise ValueError("decision must be one of: signed, rejected")
        return v.lower()


class OnboardingTriggerPayload(BaseModel):
    candidate_id: uuid.UUID
    application_id: uuid.UUID
    offer_id: uuid.UUID
    company_id: uuid.UUID
    start_date: date
    status: str = "ready_for_onboarding"


class OfferResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    application_id: uuid.UUID
    salary: Decimal
    equity_grant: str | None
    start_date: date
    expires_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime
    onboarding_trigger: OnboardingTriggerPayload | None = None

    model_config = {"from_attributes": True}
