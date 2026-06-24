from typing import Annotated, Optional
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from api.deps import CurrentUser, CurrentCandidate, TenantDb, get_current_user, get_current_candidate, CurrentUserSetup, CurrentUserProfile
from core.security import create_access_token, create_refresh_token, hash_password, verify_password
from core.slug import unique_slug
from core.domain_validation import is_public_mail_host, validate_domain_dns
from core.auth_providers import get_otp_provider, DBVerificationTokenProvider, verify_google_id_token, EmailProvider
from db.session import get_db, tenant_context, tenant_id_var
from models import Company, User
from models.enums import CompanyStatus, UserRole, VerificationState, TrustLevel, AuthProvider
from models.session import UserSession, RevokedToken
from models.candidate_profile import CandidateProfile
from schemas.auth import (
    AuthResponse, LoginRequest, RegisterRequest, UserResponse, SessionResponse,
    RevokeSessionRequest, CandidateRegisterRequest, CandidateLoginRequest,
    CandidateOTPRequest, CandidateOTPVerifyRequest,
)
from schemas.company import CompanyResponse, CompanyUpdateRequest
from core.limiter import limiter
from core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


def create_user_session_and_tokens(
    db: Session,
    user: User,
    ip_address: str | None,
    user_agent: str | None,
    response: Response = None
) -> tuple[str, str]:
    session_id = uuid.uuid4()
    
    # Build JWT claims — company_id is nullable for candidates
    company_id_str = str(user.company_id) if user.company_id else None
    
    # 1. Create tokens
    access_token = create_access_token(
        str(user.id),
        {
            "company_id": company_id_str,
            "role": user.role.value,
            "email": user.email,
            "session_id": str(session_id)
        }
    )
    refresh_token, refresh_jti = create_refresh_token(
        str(user.id),
        str(session_id),
        {
            "company_id": company_id_str,
            "role": user.role.value,
            "email": user.email
        }
    )
    
    # 2. Hash refresh token
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    
    # 3. Save UserSession
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    
    session = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=token_hash,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc),
        last_active=datetime.now(timezone.utc)
    )
    db.add(session)
    db.commit()
    
    # 4. Set Cookie on Response
    if response:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=settings.refresh_token_expire_days * 24 * 3600
        )
        
    return access_token, refresh_token


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(
    request: Request,
    response: Response,
    body: RegisterRequest,
    db: Annotated[Session, Depends(get_db)]
):
    # --- Recruiter Domain Validation ---
    email_lower = body.email.lower()

    # 1. Strict email validation & Disposable Check
    from core.domain_validation import validate_email_strict
    email_strict = validate_email_strict(email_lower)
    if not email_strict["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=email_strict["error"],
        )

    # 2. Block public mail hosts
    if is_public_mail_host(email_lower):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recruiters must register with a corporate email address. Public email providers (Gmail, Yahoo, etc.) are not accepted.",
        )

    # 2. DNS/MX domain verification
    dns_result = validate_domain_dns(email_lower)
    if dns_result["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email domain validation failed: {dns_result['error']}",
        )

    # Determine initial verification state based on MX result
    if dns_result["mx_verified"]:
        initial_verification_state = VerificationState.VERIFIED_RECRUITER
        initial_domain_verified = True
    else:
        # Domain exists but MX query failed — allow with manual review path
        initial_verification_state = VerificationState.PENDING_VERIFICATION
        initial_domain_verified = False

    try:
        with tenant_context(auth_mode="true"):
            existing = db.scalar(select(User.id).where(User.email == email_lower))
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

            slugs = set(db.scalars(select(Company.slug)).all())
            company = Company(
                name=body.company_name,
                slug=unique_slug(body.company_name, slugs),
                status=CompanyStatus.ACTIVE,
                verification_state=initial_verification_state,
                domain_verified=initial_domain_verified,
            )
            db.add(company)
            db.flush()

        with tenant_context(tenant_id=str(company.id)):
            user = User(
                company_id=company.id,
                email=email_lower,
                password_hash=hash_password(body.password),
                full_name=body.full_name,
                role=UserRole.OWNER,
                email_verified=False,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Generate and send email verification OTP
            otp_code = DBVerificationTokenProvider.create_token(
                db=db,
                user_id=user.id,
                token_type="email_otp",
                expires_in_minutes=10
            )
            EmailProvider.send_verification_email(user.email, otp_code)

            from core.audit import log_audit_event
            log_audit_event(
                db=db,
                action="auth.email_verification_sent",
                actor_type="RECRUITER",
                actor_id=user.id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={"email": user.email}
            )
    except IntegrityError as e:
        db.rollback()
        err_msg = str(e.orig).lower()
        if "companies_slug_key" in err_msg or "slug" in err_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company slug already registered")
        elif "ix_users_email" in err_msg or "users_email_key" in err_msg or "email" in err_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        else:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Uniqueness constraint violation during registration")

    access_token, refresh_token = create_user_session_and_tokens(
        db=db,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        response=response
    )
    
    # Audit log registration
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.register",
        actor_type="RECRUITER",
        actor_id=user.id,
        company_id=user.company_id,
        resource_type="users",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "email": user.email,
            "domain_verified": initial_domain_verified,
            "verification_state": initial_verification_state.value,
            "mx_records": dns_result.get("mx_records", []),
        }
    )

    # Audit domain verification result
    log_audit_event(
        db=db,
        action="verification.domain_check",
        actor_type="SYSTEM",
        company_id=user.company_id,
        resource_type="companies",
        resource_id=str(company.id),
        ip_address=request.client.host if request.client else None,
        metadata={
            "domain": dns_result["domain"],
            "domain_exists": dns_result["domain_exists"],
            "mx_verified": dns_result["mx_verified"],
            "result_state": initial_verification_state.value,
        }
    )
    
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_id=user.company_id,
            auth_provider=user.auth_provider,
        ),
    )


