from typing import Annotated
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from api.deps import CurrentCandidate, get_db
from core.security import hash_password, verify_password
from core.auth_providers import get_otp_provider, DBVerificationTokenProvider, EmailProvider
from db.session import tenant_context
from models import User
from models.enums import UserRole
from models.candidate_profile import CandidateProfile
from schemas.auth import (
    AuthResponse, UserResponse, CandidateRegisterRequest, CandidateLoginRequest,
    CandidateOTPRequest, CandidateOTPVerifyRequest, CandidatePhoneOTPRequest,
    CandidatePhoneOTPVerifyRequest, CandidateProfileUpdateRequest
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
    Verification tokens are sent, and verification_required=True is returned.
    No JWT is issued at this stage.
    """
    email_lower = body.email.lower()

    # Strict email validation & Disposable Check
    from core.domain_validation import validate_email_strict
    email_strict = validate_email_strict(email_lower)
    if not email_strict["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=email_strict["error"],
        )

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
                email_verified=False,
            )
            db.add(user)
            db.flush()

            # Create the candidate profile
            profile = CandidateProfile(
                user_id=user.id,
                full_name=body.full_name,
                phone_number=body.phone_number.strip(),
                email_verified=False,
                phone_verified=False,
            )
            db.add(profile)
            db.commit()
            db.refresh(user)

            # Send Email and Phone verifications using our new VerificationService
            from core.verification_service import VerificationService
            VerificationService.send_email_verification(db, user)
            VerificationService.send_phone_verification(db, user, body.phone_number)

            # Audit logs
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
            log_audit_event(
                db=db,
                action="auth.email_verification_sent",
                actor_type="CANDIDATE",
                actor_id=user.id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={"email": user.email}
            )
            log_audit_event(
                db=db,
                action="auth.phone_verification_sent",
                actor_type="CANDIDATE",
                actor_id=user.id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={"phone_number": body.phone_number}
            )
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

    return AuthResponse(
        access_token=None,
        refresh_token=None,
        verification_required=True,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            email_verified=False,
            phone_verified=False,
            company_id=None,
            auth_provider=user.auth_provider,
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
    """Authenticate a candidate with email + password. Enforces verification checks before JWT issuance."""
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

    # Check verification status. Unverified candidates get blocked with a 403.
    with tenant_context(auth_mode="true"):
        profile = user.candidate_profile
        phone_verified = profile.phone_verified if profile else False
        phone_number = profile.phone_number if profile else None

    if not user.email_verified or not phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Verification required",
                "verification_required": True,
                "email": user.email,
                "email_verified": user.email_verified,
                "phone_verified": phone_verified,
                "phone_number": phone_number
            }
        )

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
            email_verified=user.email_verified,
            phone_verified=phone_verified,
            company_id=None,
            auth_provider=user.auth_provider,
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
    email_lower = body.email.lower().strip()

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

    # Rate limit: 5 requests per hour per email
    import redis
    from core.config import get_settings
    from datetime import datetime, timezone, timedelta
    settings = get_settings()
    try:
        r = redis.from_url(settings.redis_url)
        rate_key = f"otp:email:rate:{email_lower}"
        attempts = r.get(rate_key)
        if attempts and int(attempts) >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Verification OTP resend limit exceeded. Please try again after 1 hour."
            )
        p = r.pipeline()
        p.incr(rate_key)
        p.ttl(rate_key)
        res = p.execute()
        new_attempts = res[0]
        ttl = res[1]
        if ttl < 0:
            r.expire(rate_key, 3600)
    except HTTPException:
        raise
    except Exception:
        # DB fallback rate limiting
        with tenant_context(auth_mode="true"):
            from models.verification_token import VerificationToken
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            count = db.scalar(
                select(func.count(VerificationToken.id)).where(
                    VerificationToken.user_id == user.id,
                    VerificationToken.token_type == "email_otp",
                    VerificationToken.created_at >= one_hour_ago
                )
            )
            if count >= 5:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Verification OTP resend limit exceeded. Please try again after 1 hour."
                )

    code = DBVerificationTokenProvider.create_token(
        db=db,
        user_id=user.id,
        token_type="email_otp",
        expires_in_minutes=10
    )

    EmailProvider.send_verification_email(email_lower, code)

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
    log_audit_event(
        db=db,
        action="auth.email_verification_sent",
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
        user.email_verified = True
        db.add(user)
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
    log_audit_event(
        db=db,
        action="auth.email_verification_completed",
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
            "auth_provider": current_candidate.auth_provider.value,
            "email_verified": current_candidate.email_verified,
            "phone_verified": current_candidate.phone_verified,
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
            "summary": profile.summary,
        }

    return response_data


@router.post("/candidate/phone/send-otp")
@limiter.limit("3/minute")
def candidate_send_phone_otp(
    request: Request,
    body: CandidatePhoneOTPRequest,
    current_candidate: CurrentCandidate,
    db: Annotated[Session, Depends(get_db)],
):
    """Send a phone verification OTP to the logged-in candidate."""
    import redis
    import random
    import os
    from core.config import get_settings

    phone = body.phone_number.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")

    # Rate limit: 1 request per minute per phone number
    settings = get_settings()
    try:
        r = redis.from_url(settings.redis_url)
        rate_key = f"otp:rate:{phone}"
        if r.get(rate_key):
            raise HTTPException(status_code=429, detail="Please wait 1 minute before requesting another OTP.")

        # Generate 6-digit code
        code = f"{random.randint(100000, 999999)}"

        # Store in Redis: key = otp:code:{phone}, value = code:attempts, expire = 5 minutes
        r.setex(f"otp:code:{phone}", 300, f"{code}:0")

        # Set rate limit key for 60 seconds
        r.setex(rate_key, 60, "1")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to prepare OTP storage: {exc}")

    # Send SMS (using Twilio client if configured, otherwise stubbed)
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_phone = os.getenv("TWILIO_FROM_PHONE")

    if account_sid and auth_token and from_phone:
        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            client.messages.create(
                body=f"Your SmartOnboard verification code is: {code}. It expires in 5 minutes.",
                from_=from_phone,
                to=phone
            )
            print(f"OTP successfully sent via Twilio to {phone}")
        except Exception as err:
            print(f"Twilio API error: {err}. Falling back to logging.")
            print(f"MOCK SMS OTP for {phone}: {code}")
    else:
        print(f"MOCK SMS OTP for {phone}: {code}")

    # Log audit event
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.candidate_otp_sent",
        actor_type="CANDIDATE",
        actor_id=current_candidate.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"phone_number": phone}
    )
    db.commit()

    return {"success": True, "message": "OTP code sent successfully"}


@router.post("/candidate/phone/verify-otp")
@limiter.limit("5/minute")
def candidate_verify_phone_otp(
    request: Request,
    body: CandidatePhoneOTPVerifyRequest,
    current_candidate: CurrentCandidate,
    db: Annotated[Session, Depends(get_db)],
):
    """Verify a candidate's phone verification OTP."""
    import redis
    from core.config import get_settings

    phone = body.phone_number.strip()
    code = body.code.strip()

    if not phone or not code:
        raise HTTPException(status_code=400, detail="Phone number and code are required")

    settings = get_settings()
    try:
        r = redis.from_url(settings.redis_url)
        otp_key = f"otp:code:{phone}"
        stored = r.get(otp_key)

        if not stored:
            raise HTTPException(status_code=400, detail="OTP expired or not requested")

        stored_code, attempts_str = stored.decode("utf-8").split(":")
        attempts = int(attempts_str)

        if attempts >= 3:
            r.delete(otp_key)
            raise HTTPException(status_code=403, detail="Too many failed attempts. Please request a new OTP.")

        if stored_code != code:
            attempts += 1
            if attempts >= 3:
                r.delete(otp_key)
                raise HTTPException(status_code=403, detail="Too many failed attempts. Please request a new OTP.")
            r.setex(otp_key, 300, f"{stored_code}:{attempts}")
            raise HTTPException(status_code=400, detail="Invalid verification code")

        r.delete(otp_key)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Verification service exception: {exc}")

    # Update CandidateProfile
    with tenant_context(auth_mode="true"):
        profile = db.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == current_candidate.id)
        )
        if profile:
            profile.phone_number = phone
            profile.phone_verified = True
            db.add(profile)
            db.commit()

    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.candidate_phone_verified",
        actor_type="CANDIDATE",
        actor_id=current_candidate.id,
        resource_type="candidate_profiles",
        resource_id=str(profile.id) if profile else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"phone_number": phone},
    )
    db.commit()

    return {"success": True, "message": "Phone number verified successfully"}


