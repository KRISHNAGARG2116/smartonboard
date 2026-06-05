from typing import Annotated
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from api.deps import CurrentCandidate, get_db
from core.security import hash_password, verify_password
from core.auth_providers import get_otp_provider, DBVerificationTokenProvider
from db.session import tenant_context
from models import User
from models.enums import UserRole
from models.candidate_profile import CandidateProfile
from schemas.auth import (
    AuthResponse, UserResponse, CandidateRegisterRequest, CandidateLoginRequest,
    CandidateOTPRequest, CandidateOTPVerifyRequest
)
from core.limiter import limiter

# Import helpers from api.auth to avoid duplication and maintain compatibility
from api.auth import (
    is_ip_blocked, record_failed_login, clear_failed_logins,
    create_user_session_and_tokens
)

router = APIRouter(prefix="/auth", tags=["Candidate Authentication"])


@router.post("/register/candidate", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register_candidate(
    request: Request,
    response: Response,
    body: CandidateRegisterRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Register a new candidate account.

    Candidates have no company_id, no tenant context, and role=CANDIDATE.
    A CandidateProfile row is created alongside the User row.
    """
    email_lower = body.email.lower()

    try:
        with tenant_context(auth_mode="true"):
            existing = db.scalar(select(User.id).where(User.email == email_lower))
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered",
                )

            user = User(
                company_id=None,
                email=email_lower,
                password_hash=hash_password(body.password),
                full_name=body.full_name,
                role=UserRole.CANDIDATE,
            )
            db.add(user)
            db.flush()

            # Create the candidate profile
            profile = CandidateProfile(
                user_id=user.id,
                full_name=body.full_name,
                email_verified=False,
                phone_verified=False,
            )
            db.add(profile)
            db.commit()
            db.refresh(user)
    except IntegrityError as e:
        db.rollback()
        err_msg = str(e.orig).lower()
        if "email" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration failed due to a constraint violation",
        )

    access_token, refresh_token = create_user_session_and_tokens(
        db=db,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        response=response,
    )

    # Audit log
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.candidate_registered",
        actor_type="CANDIDATE",
        actor_id=user.id,
        resource_type="users",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"email": user.email},
    )

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_id=None,
        ),
    )


@router.post("/login/candidate", response_model=AuthResponse)
@limiter.limit("10/minute")
def login_candidate(
    request: Request,
    response: Response,
    body: CandidateLoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Authenticate a candidate with email + password."""
    dummy_hash = "$2b$12$L7p.yF7T24Q.8Wk7Qz9.4ux7R6j8q9b0n1o2p3q4r5s6t7u8v9w0x"
    ip = request.client.host if request.client else "127.0.0.1"

    if is_ip_blocked(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. This IP is temporarily locked out.",
        )

    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User).where(
                User.email == body.email.lower(),
                User.role == UserRole.CANDIDATE,
                User.is_active.is_(True),
            )
        )

    if user is None:
        record_failed_login(ip)
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="auth.candidate_login_failed",
            actor_type="UNAUTHENTICATED",
            ip_address=ip,
            user_agent=request.headers.get("user-agent"),
            metadata={"email": body.email, "event": "login_failed"},
        )
        verify_password(body.password, dummy_hash)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(body.password, user.password_hash):
        record_failed_login(ip)
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="auth.candidate_login_failed",
            actor_type="UNAUTHENTICATED",
            ip_address=ip,
            user_agent=request.headers.get("user-agent"),
            metadata={"email": body.email, "event": "login_failed"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    clear_failed_logins(ip)

    access_token, refresh_token = create_user_session_and_tokens(
        db=db,
        user=user,
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
        response=response,
    )

    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.candidate_login",
        actor_type="CANDIDATE",
        actor_id=user.id,
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
        metadata={"email": user.email},
    )

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_id=None,
        ),
    )


@router.post("/candidate/email/send-otp")
@limiter.limit("3/minute")
def candidate_send_email_otp(
    request: Request,
    body: CandidateOTPRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Send an email verification OTP to a candidate."""
    email_lower = body.email.lower()

    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User).where(
                User.email == email_lower,
                User.role == UserRole.CANDIDATE,
                User.is_active.is_(True),
            )
        )

    if not user:
        return {"success": True, "message": "If that email is registered, a verification code has been sent."}

    code = DBVerificationTokenProvider.create_token(
        db=db,
        user_id=user.id,
        token_type="email_otp",
    )

    provider = get_otp_provider()
    provider.send_otp(email_lower, code)

    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.candidate_email_otp_sent",
        actor_type="CANDIDATE",
        actor_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"email": email_lower},
    )

    return {"success": True, "message": "If that email is registered, a verification code has been sent."}


@router.post("/candidate/email/verify-otp")
@limiter.limit("5/minute")
def candidate_verify_email_otp(
    request: Request,
    body: CandidateOTPVerifyRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Verify an email OTP for a candidate and mark their email as verified."""
    email_lower = body.email.lower()

    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User).where(
                User.email == email_lower,
                User.role == UserRole.CANDIDATE,
                User.is_active.is_(True),
            )
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification request",
        )

    result = DBVerificationTokenProvider.verify_token(
        db=db,
        user_id=user.id,
        token_type="email_otp",
        code=body.code,
    )

    if not result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )

    with tenant_context(auth_mode="true"):
        profile = db.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == user.id)
        )
        if profile:
            profile.email_verified = True
            db.add(profile)
            db.commit()

    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.candidate_email_verified",
        actor_type="CANDIDATE",
        actor_id=user.id,
        resource_type="candidate_profiles",
        resource_id=str(profile.id) if profile else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"email": email_lower},
    )

    return {"success": True, "message": "Email verified successfully"}


@router.get("/candidate/me")
@limiter.limit("100/minute")
def candidate_me(
    request: Request,
    current_candidate: CurrentCandidate,
    db: Annotated[Session, Depends(get_db)],
):
    """Get the current candidate's profile information."""
    with tenant_context(auth_mode="true"):
        profile = db.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == current_candidate.id)
        )

    response_data = {
        "user": {
            "id": str(current_candidate.id),
            "email": current_candidate.email,
            "full_name": current_candidate.full_name,
            "role": current_candidate.role.value,
        },
        "profile": None,
    }

    if profile:
        response_data["profile"] = {
            "id": str(profile.id),
            "full_name": profile.full_name,
            "phone_number": profile.phone_number,
            "phone_verified": profile.phone_verified,
            "email_verified": profile.email_verified,
            "location": profile.location,
            "profile_status": profile.profile_status,
        }

    return response_data