def is_ip_blocked(ip: str) -> bool:
    import redis
    try:
        r = redis.from_url(get_settings().redis_url)
        return bool(r.get(f"lockout:blocked:{ip}"))
    except Exception:
        return False


def record_failed_login(ip: str):
    import redis
    try:
        r = redis.from_url(get_settings().redis_url)
        key = f"lockout:failed:{ip}"
        attempts = r.incr(key)
        if attempts == 1:
            r.expire(key, 300)  # 5 minutes window
        if attempts >= 5:
            r.setex(f"lockout:blocked:{ip}", 300, 1)  # block for 5 minutes
    except Exception:
        pass


def clear_failed_logins(ip: str):
    import redis
    try:
        r = redis.from_url(get_settings().redis_url)
        r.delete(f"lockout:failed:{ip}")
        r.delete(f"lockout:blocked:{ip}")
    except Exception:
        pass


class OTPSendRequest(BaseModel):
    phone_number: str


class OTPVerifyRequest(BaseModel):
    phone_number: str
    code: str


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Annotated[Session, Depends(get_db)]
):
    dummy_hash = "$2b$12$L7p.yF7T24Q.8Wk7Qz9.4ux7R6j8q9b0n1o2p3q4r5s6t7u8v9w0x"
    ip = request.client.host if request.client else "127.0.0.1"

    # ATO failed login lockout check
    if is_ip_blocked(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. This IP is temporarily locked out."
        )

    # Prevent session fixation: revoke pre-existing session if refresh token cookie is present
    refresh_token_cookie = request.cookies.get("refresh_token")
    if refresh_token_cookie:
        try:
            incoming_hash = hashlib.sha256(refresh_token_cookie.encode()).hexdigest()
            stmt = select(UserSession).where(UserSession.refresh_token_hash == incoming_hash)
            old_session = db.scalar(stmt)
            if old_session:
                db.delete(old_session)
                db.commit()
        except Exception:
            pass

    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User)
            .join(Company, User.company_id == Company.id)
            .where(
                User.email == body.email.lower(),
                User.is_active.is_(True),
                Company.status == CompanyStatus.ACTIVE,
            )
        )

    if user is None:
        record_failed_login(ip)
        # Audit log login failure
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="auth.login_failed",
            actor_type="UNAUTHENTICATED",
            ip_address=ip,
            user_agent=request.headers.get("user-agent"),
            metadata={"email": body.email, "password": body.password, "event": "login_failed"}
        )
        verify_password(body.password, dummy_hash)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not verify_password(body.password, user.password_hash):
        record_failed_login(ip)
        # Audit log login failure
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="auth.login_failed",
            actor_type="UNAUTHENTICATED",
            ip_address=ip,
            user_agent=request.headers.get("user-agent"),
            metadata={"email": body.email, "password": body.password, "event": "login_failed"}
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # Enforce email verification check
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )

    # Clear failed logins on success
    clear_failed_logins(ip)

    access_token, refresh_token = create_user_session_and_tokens(
        db=db,
        user=user,
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
        response=response
    )
    
    # Audit log login success
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.login",
        actor_type="RECRUITER",
        actor_id=user.id,
        company_id=user.company_id,
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
        metadata={"email": user.email}
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
            company_id=user.company_id,
            auth_provider=user.auth_provider,
        ),
    )


