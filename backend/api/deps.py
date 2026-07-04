from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.security import decode_access_token
from db.session import SessionLocal, get_db, set_tenant_context, tenant_id_var, tenant_context
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
        if role == UserRole.CANDIDATE.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidates are not permitted to access recruiter resources",
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




