from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.security import decode_access_token
from db.session import SessionLocal, get_db, set_tenant_context, tenant_id_var, tenant_context, auth_mode_var, set_auth_mode
from models import User, Company
from models.enums import CompanyStatus, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
        role = payload.get("role")
        if role in (UserRole.CANDIDATE.value, UserRole.EMPLOYEE.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not permitted to access recruiter resources",
            )
        user_id = payload.get("sub")
        company_id = payload.get("company_id")
        jti = payload.get("jti")
        session_id = payload.get("session_id")
        if not user_id or not company_id or not jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            
        # Check if access token is blacklisted
        from models.session import RevokedToken, UserSession
        from datetime import datetime, timezone
        from uuid import UUID
        
        revoked = db.scalar(select(RevokedToken).where(RevokedToken.jti == jti))
        if revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
            
        # Check and update session activity
        if session_id:
            session = db.scalar(select(UserSession).where(UserSession.id == UUID(session_id)))
            if not session or session.is_revoked or session.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired or is revoked")
            
            # Update last_active
            session.last_active = datetime.now(timezone.utc)
            db.add(session)
            db.commit()
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    # Set tenant context variable so RLS applies to the User query and subsequent queries
    tenant_id_var.set(company_id)
    set_tenant_context(db, company_id)

    # Validate active user AND active company status simultaneously
    user = db.scalar(
        select(User)
        .join(Company, User.company_id == Company.id)
        .where(
            User.id == UUID(user_id),
            User.company_id == UUID(company_id),
            User.is_active.is_(True),
            Company.status == CompanyStatus.ACTIVE,
        )
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or company is inactive/suspended")
    return user


def get_current_user_setup(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
        role = payload.get("role")
        if role == UserRole.CANDIDATE.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidates are not permitted to access recruiter resources",
            )
        user_id = payload.get("sub")
        jti = payload.get("jti")
        session_id = payload.get("session_id")
        if not user_id or not jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        # Check if access token is blacklisted
        from models.session import RevokedToken, UserSession
        from datetime import datetime, timezone
        from uuid import UUID

        revoked = db.scalar(select(RevokedToken).where(RevokedToken.jti == jti))
        if revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

        # Check and update session activity
        if session_id:
            session = db.scalar(select(UserSession).where(UserSession.id == UUID(session_id)))
            if not session or session.is_revoked or session.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired or is revoked")

            session.last_active = datetime.now(timezone.utc)
            db.add(session)
            db.commit()
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    # No company context yet, query user directly (bypass RLS / query in auth_mode)
    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User)
            .where(
                User.id == UUID(user_id),
                User.is_active.is_(True),
            )
        )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    with tenant_context(auth_mode="true"):
        if user.company_id is not None and user.company_onboarding_completed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already belongs to a company")
    return user



def get_current_user_for_profile(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
        role = payload.get("role")
        if role == UserRole.CANDIDATE.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidates are not permitted to access recruiter resources",
            )
        user_id = payload.get("sub")
        company_id = payload.get("company_id")
        jti = payload.get("jti")
        session_id = payload.get("session_id")
        if not user_id or not jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        # Check if access token is blacklisted
        from models.session import RevokedToken, UserSession
        from datetime import datetime, timezone
        from uuid import UUID

        revoked = db.scalar(select(RevokedToken).where(RevokedToken.jti == jti))
        if revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

        # Check and update session activity
        if session_id:
            session = db.scalar(select(UserSession).where(UserSession.id == UUID(session_id)))
            if not session or session.is_revoked or session.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired or is revoked")

            session.last_active = datetime.now(timezone.utc)
            db.add(session)
            db.commit()
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if company_id:
        tenant_id_var.set(company_id)
        set_tenant_context(db, company_id)
        user = db.scalar(
            select(User)
            .join(Company, User.company_id == Company.id)
            .where(
                User.id == UUID(user_id),
                User.company_id == UUID(company_id),
                User.is_active.is_(True),
                Company.status == CompanyStatus.ACTIVE,
            )
        )
    else:
        with tenant_context(auth_mode="true"):
            user = db.scalar(
                select(User)
                .where(
                    User.id == UUID(user_id),
                    User.is_active.is_(True),
                )
            )

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or company is inactive/suspended")
    return user


