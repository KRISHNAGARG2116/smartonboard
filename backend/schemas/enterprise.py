import ipaddress
import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, EmailStr


class CompanyIPWhitelistCreate(BaseModel):
    cidr_block: str = Field(..., description="Allowed CIDR range, e.g., '192.168.1.0/24' or '10.0.0.0/8'")
    description: str | None = Field(None, max_length=255)

    @field_validator("cidr_block")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        try:
            # Parse CIDR block using ipaddress to validate subnet structure
            ipaddress.ip_network(v, strict=False)
        except Exception:
            raise ValueError("Invalid CIDR format. Must be a valid subnet CIDR block (e.g. '192.168.1.0/24').")
        return v


class CompanyIPWhitelistResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    cidr_block: str
    is_active: bool
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class CompanySMTPSettingsCreate(BaseModel):
    hostname: str = Field(..., max_length=255, description="SMTP server host, e.g., 'smtp.gmail.com'")
    port: int = Field(..., description="SMTP server port, e.g., 587, 465, or 25")
    username: str = Field(..., max_length=255, description="SMTP authenticated username/email")
    password: str = Field(..., min_length=1, description="SMTP authenticated credentials password")
    sender_email: EmailStr = Field(..., description="Whitelisted custom sender address header")

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("SMTP port must reside within a valid TCP boundary of [1, 65535].")
        return v


class CompanySMTPSettingsResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    hostname: str
    port: int
    username: str
    sender_email: str
    verification_status: str
    last_verification_error: str | None
    last_verified_at: datetime | None
    last_rotated_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanySubscriptionPlanUpdateRequest(BaseModel):
    tier_name: str = Field(..., description="Plan tier name: 'free' | 'growth' | 'enterprise'")

    @field_validator("tier_name")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        if v.lower() not in ("free", "growth", "enterprise"):
            raise ValueError("Plan tier name must reside within ('free', 'growth', 'enterprise').")
        return v.lower()


class CompanySubscriptionPlanResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    tier_name: str
    candidate_limit: int
    job_limit: int
    ai_limit: int
    webhook_limit: int
    pending_downgrade_tier: str | None
    pending_downgrade_effective_at: datetime | None
    billing_cycle_start: datetime
    billing_cycle_end: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyUsageLedgerResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    candidates_processed: int
    active_jobs_count: int
    ai_screenings_run: int
    webhooks_dispatched: int
    last_reset_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
