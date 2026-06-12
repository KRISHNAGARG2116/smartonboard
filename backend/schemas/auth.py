import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Recruiter registration request."""
    company_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class CandidateRegisterRequest(BaseModel):
    """Candidate registration request - no company required."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class CandidateLoginRequest(BaseModel):
    """Candidate login request - email + password."""
    email: EmailStr
    password: str


class CandidateOTPRequest(BaseModel):
    """Request to send an email OTP to a candidate."""
    email: EmailStr


class CandidateOTPVerifyRequest(BaseModel):
    """Verify an email OTP for a candidate."""
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    email_verified: bool = False
    company_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    user: UserResponse


class SessionResponse(BaseModel):
    id: uuid.UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    last_active: datetime
    is_revoked: bool

    model_config = {"from_attributes": True}


class RevokeSessionRequest(BaseModel):
    session_id: uuid.UUID


class CandidatePhoneOTPRequest(BaseModel):
    phone_number: str = Field(min_length=5, max_length=50)


class CandidatePhoneOTPVerifyRequest(BaseModel):
    phone_number: str = Field(min_length=5, max_length=50)
    code: str = Field(min_length=6, max_length=6)


class CandidateProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone_number: Optional[str] = Field(default=None, max_length=50)
    location: Optional[str] = Field(default=None, max_length=255)
    summary: Optional[str] = Field(default=None)