def get_verified_recruiter(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    import os
    if os.getenv("TESTING") == "true":
        from core.test_flags import BYPASS_EMAIL_VERIFICATION
        if BYPASS_EMAIL_VERIFICATION.value:
            return current_user
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user


def get_current_candidate(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Authenticate a candidate user from JWT.

    Candidates have no company_id and no tenant context.
    The JWT must contain role=candidate.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        role = payload.get("role")
        jti = payload.get("jti")
        session_id = payload.get("session_id")

        if not user_id or not jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        if role != UserRole.CANDIDATE.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint requires candidate authentication",
            )

        # Check if access token is blacklisted
        from models.session import RevokedToken, UserSession
        from datetime import datetime, timezone
        from uuid import UUID

        revoked = db.scalar(select(RevokedToken).where(RevokedToken.jti == jti))
        if revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

        # Check and update session activity
        if session_id:
            session = db.scalar(select(UserSession).where(UserSession.id == UUID(session_id)))
            if not session or session.is_revoked or session.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired or is revoked")

            session.last_active = datetime.now(timezone.utc)
            db.add(session)
            db.commit()
    except JWTError as exc:
        print("JWT_DECODE_ERROR_DETAILS:", str(exc), type(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    # Candidates bypass RLS - query under auth_mode
    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User).where(
                User.id == UUID(user_id),
                User.role == UserRole.CANDIDATE,
                User.is_active.is_(True),
            )
        )

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Candidate not found or inactive")
    return user


def get_current_employee(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Authenticate an employee user from JWT.

    Employees have user_id, company_id, and role=employee.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        role = payload.get("role")
        jti = payload.get("jti")
        session_id = payload.get("session_id")

        if not user_id or not jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        if role != UserRole.EMPLOYEE.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint requires employee authentication",
            )

        # Check if access token is blacklisted
        from models.session import RevokedToken, UserSession
        from datetime import datetime, timezone
        from uuid import UUID

        revoked = db.scalar(select(RevokedToken).where(RevokedToken.jti == jti))
        if revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

        # Check and update session activity
        if session_id:
            session = db.scalar(select(UserSession).where(UserSession.id == UUID(session_id)))
            if not session or session.is_revoked or session.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired or is revoked")

            session.last_active = datetime.now(timezone.utc)
            db.add(session)
            db.commit()
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    # Employees bypass recruiter RLS - query under auth_mode
    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User).where(
                User.id == UUID(user_id),
                User.role == UserRole.EMPLOYEE,
                User.is_active.is_(True),
            )
        )

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Employee not found or inactive")
    return user



def get_onboarded_recruiter(
    current_user: Annotated[User, Depends(get_verified_recruiter)],
) -> User:
    if not current_user.company_onboarding_completed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Onboarding incomplete"
        )
    return current_user


def get_tenant_db(
    current_user: Annotated[User, Depends(get_onboarded_recruiter)],
) -> Generator[Session, None, None]:
    db = SessionLocal()
    tenant_id_var.set(str(current_user.company_id))
    try:
        set_tenant_context(db, str(current_user.company_id))
        yield db
    finally:
        tenant_id_var.set("")
        db.close()


def get_candidate_db() -> Generator[Session, None, None]:
    """Provides a database session with RLS bypassed (auth_mode='true') for candidate operations.
    Security: This is the ONLY location where auth_mode is bypassed. Scoping must be enforced in the router logic.
    """
    db = SessionLocal()
    tenant_id_var.set("")
    set_auth_mode(db)
    try:
        yield db
    finally:
        tenant_id_var.set("")
        auth_mode_var.set("false")
        db.close()


def get_employee_db() -> Generator[Session, None, None]:
    """Provides a database session with RLS bypassed (auth_mode='true') for employee operations.
    """
    db = SessionLocal()
    tenant_id_var.set("")
    set_auth_mode(db)
    try:
        yield db
    finally:
        tenant_id_var.set("")
        auth_mode_var.set("false")
        db.close()



class RoleChecker:
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Annotated[User, Depends(get_onboarded_recruiter)]) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: insufficient role privileges",
            )
        return current_user