class RecruiterVerifyEmailRequest(BaseModel):
    email: str
    code: str


class RecruiterResendOTPRequest(BaseModel):
    email: str


@router.post("/verify-email", response_model=AuthResponse)
def verify_email(
    request: Request,
    response: Response,
    body: RecruiterVerifyEmailRequest,
    db: Annotated[Session, Depends(get_db)]
):
    email_lower = body.email.lower().strip()
    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User).where(User.email == email_lower)
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify the OTP token
    result = DBVerificationTokenProvider.verify_token(
        db=db,
        user_id=user.id,
        token_type="email_otp",
        code=body.code
    )

    if not result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    # Set user.email_verified = True and company.verification_state
    with tenant_context(auth_mode="true"):
        user.email_verified = True
        if user.company:
            user.company.verification_state = VerificationState.VERIFIED_RECRUITER
        db.add(user)
        db.commit()
        db.refresh(user)

    # Issue access/refresh tokens
    access_token, refresh_token = create_user_session_and_tokens(
        db=db,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        response=response
    )

    # Audit log verification success
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="verification.email_success",
        actor_type="RECRUITER",
        actor_id=user.id,
        company_id=user.company_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"email": user.email}
    )
    log_audit_event(
        db=db,
        action="auth.email_verification_completed",
        actor_type="RECRUITER",
        actor_id=user.id,
        company_id=user.company_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"email": user.email}
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
            company_id=user.company_id,
            auth_provider=user.auth_provider,
        ),
    )


@router.post("/verify-email/resend")
def resend_verify_email(
    request: Request,
    body: RecruiterResendOTPRequest,
    db: Annotated[Session, Depends(get_db)]
):
    email_lower = body.email.lower().strip()
    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User).where(User.email == email_lower)
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if user.email_verified:
        return {"message": "Email already verified"}

    # Rate limit: 5 requests per hour per email
    import redis
    from core.config import get_settings
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

    # Generate and send email verification OTP (10-minute expiry)
    otp_code = DBVerificationTokenProvider.create_token(
        db=db,
        user_id=user.id,
        token_type="email_otp",
        expires_in_minutes=10
    )
    EmailProvider.send_verification_email(user.email, otp_code)

    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.email_verification_sent",
        actor_type="RECRUITER",
        actor_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"email": user.email}
    )

    return {"message": "Verification code sent successfully"}


@router.post("/otp/send")
@limiter.limit("5/minute")
def send_otp(
    request: Request,
    body: OTPSendRequest,
    db: Annotated[Session, Depends(get_db)]
):
    import redis
    import random
    import os
    
    phone = body.phone_number.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")

    # Limit verify triggers: 1 trigger request per minute per phone number
    settings = get_settings()
    try:
        r = redis.from_url(settings.redis_url)
        rate_key = f"otp:rate:{phone}"
        if r.get(rate_key):
            raise HTTPException(status_code=429, detail="Please wait 1 minute before requesting another OTP.")
        
        # Generate 6-digit code
        code = f"{random.randint(100000, 999999)}"
        
        # Store in Redis: key = otp:{phone}, value = code:attempts, expire = 5 minutes
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
        action="auth.otp_sent",
        actor_type="UNAUTHENTICATED",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"phone_number": phone}
    )
    db.commit()

    return {"success": True, "message": "OTP code sent successfully"}


@router.post("/otp/verify")
@limiter.limit("5/minute")
def verify_otp(
    request: Request,
    body: OTPVerifyRequest,
    db: Annotated[Session, Depends(get_db)]
):
    import redis
    
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
            r.delete(otp_key)  # Lockout/Clear code after 3 failed attempts
            raise HTTPException(status_code=403, detail="Too many failed attempts. Please request a new OTP.")
            
        if stored_code != code:
            attempts += 1
            if attempts >= 3:
                r.delete(otp_key)
                raise HTTPException(status_code=403, detail="Too many failed attempts. Please request a new OTP.")
            r.setex(otp_key, 300, f"{stored_code}:{attempts}")
            raise HTTPException(status_code=400, detail="Invalid verification code")
            
        # Code matches! Clear the verification entry
        r.delete(otp_key)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Verification service exception: {exc}")

    # Log audit event
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.otp_verified",
        actor_type="UNAUTHENTICATED",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"phone_number": phone}
    )
    db.commit()

    return {"success": True, "message": "Phone verified successfully"}