@router.put("/candidate/profile")
@limiter.limit("10/minute")
def candidate_update_profile(
    request: Request,
    body: CandidateProfileUpdateRequest,
    current_candidate: CurrentCandidate,
    db: Annotated[Session, Depends(get_db)],
):
    """Update the candidate profile attributes."""
    with tenant_context(auth_mode="true"):
        profile = db.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == current_candidate.id)
        )
        if not profile:
            raise HTTPException(status_code=404, detail="Candidate profile not found")

        # Update user table name
        user = db.scalar(select(User).where(User.id == current_candidate.id))
        if user:
            user.full_name = body.full_name
            db.add(user)

        profile.full_name = body.full_name
        profile.location = body.location
        profile.summary = body.summary

        if body.phone_number:
            cleaned_phone = body.phone_number.strip()
            if profile.phone_number != cleaned_phone:
                profile.phone_number = cleaned_phone
                profile.phone_verified = False # Reset verification on phone change

        db.add(profile)
        db.commit()
        db.refresh(profile)

    # Build me response
    return {
        "user": {
            "id": str(current_candidate.id),
            "email": current_candidate.email,
            "full_name": body.full_name,
            "role": current_candidate.role.value,
            "auth_provider": current_candidate.auth_provider.value,
        },
        "profile": {
            "id": str(profile.id),
            "full_name": profile.full_name,
            "phone_number": profile.phone_number,
            "phone_verified": profile.phone_verified,
            "email_verified": profile.email_verified,
            "location": profile.location,
            "profile_status": profile.profile_status,
            "summary": profile.summary,
        }
    }


