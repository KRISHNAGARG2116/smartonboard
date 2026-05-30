from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.security import decode_access_token
from db.session import SessionLocal, get_db, set_tenant_context, tenant_id_var
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


def get_tenant_db(
    current_user: Annotated[User, Depends(get_current_user)],
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

    def __call__(self, current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: insufficient role privileges",
            )
        return current_user


TenantDb = Annotated[Session, Depends(get_tenant_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
RequireOwner = Annotated[User, Depends(RoleChecker([UserRole.OWNER]))]
RequireRecruiter = Annotated[User, Depends(RoleChecker([UserRole.OWNER, UserRole.RECRUITER]))]