def get_portal_session(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)]
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
        employee_id = payload.get("sub")
        company_id = payload.get("company_id")
        token_type = payload.get("type")
        
        if not employee_id or not company_id or token_type != "portal":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid portal token")
            
        # Check revocation & expiration
        from models.employees import OnboardingPortalToken
        from datetime import datetime, timezone
        from uuid import UUID
        
        # Bypass RLS to check validity of portal session
        with tenant_context(auth_mode="true"):
            portal_token = db.scalar(
                select(OnboardingPortalToken).where(
                    OnboardingPortalToken.employee_id == UUID(employee_id),
                    OnboardingPortalToken.company_id == UUID(company_id),
                    OnboardingPortalToken.is_revoked.is_(False),
                    OnboardingPortalToken.expires_at > datetime.now(timezone.utc)
                )
            )
            if not portal_token:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Portal session revoked or expired")
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired portal token") from exc

    # Set tenant context variable so RLS applies to all subsequent queries in this request thread
    tenant_id_var.set(company_id)
    set_tenant_context(db, company_id)
    
    return {
        "employee_id": UUID(employee_id),
        "company_id": UUID(company_id),
        "scopes": payload.get("scopes", [])
    }


def get_portal_db(
    portal_session: Annotated[dict, Depends(get_portal_session)]
) -> Generator[Session, None, None]:
    db = SessionLocal()
    company_id = str(portal_session["company_id"])
    tenant_id_var.set(company_id)
    try:
        set_tenant_context(db, company_id)
        yield db
    finally:
        tenant_id_var.set("")
        db.close()


TenantDb = Annotated[Session, Depends(get_tenant_db)]
CurrentUser = Annotated[User, Depends(get_verified_recruiter)]
CurrentUserSetup = Annotated[User, Depends(get_current_user_setup)]
CurrentUserProfile = Annotated[User, Depends(get_current_user_for_profile)]
CurrentCandidate = Annotated[User, Depends(get_current_candidate)]
RequireOwner = Annotated[User, Depends(RoleChecker([UserRole.OWNER]))]
RequireRecruiter = Annotated[User, Depends(RoleChecker([UserRole.OWNER, UserRole.RECRUITER]))]
PortalSession = Annotated[dict, Depends(get_portal_session)]
PortalDb = Annotated[Session, Depends(get_portal_db)]


def get_verified_candidate(
    current_candidate: Annotated[User, Depends(get_current_candidate)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    import os
    if os.getenv("TESTING") == "true":
        from core.test_flags import BYPASS_EMAIL_VERIFICATION
        if BYPASS_EMAIL_VERIFICATION.value:
            return current_candidate
    from models.candidate_profile import CandidateProfile
    with tenant_context(auth_mode="true"):
        profile = db.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == current_candidate.id)
        )
    if not profile or not profile.email_verified or not profile.phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email and phone number must be verified before performing this action."
        )
    return current_candidate

VerifiedCandidate = Annotated[User, Depends(get_verified_candidate)]
RequireCandidate = Annotated[User, Depends(get_current_candidate)]
CandidateDb = Annotated[Session, Depends(get_candidate_db)]
RequireEmployee = Annotated[User, Depends(get_current_employee)]
EmployeeDb = Annotated[Session, Depends(get_employee_db)]



VerifiedRecruiter = Annotated[User, Depends(get_verified_recruiter)]


import json
import threading
from datetime import datetime, timedelta

_local_permission_cache = {}
_local_permission_cache_lock = threading.Lock()


def get_user_permissions(db: Session, user_id: UUID, company_id: UUID) -> set[str]:
    cache_key = f"user_permissions:{str(user_id)}:{str(company_id)}"
    redis_client = None
    try:
        import redis
        from core.config import get_settings
        redis_client = redis.from_url(get_settings().redis_url)
        cached = redis_client.get(cache_key)
        if cached:
            return set(json.loads(cached.decode("utf-8")))
    except Exception:
        pass

    with _local_permission_cache_lock:
        if cache_key in _local_permission_cache:
            val, expiry = _local_permission_cache[cache_key]
            if datetime.now() < expiry:
                return val

    from models.rbac import Permission, Role, user_roles, role_permissions
    stmt = (
        select(Permission.name)
        .join(role_permissions, Permission.id == role_permissions.c.permission_id)
        .join(Role, Role.id == role_permissions.c.role_id)
        .join(user_roles, Role.id == user_roles.c.role_id)
        .where(
            user_roles.c.user_id == user_id,
            Role.is_active == True,
            Role.deleted_at.is_(None)
        )
    )
    perm_names = set(db.scalars(stmt).all())

    if redis_client:
        try:
            redis_client.setex(cache_key, 3600, json.dumps(list(perm_names)))
        except Exception:
            pass

    with _local_permission_cache_lock:
        _local_permission_cache[cache_key] = (perm_names, datetime.now() + timedelta(hours=1))

    return perm_names


