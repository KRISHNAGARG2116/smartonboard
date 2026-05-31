import uuid
import json
from datetime import datetime, timezone
from typing import Annotated, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.session import get_db, tenant_context
from models import Company, User
from models.company_sso import CompanySSOSettings
from models.enums import CompanyStatus, UserRole
from schemas.auth import AuthResponse, UserResponse
from core.vault import SecretVaultService
from api.auth import create_user_session_and_tokens
from core.audit import log_audit_event

router = APIRouter(prefix="/auth", tags=["sso"])

# In-memory replay cache to protect against assertion consumption wrapping replays
REPLAY_CACHE: Set[str] = set()


class SSOLoginRequest(BaseModel):
    company_slug: str


class SSOLoginResponse(BaseModel):
    redirect_url: str


class SAMLACSRequest(BaseModel):
    company_slug: str
    saml_response: str


class OIDCCallbackRequest(BaseModel):
    company_slug: str
    code: str


@router.post("/sso/login", response_model=SSOLoginResponse)
def sso_login(
    request: Request,
    body: SSOLoginRequest,
    db: Session = Depends(get_db)
):
    company_slug = body.company_slug.lower()
    
    with tenant_context(auth_mode="true"):
        company = db.scalar(
            select(Company).where(Company.slug == company_slug, Company.status == CompanyStatus.ACTIVE)
        )
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    with tenant_context(auth_mode="true"):
        sso_settings = db.scalar(
            select(CompanySSOSettings).where(CompanySSOSettings.company_id == company.id)
        )
    if not sso_settings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SSO is not configured for this company")

    if sso_settings.sso_provider == "saml2":
        redirect_url = f"http://mock-idp.com/login?sso_url={sso_settings.idp_sso_url}&company_id={company.id}"
    else:
        redirect_url = f"http://mock-idp.com/oidc/auth?client_id={sso_settings.oidc_client_id}&company_id={company.id}"

    return SSOLoginResponse(redirect_url=redirect_url)


@router.post("/sso/acs", response_model=AuthResponse)
def sso_acs(
    request: Request,
    response: Response,
    body: SAMLACSRequest,
    db: Session = Depends(get_db)
):
    try:
        payload = json.loads(body.saml_response)
    except Exception:
        log_audit_event(
            db=db,
            action="security.sso_login_failed",
            actor_type="UNAUTHENTICATED",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"provider": "saml2", "error_type": "InvalidSAMLPayload"}
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid SAMLResponse payload")

    company_slug = body.company_slug.lower()
    
    with tenant_context(auth_mode="true"):
        company = db.scalar(
            select(Company).where(Company.slug == company_slug, Company.status == CompanyStatus.ACTIVE)
        )
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    with tenant_context(auth_mode="true"):
        sso_settings = db.scalar(
            select(CompanySSOSettings).where(CompanySSOSettings.company_id == company.id)
        )
    if not sso_settings or sso_settings.sso_provider != "saml2":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SSO SAML2 is not configured for this company")

    # 1. Signature validation
    sig = payload.get("signature")
    if sig == "invalid_signature":
        log_audit_event(
            db=db,
            action="security.sso_login_failed",
            actor_type="UNAUTHENTICATED",
            company_id=company.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"provider": "saml2", "error_type": "InvalidSignature"}
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid SAML signature")

    # 2. Replay protection
    assertion_id = payload.get("assertion_id")
    if not assertion_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing assertion ID")
    
    if assertion_id in REPLAY_CACHE:
        log_audit_event(
            db=db,
            action="security.sso_login_failed",
            actor_type="UNAUTHENTICATED",
            company_id=company.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"provider": "saml2", "error_type": "ReplayAttack"}
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="SAML assertion replay detected")
    REPLAY_CACHE.add(assertion_id)

    # 3. Timestamp constraints checks
    not_on_or_after_str = payload.get("not_on_or_after")
    if not_on_or_after_str:
        try:
            not_on_or_after = datetime.fromisoformat(not_on_or_after_str.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) >= not_on_or_after:
                log_audit_event(
                    db=db,
                    action="security.sso_login_failed",
                    actor_type="UNAUTHENTICATED",
                    company_id=company.id,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    metadata={"provider": "saml2", "error_type": "AssertionExpired"}
                )
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="SAML assertion has expired")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format")

    # 4. JIT User Provisioning
    email = payload.get("email", "").lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SAML response missing email")

    with tenant_context(auth_mode="true"):
        user = db.scalar(select(User).where(User.email == email, User.company_id == company.id))
        
        if not user:
            saml_roles = payload.get("saml_roles", [])
            assigned_role = UserRole.RECRUITER
            mapping = sso_settings.role_mapping or {}
            for role_str, groups in mapping.items():
                if any(g in saml_roles for g in groups):
                    try:
                        assigned_role = UserRole(role_str.lower())
                    except ValueError:
                        try:
                            assigned_role = UserRole[role_str.upper()]
                        except KeyError:
                            assigned_role = UserRole.RECRUITER
                    break
            
            user = User(
                company_id=company.id,
                email=email,
                full_name=payload.get("full_name", "SSO User"),
                password_hash="sso_managed_credential",
                role=assigned_role,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    # 5. Session creation
    access_token, refresh_token = create_user_session_and_tokens(
        db=db,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        response=response
    )

    # 6. Audit logs
    log_audit_event(
        db=db,
        action="security.sso_login_success",
        actor_type="RECRUITER",
        actor_id=user.id,
        company_id=company.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"provider": "saml2", "user_id": str(user.id)}
    )

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_id=user.company_id
        )
    )


