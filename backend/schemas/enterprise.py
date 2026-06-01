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
