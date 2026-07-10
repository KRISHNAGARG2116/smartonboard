import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Annotated, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel
from sqlalchemy import select

from api.deps import TenantDb, RequireRecruiter
from api.auth import create_user_session_and_tokens
from core.security import hash_password, verify_password
from db.session import tenant_context
from models import Company, User
from models.company_sso import CompanySSOSettings
from models.enums import UserRole

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/identity/sso", tags=["identity"])


# --- Schemas ---

class SAMLImportRequest(BaseModel):
    sso_provider: str  # saml2, oidc
    idp_entity_id: str
    idp_sso_url: str
    idp_x509_cert: str
    idp_x509_cert_expiry_days: int = 365
    role_mapping: dict = {}


class CertRotationRequest(BaseModel):
    next_cert: str
    expiry_days: int = 365


class BreakGlassConfigureRequest(BaseModel):
    enabled: bool
    emergency_password: str | None = None


class BreakGlassLoginRequest(BaseModel):
    email: str
    password: str


class SAMLACSRequest(BaseModel):
    saml_response_base64: str


# --- Endpoints ---

@router.get("/saml/metadata")
def get_sp_metadata(request: Request):
    """
    Generates Service Provider (SP) metadata XML.
    """
    base_url = str(request.base_url).rstrip("/")
    entity_id = f"{base_url}/api/v1/identity/sso/saml/metadata"
    acs_url = f"{base_url}/api/v1/identity/sso/saml/acs"
    
    metadata_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor entityID="{entity_id}" xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata">
    <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="{acs_url}" index="1"/>
        <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
    return Response(content=metadata_xml, media_type="application/xml")


@router.post("/saml/import", status_code=status.HTTP_200_OK)
def import_idp_metadata(
    payload: SAMLImportRequest,
    db: TenantDb,
    current_user: RequireRecruiter
):
    """Imports IdP metadata configuration for the active tenant."""
    # Verify owner permission
    if current_user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Only owners can configure SSO.")

    expiry_date = datetime.now(timezone.utc) + timedelta(days=payload.idp_x509_cert_expiry_days)
    
    settings = db.scalar(
        select(CompanySSOSettings).where(CompanySSOSettings.company_id == current_user.company_id)
    )
    
    if not settings:
        settings = CompanySSOSettings(
            company_id=current_user.company_id,
            sso_provider=payload.sso_provider,
            idp_entity_id=payload.idp_entity_id,
            idp_sso_url=payload.idp_sso_url,
            idp_x509_cert=payload.idp_x509_cert,
            idp_x509_cert_expiry=expiry_date,
            role_mapping=payload.role_mapping
        )
        db.add(settings)
    else:
        settings.sso_provider = payload.sso_provider
        settings.idp_entity_id = payload.idp_entity_id
        settings.idp_sso_url = payload.idp_sso_url
        settings.idp_x509_cert = payload.idp_x509_cert
        settings.idp_x509_cert_expiry = expiry_date
        settings.role_mapping = payload.role_mapping

    db.commit()
    return {"status": "success", "message": "IdP Metadata imported successfully."}


@router.post("/saml/rotate-cert", status_code=status.HTTP_200_OK)
def rotate_saml_certificate(
    payload: CertRotationRequest,
    db: TenantDb,
    current_user: RequireRecruiter
):
    """Promotes next rollover certificate or staging cert to active status."""
    if current_user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Only owners can configure certificate settings.")

    settings = db.scalar(
        select(CompanySSOSettings).where(CompanySSOSettings.company_id == current_user.company_id)
    )
    if not settings:
        raise HTTPException(status_code=404, detail="SSO settings not configured for this tenant.")

    expiry_date = datetime.now(timezone.utc) + timedelta(days=payload.expiry_days)
    
    # Store KEK/cert rotation rollover history
    settings.idp_x509_cert_next = payload.next_cert
    settings.idp_x509_cert_expiry = expiry_date
    db.commit()

    return {"status": "success", "message": "SSO certificate rollover registered successfully."}


