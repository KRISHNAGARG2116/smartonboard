from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import CurrentUser, TenantDb
from core.security import create_access_token, hash_password, verify_password
from core.slug import unique_slug
from db.session import get_db, tenant_context
from models import Company, User
from models.enums import CompanyStatus, UserRole
from schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from schemas.company import CompanyResponse, CompanyUpdateRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Annotated[Session, Depends(get_db)]):
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

    token = create_access_token(
        str(user.id),
        {"company_id": str(user.company_id), "role": user.role.value, "email": user.email},
    )
    return AuthResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_id=user.company_id,
        ),
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    with tenant_context(auth_mode="true"):
        user = db.scalar(select(User).where(User.email == body.email.lower(), User.is_active.is_(True)))
        if user is None or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(
        str(user.id),
        {"company_id": str(user.company_id), "role": user.role.value, "email": user.email},
    )
    return AuthResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_id=user.company_id,
        ),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        company_id=current_user.company_id,
    )