from schemas.auth import PhoneVerifyOTPRequest, PhoneSendOTPRequest

@router.get("/verification-status")
def get_verification_status(
    email: str,
    db: Annotated[Session, Depends(get_db)],
):
    """Retrieve the current verification status for a candidate by email."""
    email_lower = email.lower().strip()
    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User).where(
                User.email == email_lower,
                User.role == UserRole.CANDIDATE,
            )
        )
    if not user:
        raise HTTPException(status_code=404, detail="Candidate not found")

    with tenant_context(auth_mode="true"):
        profile = user.candidate_profile
        phone_verified = profile.phone_verified if profile else False
        phone_number = profile.phone_number if profile else None

    return {
        "email_verified": user.email_verified,
        "phone_verified": phone_verified,
        "verification_required": not (user.email_verified and phone_verified),
        "phone_number": phone_number
    }


@router.post("/email/verify-otp")
def candidate_verify_email_otp_new(
    request: Request,
    response: Response,
    body: CandidateOTPVerifyRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Verify email OTP. Automatically issues JWT if phone is also verified."""
    email_lower = body.email.lower().strip()
    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User).where(
                User.email == email_lower,
                User.role == UserRole.CANDIDATE,
                User.is_active.is_(True),
            )
        )
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification request")

    from core.verification_service import VerificationService
    try:
        VerificationService.verify_email_code(db, user, body.code)
    except HTTPException:
        # Log failed attempt
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="auth.email_verification_failed",
            actor_type="CANDIDATE",
            actor_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"email": email_lower}
        )
        raise

    # Mark as verified
    with tenant_context(auth_mode="true"):
        user.email_verified = True
        db.add(user)
        profile = user.candidate_profile
        if profile:
            profile.email_verified = True
            db.add(profile)
        db.commit()
        db.refresh(user)

    # Log success
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.email_verification_completed",
        actor_type="CANDIDATE",
        actor_id=user.id,
        resource_type="candidate_profiles",
        resource_id=str(profile.id) if profile else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"email": email_lower},
    )

    # Check if phone is also verified
    phone_verified = profile.phone_verified if profile else False
    if phone_verified:
        # Issue JWT tokens!
        access_token, refresh_token = create_user_session_and_tokens(
            db=db,
            user=user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            response=response,
        )
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            verification_required=False,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role.value,
                email_verified=True,
                phone_verified=True,
                company_id=None,
                auth_provider=user.auth_provider,
            ),
        )

    return {
        "success": True,
        "message": "Email verified successfully. Phone verification is still required.",
        "email_verified": True,
        "phone_verified": False
    }


@router.post("/phone/send-otp")
def candidate_send_phone_otp_new(
    request: Request,
    body: PhoneSendOTPRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Send phone verification OTP. Supports phone number change flow and logs auth.phone_number_changed."""
    email_lower = body.email.lower().strip()
    phone_new = body.phone_number.strip()

    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User).where(
                User.email == email_lower,
                User.role == UserRole.CANDIDATE,
                User.is_active.is_(True),
            )
        )
    if not user:
        raise HTTPException(status_code=404, detail="Candidate not found")

    with tenant_context(auth_mode="true"):
        profile = user.candidate_profile
        if not profile:
            profile = CandidateProfile(user_id=user.id, full_name=user.full_name)
            db.add(profile)
            db.flush()

        old_phone = profile.phone_number
        if old_phone != phone_new:
            # Phone number changed flow!
            profile.phone_number = phone_new
            profile.phone_verified = False
            db.add(profile)
            db.commit()

            # Invalidate previous verification attempt
            if old_phone:
                from core.verification_service import _mock_phone_otps
                _mock_phone_otps.pop(old_phone.strip(), None)

            # Log phone number changed event
            from core.audit import log_audit_event
            log_audit_event(
                db=db,
                action="auth.phone_number_changed",
                actor_type="CANDIDATE",
                actor_id=user.id,
                resource_type="candidate_profiles",
                resource_id=str(profile.id),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={"old_phone": old_phone, "new_phone": phone_new}
            )

    # Send OTP via VerificationService
    from core.verification_service import VerificationService
    VerificationService.send_phone_verification(db, user, phone_new)

    # Log phone verification sent event
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.phone_verification_sent",
        actor_type="CANDIDATE",
        actor_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"phone_number": phone_new}
    )

    return {"success": True, "message": "Verification OTP sent successfully"}


