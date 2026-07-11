import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_db, RequireEmployee
from core.security import verify_password
from models import User
from models.enums import UserRole
from schemas.auth import AuthResponse, CandidateLoginRequest, UserResponse
from core.limiter import limiter
from api.auth import is_ip_blocked, record_failed_login, create_user_session_and_tokens
from db.session import tenant_context

router = APIRouter(prefix="/employee/auth", tags=["Employee Authentication"])

@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
def login_employee(
    request: Request,
    response: Response,
    body: CandidateLoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Authenticate an employee with email + password. Returns employee JWT."""
    dummy_hash = "$2b$12$L7p.yF7T24Q.8Wk7Qz9.4ux7R6j8q9b0n1o2p3q4r5s6t7u8v9w0x"
    ip = request.client.host if request.client else "127.0.0.1"

    if is_ip_blocked(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. This IP is temporarily locked out.",
        )

    # query user under auth_mode to bypass recruiter isolation
    with tenant_context(auth_mode="true"):
        user = db.scalar(
            select(User).where(
                User.email == body.email.lower(),
                User.role == UserRole.EMPLOYEE,
                User.is_active.is_(True),
            )
        )

    if user is None:
        record_failed_login(ip)
        verify_password(body.password, dummy_hash)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(body.password, user.password_hash):
        record_failed_login(ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Login successful, issue tokens
    access_token, refresh_token = create_user_session_and_tokens(
        db=db,
        user=user,
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
        response=response
    )

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        verification_required=False,
        user=UserResponse.model_validate(user),
    )


@router.get("/verify", response_model=UserResponse)
def verify_employee(
    current_employee: RequireEmployee,
):
    """Verify employee token validity."""
    return UserResponse.model_validate(current_employee)