def invalidate_permission_cache(user_id: UUID, company_id: UUID):
    cache_key = f"user_permissions:{str(user_id)}:{str(company_id)}"
    try:
        import redis
        from core.config import get_settings
        redis_client = redis.from_url(get_settings().redis_url)
        redis_client.delete(cache_key)
    except Exception:
        pass
    with _local_permission_cache_lock:
        _local_permission_cache.pop(cache_key, None)


class RequirePermission:
    def __init__(self, permission: str):
        self.permission = permission

    def __call__(
        self,
        current_user: Annotated[User, Depends(get_verified_recruiter)],
        db: TenantDb,
    ) -> User:
        if current_user.role == UserRole.OWNER:
            return current_user

        perms = get_user_permissions(db, current_user.id, current_user.company_id)
        if self.permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: missing required permission '{self.permission}'",
            )
        return current_user


def has_job_access(db: Session, user: User, job_id: UUID, required_level: str = "read") -> bool:
    if user.role == UserRole.OWNER:
        return True
    from models.rbac import UserJobAccess
    stmt = select(UserJobAccess).where(UserJobAccess.user_id == user.id)
    user_accesses = db.scalars(stmt).all()
    if not user_accesses:
        return True
    for access in user_accesses:
        if access.job_id == job_id:
            if required_level == "read":
                return True
            elif required_level == "write" and access.access_level == "write":
                return True
    return False


def verify_developer_key(
    request: Request,
    db: TenantDb,
) -> "ApiKey":
    import hashlib
    import time
    import fastapi
    from models.api_key import ApiKey
    from db.session import tenant_id_var, set_tenant_context
    import redis
    from core.config import get_settings

    api_key_header = request.headers.get("X-API-Key")
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    key_hash = hashlib.sha256(api_key_header.encode("utf-8")).hexdigest()
    
    # We must query with auth_mode enabled temporarily since we don't have company_id context yet
    with tenant_context(auth_mode="true"):
        key = db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True))

    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API Key",
        )

    from datetime import datetime, timezone
    if key.expires_at and key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key has expired",
        )

    # Set tenant context
    tenant_id_var.set(key.company_id)
    set_tenant_context(db, key.company_id)

    # Rate limiting sliding window via Redis
    try:
        r = redis.from_url(get_settings().redis_url)
        current_ts = int(time.time())
        window_start = current_ts - 60
        redis_key = f"api_rate_limit:{key.id}"
        
        # Remove old requests
        r.zremrangebyscore(redis_key, 0, window_start)
        # Count current window requests
        request_count = r.zcard(redis_key)
        
        if request_count >= 100:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Maximum 100 requests per minute.",
            )
        
        # Add new request
        r.zadd(redis_key, {str(current_ts): current_ts})
        r.expire(redis_key, 60)
    except HTTPException:
        raise
    except Exception as e:
        # Fallback if Redis fails, do not block the request
        pass

    # Update metadata
    key.usage_count += 1
    key.last_used_at = datetime.now(timezone.utc)
    key.last_ip = request.client.host if request.client else None
    db.add(key)
    db.commit()

    # Emit api request billing event
    from core.workflow_engine import emit_billing_event
    emit_billing_event(db, key.company_id, "api.request", str(key.id))
    db.commit()

    return key


class RequireScope:
    def __init__(self, required_scope: str):
        self.required_scope = required_scope

    def __call__(
        self,
        api_key: Annotated["ApiKey", Depends(verify_developer_key)],
    ) -> "ApiKey":
        if self.required_scope not in api_key.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: API Key missing required scope '{self.required_scope}'",
            )
        return api_key






