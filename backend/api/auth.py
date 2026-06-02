from typing import Annotated, Optional
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from api.deps import CurrentUser, TenantDb, get_current_user
from core.security import create_access_token, create_refresh_token, hash_password, verify_password
from core.slug import unique_slug
from db.session import get_db, tenant_context, tenant_id_var
from models import Company, User
from models.enums import CompanyStatus, UserRole, VerificationState, TrustLevel
from models.session import UserSession, RevokedToken
from schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse, SessionResponse, RevokeSessionRequest
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
    
    # 1. Create tokens
    access_token = create_access_token(
        str(user.id),
        {
            "company_id": str(user.company_id),
            "role": user.role.value,
            "email": user.email,
            "session_id": str(session_id)
        }
    )
    refresh_token, refresh_jti = create_refresh_token(
        str(user.id),
        str(session_id),
        {
            "company_id": str(user.company_id),
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
    try:
        with tenant_context(auth_mode="true"):
            existing = db.scalar(select(User.id).where(User.email == body.email.lower()))
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

            slugs = set(db.scalars(select(Company.slug)).all())
            company = Company(
                name=body.company_name,
                slug=unique_slug(body.company_name, slugs),
                status=CompanyStatus.ACTIVE,
            )
            db.add(company)
            db.flush()

        with tenant_context(tenant_id=str(company.id)):
            user = User(
                company_id=company.id,
                email=body.email.lower(),
                password_hash=hash_password(body.password),
                full_name=body.full_name,
                role=UserRole.OWNER,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
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
            company_id=user.company_id,
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
            metadata={"email": body.email, "event": "login_failed"}
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
            metadata={"email": body.email, "event": "login_failed"}
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

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
            company_id=user.company_id,
        ),
    )


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
        
    tenant_id_var.set(str(user.company_id))
    
    new_access_token = create_access_token(
        str(user.id),
        {
            "company_id": str(user.company_id),
            "role": user.role.value,
            "email": user.email,
            "session_id": str(session.id)
        }
    )
    new_refresh_token, new_refresh_jti = create_refresh_token(
        str(user.id),
        str(session.id),
        {
            "company_id": str(user.company_id),
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
    log_audit_event(
        db=db,
        action="auth.refresh",
        actor_type="RECRUITER",
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
            company_id=user.company_id
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
def me(request: Request, current_user: CurrentUser):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        company_id=current_user.company_id,
    )


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
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
    current_user: Annotated[User, Depends(get_current_user)]
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