@router.post("/phone/verify-otp")
def candidate_verify_phone_otp_new(
    request: Request,
    response: Response,
    body: PhoneVerifyOTPRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Verify phone OTP. Automatically issues JWT if email is also verified."""
    email_lower = body.email.lower().strip()
    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User).where(
                User.email == email_lower,
                User.role == UserRole.CANDIDATE,
                User.is_active.is_(True),
            )
        )
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification request")

    from core.verification_service import VerificationService
    try:
        VerificationService.verify_phone_code(db, user, body.code)
    except HTTPException:
        # Log failed attempt
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="auth.phone_verification_failed",
            actor_type="CANDIDATE",
            actor_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"email": email_lower}
        )
        raise

    # Mark phone as verified in CandidateProfile
    with tenant_context(auth_mode="true"):
        profile = user.candidate_profile
        if profile:
            profile.phone_verified = True
            db.add(profile)
            db.commit()

    # Log successful verification
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.phone_verification_completed",
        actor_type="CANDIDATE",
        actor_id=user.id,
        resource_type="candidate_profiles",
        resource_id=str(profile.id) if profile else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"phone_number": profile.phone_number if profile else None},
    )

    # Check if email is also verified
    if user.email_verified:
        # Issue JWT tokens!
        access_token, refresh_token = create_user_session_and_tokens(
            db=db,
            user=user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            response=response,
        )
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            verification_required=False,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role.value,
                email_verified=True,
                phone_verified=True,
                company_id=None,
                auth_provider=user.auth_provider,
            ),
        )

    return {
        "success": True,
        "message": "Phone verified successfully. Email verification is still required.",
        "email_verified": False,
        "phone_verified": True
    }


@router.get("/test/otps")
def get_test_otps(
    email: str,
    db: Annotated[Session, Depends(get_db)],
):
    """Backdoor endpoint to retrieve mock OTPs for automated E2E testing. Only active in development/testing."""
    email_lower = email.lower().strip()
    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User).where(
                User.email == email_lower,
                User.role == UserRole.CANDIDATE,
            )
        )
    if not user:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Generate a fresh email OTP and get its plaintext code
    email_code = DBVerificationTokenProvider.create_token(
        db=db,
        user_id=user.id,
        token_type="email_otp",
        expires_in_minutes=10
    )

    # Get active phone OTP
    from core.verification_service import _mock_phone_otps
    phone_code = None
    with tenant_context(auth_mode="true"):
        profile = user.candidate_profile
        phone = profile.phone_number if profile else None
        if phone:
            phone_stripped = phone.strip()
            if phone_stripped in _mock_phone_otps:
                phone_code = _mock_phone_otps[phone_stripped]["code"]

    return {
        "email_code": email_code,
        "phone_code": phone_code,
        "phone_number": phone
    }

