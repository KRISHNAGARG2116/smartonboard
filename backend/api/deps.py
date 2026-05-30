from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.security import decode_access_token
from db.session import SessionLocal, get_db, set_tenant_context
from models import User

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
        if not user_id or not company_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    set_tenant_context(db, company_id)
    user = db.scalar(
        select(User).where(
            User.id == UUID(user_id),
            User.company_id == UUID(company_id),
            User.is_active.is_(True),
        )
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_tenant_db(
    current_user: Annotated[User, Depends(get_current_user)],
) -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        set_tenant_context(db, str(current_user.company_id))
        yield db
    finally:
        db.close()


TenantDb = Annotated[Session, Depends(get_tenant_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