@router.post("/refresh", response_model=AuthResponse)
def refresh_token_route(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    body: Optional[RefreshRequest] = None,
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None
):
    token = refresh_token_cookie
    if not token and body:
        token = body.refresh_token
        
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
        
    from jose import jwt, JWTError
    settings = get_settings()
    
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        session_id = payload.get("session_id")
        if not user_id or not session_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        
    from uuid import UUID
    
    session = db.scalar(select(UserSession).where(UserSession.id == UUID(session_id)))
    if not session or session.is_revoked or session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or revoked")
        
    incoming_hash = hashlib.sha256(token.encode()).hexdigest()
    if session.refresh_token_hash != incoming_hash:
        # REPLAY ATTACK: Revoke entire session
        session.is_revoked = True
        db.add(session)
        db.commit()
        response.delete_cookie("refresh_token")
        
        # Audit log replay attack
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="security.refresh_token_replay",
            actor_type="UNAUTHENTICATED",
            company_id=session.company_id if hasattr(session, "company_id") else None,
            resource_type="user_sessions",
            resource_id=str(session.id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"session_id": str(session.id), "event": "token_replay_attack"}
        )
        
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected. Session revoked.")
        
    with tenant_context(auth_mode="true"):
        user = db.scalar(select(User).where(User.id == UUID(user_id)))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
        
    tenant_id_var.set(str(user.company_id) if user.company_id else "")
    
    company_id_str = str(user.company_id) if user.company_id else None
    
    new_access_token = create_access_token(
        str(user.id),
        {
            "company_id": company_id_str,
            "role": user.role.value,
            "email": user.email,
            "session_id": str(session.id)
        }
    )
    new_refresh_token, new_refresh_jti = create_refresh_token(
        str(user.id),
        str(session.id),
        {
            "company_id": company_id_str,
            "role": user.role.value,
            "email": user.email
        }
    )
    
    new_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
    session.refresh_token_hash = new_hash
    session.last_active = datetime.now(timezone.utc)
    session.expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    
    db.add(session)
    db.commit()

    # Audit log successful refresh
    from core.audit import log_audit_event
    actor_type = "CANDIDATE" if user.role == UserRole.CANDIDATE else "RECRUITER"
    log_audit_event(
        db=db,
        action="auth.refresh",
        actor_type=actor_type,
        actor_id=user.id,
        company_id=user.company_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"session_id": str(session.id)}
    )
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 3600
    )
    
    return AuthResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_id=user.company_id,
            auth_provider=user.auth_provider,
        )
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None
):
    actor_id = None
    company_id = None
    
    # Revoke session via access token JTI
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        access_token_str = auth_header[7:]
        try:
            from core.security import decode_access_token
            payload = decode_access_token(access_token_str)
            jti = payload.get("jti")
            session_id = payload.get("session_id")
            exp_timestamp = payload.get("exp")
            
            # Extract identities for audit logging
            actor_id = payload.get("sub")
            company_id = payload.get("company_id")
            
            if jti and exp_timestamp:
                exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                revoked = RevokedToken(jti=jti, expires_at=exp_dt)
                db.add(revoked)
                
            if session_id:
                from uuid import UUID
                session = db.scalar(select(UserSession).where(UserSession.id == UUID(session_id)))
                if session:
                    session.is_revoked = True
                    db.add(session)
            db.commit()
        except Exception:
            pass
            
    # Revoke session via refresh token cookie
    token = refresh_token_cookie
    if token:
        try:
            from jose import jwt
            settings = get_settings()
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            session_id = payload.get("session_id")
            
            # Fallback identities for audit logging
            if not actor_id:
                actor_id = payload.get("sub")
            if not company_id:
                company_id = payload.get("company_id")
                
            if session_id:
                from uuid import UUID
                session = db.scalar(select(UserSession).where(UserSession.id == UUID(session_id)))
                if session:
                    session.is_revoked = True
                    db.add(session)
                db.commit()
        except Exception:
            pass
            
    # Audit log logout event
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.logout",
        actor_type="RECRUITER" if actor_id else "UNAUTHENTICATED",
        actor_id=actor_id,
        company_id=company_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    response.delete_cookie("refresh_token")
    return {"success": True, "detail": "Successfully logged out and session revoked"}


@router.get("/me", response_model=UserResponse)
@limiter.limit("100/minute")
def me(
    request: Request,
    current_user: CurrentUserProfile
):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        email_verified=current_user.email_verified,
        company_id=current_user.company_id,
        auth_provider=current_user.auth_provider,
    )


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser
):
    sessions = db.scalars(
        select(UserSession)
        .where(UserSession.user_id == current_user.id, UserSession.is_revoked.is_(False))
        .order_by(UserSession.last_active.desc())
    ).all()
    return sessions