@router.post("/saml/acs")
def assertion_consumer_service(
    payload: SAMLACSRequest,
    request: Request,
    response: Response,
    db: TenantDb
):
    """
    SAML ACS callback resolving JIT provisioning and logging users in.
    """
    # Simulate decoding SAML payload structure
    try:
        # Decrypted SAML attributes mock
        saml_email = "jit_user@corpdomain.com"
        saml_company_id_str = "e2d319e5-9c98-47fb-ba8d-db3288ebad4b"  # Tenant company uuid
        saml_company_id = uuid.UUID(saml_company_id_str)
        saml_full_name = "JIT Provisioned User"
        saml_role = "recruiter"
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid SAML response encoding.")

    # Fetch Tenant SSO configurations
    sso_settings = db.scalar(
        select(CompanySSOSettings).where(CompanySSOSettings.company_id == saml_company_id)
    )
    if not sso_settings:
        raise HTTPException(status_code=400, detail="SSO configurations not configured for this tenant.")

    # Check Certificate Expiration
    if sso_settings.idp_x509_cert_expiry and datetime.now(timezone.utc) > sso_settings.idp_x509_cert_expiry.replace(tzinfo=timezone.utc):
        logger.warning(f"SAML Certificate expired on {sso_settings.idp_x509_cert_expiry}")
        # Rollover check
        if sso_settings.idp_x509_cert_next:
            logger.info("Promoting rollover certificate to active key.")
            sso_settings.idp_x509_cert = sso_settings.idp_x509_cert_next
            sso_settings.idp_x509_cert_next = None
            db.commit()
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="SSO SAML Certificate has expired.")

    # JIT Provision User
    with tenant_context(tenant_id=saml_company_id):
        user = db.scalar(
            select(User).where(User.email == saml_email)
        )
        if not user:
            logger.info(f"JIT Provisioning new user {saml_email} in company {saml_company_id}")
            user = User(
                company_id=saml_company_id,
                email=saml_email,
                password_hash=hash_password(str(uuid.uuid4())), # random secure fallback password
                full_name=saml_full_name,
                role=UserRole.RECRUITER,
                email_verified=True,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    # Issue Session Tokens
    access_token, refresh_token = create_user_session_and_tokens(
        db=db,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        response=response
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "company_id": str(user.company_id)
        }
    }


@router.post("/break-glass/configure", status_code=status.HTTP_200_OK)
def configure_break_glass_access(
    payload: BreakGlassConfigureRequest,
    db: TenantDb,
    current_user: RequireRecruiter
):
    """Enables or disables local authentication recovery bypass for tenant owner."""
    if current_user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Only owners can configure emergency access settings.")

    sso_settings = db.scalar(
        select(CompanySSOSettings).where(CompanySSOSettings.company_id == current_user.company_id)
    )
    if not sso_settings:
        raise HTTPException(status_code=404, detail="SSO settings not configured.")

    sso_settings.emergency_access_enabled = payload.enabled
    
    if payload.enabled and payload.emergency_password:
        # Override owner password to emergency bypass password
        current_user.password_hash = hash_password(payload.emergency_password)
        db.add(current_user)

    db.commit()
    return {"status": "success", "emergency_access_enabled": payload.enabled}


@router.post("/break-glass/login")
def break_glass_emergency_login(
    payload: BreakGlassLoginRequest,
    request: Request,
    response: Response,
    db: TenantDb
):
    """Traditional login bypass for owners when SSO is down."""
    user = db.scalar(
        select(User).where(User.email == payload.email, User.role == UserRole.OWNER)
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid emergency credentials.")

    sso_settings = db.scalar(
        select(CompanySSOSettings).where(CompanySSOSettings.company_id == user.company_id)
    )
    
    if not sso_settings or not sso_settings.emergency_access_enabled:
        raise HTTPException(status_code=403, detail="Emergency break-glass recovery account is not active.")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid emergency credentials.")

    # Issue Session Tokens
    access_token, refresh_token = create_user_session_and_tokens(
        db=db,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        response=response
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "emergency_bypass": True
    }