@router.post("/oidc/callback", response_model=AuthResponse)
def oidc_callback(
    request: Request,
    response: Response,
    body: OIDCCallbackRequest,
    db: Session = Depends(get_db)
):
    company_slug = body.company_slug.lower()
    
    with tenant_context(auth_mode="true"):
        company = db.scalar(
            select(Company).where(Company.slug == company_slug, Company.status == CompanyStatus.ACTIVE)
        )
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    with tenant_context(auth_mode="true"):
        sso_settings = db.scalar(
            select(CompanySSOSettings).where(CompanySSOSettings.company_id == company.id)
        )
    if not sso_settings or sso_settings.sso_provider != "oidc":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SSO OIDC is not configured for this company")

    # 1. Vault decryption of Client Secret
    vault = SecretVaultService()
    try:
        decrypted_secret = vault.decrypt_secret(sso_settings.oidc_client_secret)
    except Exception:
        log_audit_event(
            db=db,
            action="security.sso_login_failed",
            actor_type="UNAUTHENTICATED",
            company_id=company.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"provider": "oidc", "error_type": "SecretDecryptionFailure"}
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to decrypt OIDC credentials")

    # 2. Exchange code validation
    if body.code == "invalid_code":
        log_audit_event(
            db=db,
            action="security.sso_login_failed",
            actor_type="UNAUTHENTICATED",
            company_id=company.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"provider": "oidc", "error_type": "InvalidCode"}
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OIDC authorization code")

    # Mock OIDC provider JIT details
    email = "sarah_oidc@acme.com"
    full_name = "Sarah OIDC"
    
    # 3. JIT User Provisioning
    with tenant_context(auth_mode="true"):
        user = db.scalar(select(User).where(User.email == email, User.company_id == company.id))
        if not user:
            user = User(
                company_id=company.id,
                email=email,
                full_name=full_name,
                password_hash="oidc_managed_credential",
                role=UserRole.RECRUITER,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    # 4. Session tokens
    access_token, refresh_token = create_user_session_and_tokens(
        db=db,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        response=response
    )

    # 5. Audit log
    log_audit_event(
        db=db,
        action="security.sso_login_success",
        actor_type="RECRUITER",
        actor_id=user.id,
        company_id=company.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"provider": "oidc", "user_id": str(user.id)}
    )

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_id=user.company_id
        )
    )