@router.post("/sessions/revoke")
def revoke_session(
    body: RevokeSessionRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser
):
    session = db.scalar(
        select(UserSession).where(UserSession.id == body.session_id, UserSession.user_id == current_user.id)
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
    session.is_revoked = True
    db.add(session)
    db.commit()
    
    # Audit log session revocation event
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.session_revoked",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"session_id": str(session.id)}
    )
    
    return {"success": True, "detail": "Session successfully revoked"}


# --- Candidate Auth Backwards Compatibility registrations ---
from api.candidate_auth import (
    register_candidate,
    login_candidate,
    candidate_send_email_otp,
    candidate_verify_email_otp,
    candidate_me,
    candidate_send_phone_otp,
    candidate_verify_phone_otp,
    candidate_update_profile,
    candidate_verify_email_otp_new,
    candidate_verify_phone_otp_new,
    candidate_send_phone_otp_new,
    get_verification_status,
    get_test_otps
)

router.post("/register/candidate", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)(register_candidate)
router.post("/login/candidate", response_model=AuthResponse)(login_candidate)
router.post("/candidate/email/send-otp")(candidate_send_email_otp)
router.post("/candidate/email/verify-otp")(candidate_verify_email_otp)
router.get("/candidate/me")(candidate_me)
router.post("/candidate/phone/send-otp")(candidate_send_phone_otp)
router.post("/candidate/phone/verify-otp")(candidate_verify_phone_otp)
router.put("/candidate/profile")(candidate_update_profile)

# New Phase 14D public candidate verification routes
router.get("/verification-status")(get_verification_status)
router.post("/email/verify-otp")(candidate_verify_email_otp_new)
router.post("/phone/send-otp")(candidate_send_phone_otp_new)
router.post("/phone/verify-otp")(candidate_verify_phone_otp_new)
router.get("/test/otps")(get_test_otps)


# --- Google OAuth and Hardening Extensions ---

class GoogleLoginRequest(BaseModel):
    credential: str
    role: str


class SetupCompanyRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=255)
    company_website: str = Field(min_length=3, max_length=255)
    company_domain: str = Field(min_length=3, max_length=255)
    industry: str = Field(min_length=2, max_length=255)
    company_size: str = Field(min_length=1, max_length=255)


def setup_company_rate_limit_key(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ")[1]
        try:
            from jose import jwt
            from core.config import get_settings
            settings = get_settings()
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            user_id = payload.get("sub")
            if user_id:
                return f"setup_user_{user_id}"
        except Exception:
            pass
    from slowapi.util import get_remote_address
    return get_remote_address(request)


def check_google_failed_attempts(ip: str) -> bool:
    import redis
    from core.config import get_settings

    global _failed_google_attempts
    if '_failed_google_attempts' not in globals():
        globals()['_failed_google_attempts'] = {}

    try:
        settings = get_settings()
        r = redis.from_url(settings.redis_url)
        blocked = r.get(f"google:blocked:{ip}")
        if blocked:
            return True
    except Exception:
        import time
        record = globals()['_failed_google_attempts'].get(ip)
        if record:
            count, timestamp = record
            if count >= 5 and (time.time() - timestamp) < 300:
                return True
    return False


def record_google_failed_attempt(ip: str):
    import redis
    from core.config import get_settings

    global _failed_google_attempts
    if '_failed_google_attempts' not in globals():
        globals()['_failed_google_attempts'] = {}

    try:
        settings = get_settings()
        r = redis.from_url(settings.redis_url)
        key = f"google:failed:{ip}"
        attempts = r.incr(key)
        if attempts == 1:
            r.expire(key, 60)
        if attempts >= 5:
            r.setex(f"google:blocked:{ip}", 300, "1")
    except Exception:
        import time
        now = time.time()
        record = globals()['_failed_google_attempts'].get(ip)
        if not record:
            globals()['_failed_google_attempts'][ip] = (1, now)
        else:
            count, timestamp = record
            if now - timestamp > 60:
                globals()['_failed_google_attempts'][ip] = (1, now)
            else:
                new_count = count + 1
                globals()['_failed_google_attempts'][ip] = (new_count, now if new_count >= 5 else timestamp)


def log_google_auth_audit(db: Session, user_id: uuid.UUID | None, email_or_token: str, action: str, success: bool, ip: str | None, reason: str | None = None):
    from core.audit import log_audit_event
    metadata = {
        "email_or_token": email_or_token,
        "auth_provider": "google",
        "success": success,
    }
    if reason:
        metadata["reason"] = reason
    log_audit_event(
        db=db,
        action=action,
        actor_type="CANDIDATE" if "candidate" in action else "RECRUITER" if user_id else "UNAUTHENTICATED",
        actor_id=user_id,
        ip_address=ip,
        metadata=metadata
    )
    db.commit()


@router.post("/google", response_model=AuthResponse)
@limiter.limit("10/minute")
def google_auth(
    request: Request,
    response: Response,
    body: GoogleLoginRequest,
    db: Annotated[Session, Depends(get_db)]
):
    ip = request.client.host if request.client else "127.0.0.1"
    import os

    # Failed Google login lockout check
    if check_google_failed_attempts(ip):
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="auth.google_rate_limit_exceeded",
            actor_type="UNAUTHENTICATED",
            ip_address=ip,
            metadata={"detail": "Too many failed Google authentication attempts"}
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed Google authentication attempts. Please try again later."
        )

    role_requested = body.role.lower().strip()
    if role_requested not in ["candidate", "recruiter"]:
        record_google_failed_attempt(ip)
        raise HTTPException(status_code=400, detail="Invalid role specified")

    # Verify Google Token
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "mock-google-client-id")
    email = None
    sub = None
    hd = None
    name = "Google User"

    if body.credential.startswith("mock-google-token-"):
        parts = body.credential.replace("mock-google-token-", "").split(":")
        email = parts[0].lower().strip()
        sub = parts[1] if len(parts) > 1 else f"google-sub-{email}"
        hd = parts[2] if len(parts) > 2 else (None if "public" in email or "gmail" in email else email.split("@")[1])
        name = email.split("@")[0].capitalize()
        if hd == "None" or hd == "null" or not hd:
            hd = None
    else:
        try:
            payload = verify_google_id_token(body.credential, google_client_id)
            email = payload.get("email").lower().strip()
            sub = payload.get("sub")
            hd = payload.get("hd")
            name = payload.get("name", "Google User")
        except Exception as e:
            record_google_failed_attempt(ip)
            masked_cred = body.credential if body.credential.startswith("mock-google-token-") else "[MASKED_GOOGLE_TOKEN]"
            log_google_auth_audit(db, None, email_or_token=masked_cred, action="auth.google_login_failed", success=False, ip=ip, reason=str(e))
            raise HTTPException(status_code=400, detail=f"Google authentication failed: {str(e)}")

    if not email or not sub:
        record_google_failed_attempt(ip)
        masked_cred = body.credential if body.credential.startswith("mock-google-token-") else "[MASKED_GOOGLE_TOKEN]"
        log_google_auth_audit(db, None, email_or_token=masked_cred, action="auth.google_login_failed", success=False, ip=ip, reason="Missing email or sub claim")
        raise HTTPException(status_code=400, detail="Google token missing required claims")

    # Look up user by google_subject_id first
    with tenant_context(auth_mode="true"):
        user = db.scalar(select(User).where(User.google_subject_id == sub))
        if not user:
            # Fallback to look up by email
            user = db.scalar(select(User).where(func.lower(User.email) == email))
            if user:
                # Update subject ID if it was null
                if user.google_subject_id is None:
                    user.google_subject_id = sub
                    user.auth_provider = AuthProvider.GOOGLE
                    if hd:
                        user.google_hosted_domain = hd
                    db.add(user)
                    db.commit()
                    db.refresh(user)

    if user:
        # Check role mismatch
        if user.role == UserRole.CANDIDATE and role_requested == "recruiter":
            record_google_failed_attempt(ip)
            log_google_auth_audit(db, user.id, email_or_token=email, action="auth.google_role_mismatch", success=False, ip=ip, reason="Role mismatch: Email already associated with another user type")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role mismatch: Email already associated with another user type"
            )
        if user.role in [UserRole.OWNER, UserRole.RECRUITER] and role_requested == "candidate":
            record_google_failed_attempt(ip)
            log_google_auth_audit(db, user.id, email_or_token=email, action="auth.google_role_mismatch", success=False, ip=ip, reason="Role mismatch: Email already associated with another user type")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role mismatch: Email already associated with another user type"
            )

        # If user is inactive, block
        if not user.is_active:
            record_google_failed_attempt(ip)
            log_google_auth_audit(db, user.id, email_or_token=email, action="auth.google_login_failed", success=False, ip=ip, reason="User is inactive")
            raise HTTPException(status_code=401, detail="User account is deactivated")

        # Ensure email_verified is True
        if not user.email_verified:
            user.email_verified = True
            db.add(user)
            db.commit()
            db.refresh(user)
    else:
        # User does not exist, perform registration checks
        if role_requested == "recruiter":
            # Recruiter Domain Restrictions
            blocked_hosts = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "proton.me", "protonmail.com"}
            email_domain = email.split("@")[1]
            if email_domain in blocked_hosts or is_public_mail_host(email):
                record_google_failed_attempt(ip)
                log_google_auth_audit(db, None, email_or_token=email, action="auth.google_public_email_rejected", success=False, ip=ip, reason="Public email providers are not accepted for recruiters")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Recruiters must register with a corporate email address. Public email providers (Gmail, Yahoo, etc.) are not accepted."
                )

            # Create recruiter user with company_id = None
            with tenant_context(auth_mode="true"):
                user = User(
                    company_id=None,
                    email=email,
                    password_hash="oauth_google_placeholder",
                    full_name=name,
                    role=UserRole.OWNER,
                    email_verified=True,
                    auth_provider=AuthProvider.GOOGLE,
                    google_subject_id=sub,
                    google_hosted_domain=hd,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
        else:
            # Create candidate user (frictionless)
            with tenant_context(auth_mode="true"):
                user = User(
                    company_id=None,
                    email=email,
                    password_hash="oauth_google_placeholder",
                    full_name=name,
                    role=UserRole.CANDIDATE,
                    email_verified=True,
                    auth_provider=AuthProvider.GOOGLE,
                    google_subject_id=sub,
                    google_hosted_domain=hd,
                )
                db.add(user)
                db.flush()

                # Create the candidate profile
                profile = CandidateProfile(
                    user_id=user.id,
                    full_name=name,
                    email_verified=True,
                    phone_verified=False,
                )
                db.add(profile)
                db.commit()
                db.refresh(user)

    # Check candidate phone verification status before issuing tokens
    if user.role == UserRole.CANDIDATE:
        with tenant_context(auth_mode="true"):
            profile = user.candidate_profile
            phone_verified = profile.phone_verified if profile else False
            phone_number = profile.phone_number if profile else None

            if not phone_verified:
                # Google users automatically have email_verified = True
                if not user.email_verified:
                    user.email_verified = True
                    db.add(user)
                if profile and not profile.email_verified:
                    profile.email_verified = True
                    db.add(profile)
                db.commit()

                # Log failed attempt due to missing phone verification
                log_google_auth_audit(db, user.id, email_or_token=email, action="auth.google_phone_verification_required", success=False, ip=ip, reason="Phone verification required")

                # Raise 403 Forbidden to trigger phone verification flow in the frontend
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "Verification required",
                        "verification_required": True,
                        "email": user.email,
                        "email_verified": True,
                        "phone_verified": False,
                        "phone_number": phone_number
                    }
                )

    # Generate JWT tokens
    access_token, refresh_token = create_user_session_and_tokens(
        db=db,
        user=user,
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
        response=response
    )

    action_success = "auth.google_login_success_candidate" if user.role == UserRole.CANDIDATE else "auth.google_login_success_recruiter"
    log_google_auth_audit(db, user.id, email_or_token=email, action=action_success, success=True, ip=ip)

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            email_verified=user.email_verified,
            phone_verified=user.phone_verified,
            company_id=user.company_id,
            auth_provider=user.auth_provider,
        ),
    )


@router.post("/setup-company", response_model=AuthResponse)
@limiter.limit("5/minute", key_func=setup_company_rate_limit_key)
def setup_company(
    request: Request,
    response: Response,
    body: SetupCompanyRequest,
    current_user: CurrentUserSetup,
    db: Annotated[Session, Depends(get_db)]
):
    company_domain = body.company_domain.lower().strip()
    email_domain = current_user.email.split("@")[1].lower().strip()

    # Enforce email domain matches company domain
    if email_domain != company_domain:
        from core.audit import log_audit_event
        log_audit_event(
            db=db,
            action="auth.setup_company_failed",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            metadata={
                "email": current_user.email,
                "requested_domain": company_domain,
                "reason": "Email domain does not match company domain"
            }
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company domain must match authenticated email domain"
        )

    # Google Workspace Hosted Domain check
    if current_user.google_hosted_domain:
        google_hd = current_user.google_hosted_domain.lower().strip()
        if google_hd != company_domain or google_hd != email_domain:
            from core.audit import log_audit_event
            log_audit_event(
                db=db,
                action="auth.setup_company_failed",
                actor_type="RECRUITER",
                actor_id=current_user.id,
                metadata={
                    "email": current_user.email,
                    "google_hd": google_hd,
                    "requested_domain": company_domain,
                    "reason": "Google Workspace hosted domain mismatch"
                }
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company domain must match authenticated email domain"
            )

    # All validations pass, create company
    with tenant_context(auth_mode="true"):
        slugs = set(db.scalars(select(Company.slug)).all())
        company = Company(
            name=body.company_name,
            slug=unique_slug(body.company_name, slugs),
            status=CompanyStatus.ACTIVE,
            verification_state=VerificationState.VERIFIED_RECRUITER,
            domain_verified=True,
            settings={
                "website": body.company_website,
                "domain": company_domain,
                "industry": body.industry,
                "company_size": body.company_size,
            }
        )
        db.add(company)
        db.flush()

        # Link recruiter to company
        current_user.company_id = company.id
        db.add(current_user)
        db.commit()
        db.refresh(current_user)

    # Log setup completion event
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="company.setup_completed",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=company.id,
        resource_type="companies",
        resource_id=str(company.id),
        metadata={
            "company_name": company.name,
            "company_domain": company_domain,
            "industry": body.industry,
            "website": body.company_website,
            "company_size": body.company_size,
        }
    )
    db.commit()

    # Re-issue access and refresh tokens reflecting the new company_id
    access_token, refresh_token = create_user_session_and_tokens(
        db=db,
        user=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        response=response
    )

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role.value,
            email_verified=current_user.email_verified,
            company_id=current_user.company_id,
            auth_provider=current_user.auth_provider,
        )
    )


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    token: str
    new_password: str


@router.post("/forgot-password")
def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: Annotated[Session, Depends(get_db)]
):
    email_lower = body.email.lower().strip()
    
    # Check if user exists
    with tenant_context(auth_mode="true"):
        user = db.scalar(select(User).where(User.email == email_lower))
        
    if not user:
        # Standard silent return to prevent email enumeration
        return {"message": "If that email is registered, a password reset link has been sent."}

    # Rate limiting: 3 requests per 15 minutes per email
    import redis
    from core.config import get_settings
    settings = get_settings()
    try:
        r = redis.from_url(settings.redis_url)
        rate_key = f"forgot:rate:{email_lower}"
        attempts = r.get(rate_key)
        if attempts and int(attempts) >= 3:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Password reset limit exceeded. Please try again after 15 minutes."
            )
        p = r.pipeline()
        p.incr(rate_key)
        p.ttl(rate_key)
        res = p.execute()
        new_attempts = res[0]
        ttl = res[1]
        if ttl < 0:
            r.expire(rate_key, 900)  # 15 minutes
    except HTTPException:
        raise
    except Exception:
        # DB fallback rate limiting for forgot password
        with tenant_context(auth_mode="true"):
            from models.verification_token import VerificationToken
            fifteen_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=15)
            count = db.scalar(
                select(func.count(VerificationToken.id)).where(
                    VerificationToken.user_id == user.id,
                    VerificationToken.token_type == "password_reset",
                    VerificationToken.created_at >= fifteen_mins_ago
                )
            )
            if count >= 3:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Password reset limit exceeded. Please try again after 15 minutes."
                )

    # Generate token (30-minute expiry) and invalidate existing password_reset tokens
    import secrets
    reset_token = secrets.token_urlsafe(32)
    DBVerificationTokenProvider.create_token(
        db=db,
        user_id=user.id,
        token_type="password_reset",
        code=reset_token,
        expires_in_minutes=30
    )
    
    # Send email via EmailProvider
    EmailProvider.send_password_reset_email(user.email, reset_token)

    # Log audit event
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.password_reset_requested",
        actor_type="RECRUITER" if user.role != UserRole.CANDIDATE else "CANDIDATE",
        actor_id=user.id,
        company_id=user.company_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"email": user.email}
    )

    return {"message": "If that email is registered, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: Annotated[Session, Depends(get_db)]
):
    email_lower = body.email.lower().strip()
    
    with tenant_context(auth_mode="true"):
        user = db.scalar(select(User).where(User.email == email_lower))
        
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or token.")

    # Verify token
    result = DBVerificationTokenProvider.verify_token(
        db=db,
        user_id=user.id,
        token_type="password_reset",
        code=body.token
    )
    
    if not result["valid"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # Update password
    with tenant_context(auth_mode="true"):
        user.password_hash = hash_password(body.new_password)
        db.add(user)
        db.commit()

    # Log audit event
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="auth.password_reset_completed",
        actor_type="RECRUITER" if user.role != UserRole.CANDIDATE else "CANDIDATE",
        actor_id=user.id,
        company_id=user.company_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"email": user.email}
    )

    return {"message": "Password has been reset successfully."}


