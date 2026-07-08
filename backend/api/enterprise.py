import hashlib
import ipaddress
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select

from api.deps import RequireOwner, TenantDb
from core.audit import log_audit_event
from core.vault import SecretVaultService
from core.middleware import resolve_client_ip
from core.smtp import verify_smtp_credentials
from models.enterprise import CompanyIPWhitelist, CompanySMTPSettings
from schemas.enterprise import (
    CompanyIPWhitelistCreate,
    CompanyIPWhitelistResponse,
    CompanySMTPSettingsCreate,
    CompanySMTPSettingsResponse,
    CompanySubscriptionPlanResponse,
    CompanySubscriptionPlanUpdateRequest,
    CompanyUsageLedgerResponse,
)

logger = logging.getLogger("app")

router = APIRouter(prefix="/enterprise", tags=["enterprise_governance"])


# =========================================================================
# IP Whitelisting Endpoints
# =========================================================================

@router.post("/ip-whitelist", response_model=CompanyIPWhitelistResponse, status_code=status.HTTP_201_CREATED)
def create_ip_whitelist(
    body: CompanyIPWhitelistCreate,
    request: Request,
    current_user: RequireOwner,
    db: TenantDb,
):
    # Lockout protection check: resolve client IP and assert it is in proposed range
    proxies_str = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1")
    trusted_proxies = [p.strip() for p in proxies_str.split(",") if p.strip()]
    client_ip_str = resolve_client_ip(request, trusted_proxies)
    client_ip = ipaddress.ip_address(client_ip_str)

    proposed_network = ipaddress.ip_network(body.cidr_block, strict=False)

    if client_ip not in proposed_network:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lockout protection: Your current IP address is not within the proposed whitelisted CIDR range."
        )

    # Save whitelist CIDR
    whitelist = CompanyIPWhitelist(
        company_id=current_user.company_id,
        cidr_block=body.cidr_block,
        is_active=True,
        description=body.description,
    )
    db.add(whitelist)
    db.commit()
    db.refresh(whitelist)

    # Log enterprise.ip_whitelisted audit event
    log_audit_event(
        db=db,
        action="enterprise.ip_whitelisted",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="company_ip_whitelists",
        resource_id=str(whitelist.id),
        ip_address=client_ip_str,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "ip_whitelist_id": str(whitelist.id),
            "cidr_block": body.cidr_block,
            "description": body.description,
        }
    )
    db.commit()

    return whitelist


@router.get("/ip-whitelist", response_model=List[CompanyIPWhitelistResponse])
def list_ip_whitelists(
    current_user: RequireOwner,
    db: TenantDb,
):
    stmt = select(CompanyIPWhitelist).where(
        CompanyIPWhitelist.company_id == current_user.company_id
    ).order_by(CompanyIPWhitelist.created_at.desc())
    return list(db.scalars(stmt).all())


@router.delete("/ip-whitelist/{whitelist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ip_whitelist(
    whitelist_id: uuid.UUID,
    request: Request,
    current_user: RequireOwner,
    db: TenantDb,
):
    whitelist = db.scalar(
        select(CompanyIPWhitelist).where(
            CompanyIPWhitelist.id == whitelist_id,
            CompanyIPWhitelist.company_id == current_user.company_id
        )
    )
    if not whitelist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IP Whitelist range not found")

    db.delete(whitelist)
    db.commit()

    # Log enterprise.ip_whitelist_removed audit event
    proxies_str = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1")
    trusted_proxies = [p.strip() for p in proxies_str.split(",") if p.strip()]
    client_ip_str = resolve_client_ip(request, trusted_proxies)

    log_audit_event(
        db=db,
        action="enterprise.ip_whitelist_removed",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="company_ip_whitelists",
        resource_id=str(whitelist_id),
        ip_address=client_ip_str,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "ip_whitelist_id": str(whitelist_id),
            "cidr_block": whitelist.cidr_block,
        }
    )
    db.commit()


# =========================================================================
# SMTP Gateway Endpoints
# =========================================================================

@router.get("/smtp", response_model=CompanySMTPSettingsResponse)
def get_smtp_settings(
    current_user: RequireOwner,
    db: TenantDb,
):
    smtp = db.scalar(
        select(CompanySMTPSettings).where(
            CompanySMTPSettings.company_id == current_user.company_id
        )
    )
    if not smtp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMTP settings not configured")
    return smtp


@router.post("/smtp", response_model=CompanySMTPSettingsResponse)
def configure_smtp_settings(
    body: CompanySMTPSettingsCreate,
    request: Request,
    current_user: RequireOwner,
    db: TenantDb,
):
    # Lookup existing SMTP settings to track rotation changes
    smtp = db.scalar(
        select(CompanySMTPSettings).where(
            CompanySMTPSettings.company_id == current_user.company_id
        )
    )

    vault = SecretVaultService()
    encrypted_json = vault.encrypt_secret(body.password)
    encrypted_dict = json.loads(encrypted_json)

    proxies_str = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1")
    trusted_proxies = [p.strip() for p in proxies_str.split(",") if p.strip()]
    client_ip_str = resolve_client_ip(request, trusted_proxies)

    now = datetime.now(timezone.utc)

    if smtp:
        # Check if credential parameters changed (Rotation)
        is_rotated = (
            smtp.hostname != body.hostname or
            smtp.port != body.port or
            smtp.username != body.username or
            smtp.sender_email != body.sender_email
        )
        
        # Test password decryption to see if password changed
        if not is_rotated:
            try:
                envelope = {
                    "ciphertext": smtp.encrypted_password,
                    "iv": smtp.iv,
                    "tag": smtp.tag,
                    "key_version": smtp.key_version
                }
                old_password = vault.decrypt_secret(json.dumps(envelope))
                if old_password != body.password:
                    is_rotated = True
            except Exception:
                is_rotated = True

        smtp.hostname = body.hostname
        smtp.port = body.port
        smtp.username = body.username
        smtp.encrypted_password = encrypted_dict["ciphertext"]
        smtp.iv = encrypted_dict["iv"]
        smtp.tag = encrypted_dict["tag"]
        smtp.key_version = encrypted_dict.get("key_version", "v1")
        smtp.sender_email = str(body.sender_email)
        smtp.updated_at = now

        if is_rotated:
            smtp.verification_status = "pending"
            smtp.last_rotated_at = now
            smtp.last_verified_at = None
            smtp.last_verification_error = None

            # Log enterprise.smtp_rotation audit event
            log_audit_event(
                db=db,
                action="enterprise.smtp_rotation",
                actor_type="RECRUITER",
                actor_id=current_user.id,
                company_id=current_user.company_id,
                resource_type="company_smtp_settings",
                resource_id=str(smtp.id),
                ip_address=client_ip_str,
                user_agent=request.headers.get("user-agent"),
                metadata={
                    "smtp_setting_id": str(smtp.id),
                    "hostname": body.hostname,
                    "port": body.port,
                }
            )
    else:
        smtp = CompanySMTPSettings(
            company_id=current_user.company_id,
            hostname=body.hostname,
            port=body.port,
            username=body.username,
            encrypted_password=encrypted_dict["ciphertext"],
            iv=encrypted_dict["iv"],
            tag=encrypted_dict["tag"],
            key_version=encrypted_dict.get("key_version", "v1"),
            sender_email=str(body.sender_email),
            verification_status="pending",
            last_rotated_at=now,
            updated_at=now,
        )
        db.add(smtp)
        db.flush()

        # Log initial configuration as a rotation/setup event
        log_audit_event(
            db=db,
            action="enterprise.smtp_rotation",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            resource_type="company_smtp_settings",
            resource_id=str(smtp.id),
            ip_address=client_ip_str,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "smtp_setting_id": str(smtp.id),
                "hostname": body.hostname,
                "port": body.port,
            }
        )

    db.commit()
    db.refresh(smtp)
    return smtp


@router.post("/smtp/test", response_model=CompanySMTPSettingsResponse)
def test_smtp_settings(
    request: Request,
    current_user: RequireOwner,
    db: TenantDb,
):
    smtp = db.scalar(
        select(CompanySMTPSettings).where(
            CompanySMTPSettings.company_id == current_user.company_id
        )
    )
    if not smtp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMTP settings not configured")

    vault = SecretVaultService()
    
    # Decrypt password credentials
    try:
        envelope = {
            "ciphertext": smtp.encrypted_password,
            "iv": smtp.iv,
            "tag": smtp.tag,
            "key_version": smtp.key_version
        }
        password_plain = vault.decrypt_secret(json.dumps(envelope))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Credentials decrypt failed: {str(e)}"
        )

    proxies_str = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1")
    trusted_proxies = [p.strip() for p in proxies_str.split(",") if p.strip()]
    client_ip_str = resolve_client_ip(request, trusted_proxies)

    now = datetime.now(timezone.utc)

    try:
        # Perform SMTP connection STARTTLS handshake check
        verify_smtp_credentials(
            hostname=smtp.hostname,
            port=smtp.port,
            username=smtp.username,
            password_plain=password_plain
        )

        smtp.verification_status = "verified"
        smtp.last_verified_at = now
        smtp.last_verification_error = None
        db.add(smtp)
        db.flush()

        # Log enterprise.smtp_configured audit event
        log_audit_event(
            db=db,
            action="enterprise.smtp_configured",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            resource_type="company_smtp_settings",
            resource_id=str(smtp.id),
            ip_address=client_ip_str,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "smtp_setting_id": str(smtp.id),
                "hostname": smtp.hostname,
                "port": smtp.port,
            }
        )

    except Exception as e:
        smtp.verification_status = "failed"
        smtp.last_verification_error = str(e)
        db.add(smtp)
        db.flush()

        # Log enterprise.smtp_test_failed audit event
        log_audit_event(
            db=db,
            action="enterprise.smtp_test_failed",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            resource_type="company_smtp_settings",
            resource_id=str(smtp.id),
            ip_address=client_ip_str,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "smtp_setting_id": str(smtp.id),
                "hostname": smtp.hostname,
                "port": smtp.port,
                "error": str(e),
            }
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SMTP handshake verification failed: {str(e)}"
        )

    db.commit()
    db.refresh(smtp)
    return smtp


# =========================================================================
# Subscription & Quota Ledgers Endpoints
# =========================================================================

from sqlalchemy.orm import Session
from db.session import get_db

def require_owner_or_billing_service(
    request: Request,
    db: Session,
) -> dict:
    is_billing_service = request.headers.get("X-Billing-Service-Token") == os.getenv(
        "BILLING_SERVICE_TOKEN", "secure-billing-service-token"
    )
    if is_billing_service:
        company_id_str = request.headers.get("X-Company-Id")
        if not company_id_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Billing Service requests must carry a valid 'X-Company-Id' header."
            )
        try:
            company_id = uuid.UUID(company_id_str)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 'X-Company-Id' header format."
            )

        from db.session import set_tenant_context, tenant_id_var
        tenant_id_var.set(str(company_id))
        set_tenant_context(db, str(company_id))

        return {
            "company_id": company_id,
            "actor_id": None,
            "actor_type": "SYSTEM"
        }
    
    # Otherwise, require logged-in Owner
    from fastapi.security import HTTPAuthorizationCredentials
    from api.deps import get_current_user
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = get_current_user(credentials=credentials, db=db)
    if user.role.value != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only Company Owners or the Billing Service can modify subscription plans."
        )

    from db.session import set_tenant_context, tenant_id_var
    tenant_id_var.set(str(user.company_id))
    set_tenant_context(db, str(user.company_id))

    return {
        "company_id": user.company_id,
        "actor_id": user.id,
        "actor_type": "RECRUITER"
    }


@router.get("/subscription", response_model=CompanySubscriptionPlanResponse)
def get_company_subscription(
    current_user: RequireOwner,
    db: TenantDb,
):
    from core.quota import get_or_initialize_subscription_plan
    return get_or_initialize_subscription_plan(db, current_user.company_id)


@router.get("/usage", response_model=CompanyUsageLedgerResponse)
def get_company_usage(
    current_user: RequireOwner,
    db: TenantDb,
):
    from core.quota import get_or_initialize_usage_ledger
    from sqlalchemy import func
    from models import Job

    ledger = get_or_initialize_usage_ledger(db, current_user.company_id)
    
    # Sync live active jobs count for accuracy
    stmt = select(func.count(Job.id)).where(
        Job.company_id == current_user.company_id,
        Job.status == "active"
    )
    ledger.active_jobs_count = db.scalar(stmt)
    db.add(ledger)
    db.commit()
    db.refresh(ledger)
    return ledger


@router.post("/subscription", response_model=CompanySubscriptionPlanResponse)
def update_company_subscription(
    body: CompanySubscriptionPlanUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    auth_data = require_owner_or_billing_service(request, db)
    company_id = auth_data["company_id"]
    actor_id = auth_data["actor_id"]
    actor_type = auth_data["actor_type"]

    # Process Tier Upgrade/Downgrade Lifecycle
    from core.quota import get_or_initialize_subscription_plan
    plan = get_or_initialize_subscription_plan(db, company_id)

    target_tier = body.tier_name.lower()
    current_tier = plan.tier_name.lower()

    if target_tier == current_tier:
        return plan

    tier_levels = {"free": 1, "growth": 2, "enterprise": 3}
    current_level = tier_levels.get(current_tier, 1)
    target_level = tier_levels.get(target_tier, 1)

    now = datetime.now(timezone.utc)

    # Determine limits
    limits_map = {
        "free": {"candidate": 5, "job": 3, "ai": 5, "webhook": 10},
        "growth": {"candidate": 100, "job": 20, "ai": 100, "webhook": 200},
        "enterprise": {"candidate": 1000, "job": 100, "ai": 1000, "webhook": 2000}
    }
    new_limits = limits_map.get(target_tier, limits_map["free"])

    if target_level > current_level:
        # 1. UPGRADE: Take effect immediately
        plan.tier_name = target_tier
        plan.candidate_limit = new_limits["candidate"]
        plan.job_limit = new_limits["job"]
        plan.ai_limit = new_limits["ai"]
        plan.webhook_limit = new_limits["webhook"]

        # Cancel any pending scheduled downgrades
        plan.pending_downgrade_tier = None
        plan.pending_downgrade_effective_at = None
        plan.updated_at = now
        db.add(plan)
        db.commit()
        db.refresh(plan)

        # Log billing.tier_upgraded audit event
        log_audit_event(
            db=db,
            action="billing.tier_upgraded",
            actor_type=actor_type,
            actor_id=actor_id,
            company_id=company_id,
            resource_type="company_subscription_plans",
            resource_id=str(plan.id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "old_tier": current_tier,
                "new_tier": target_tier,
                "candidate_limit": new_limits["candidate"],
                "job_limit": new_limits["job"],
            }
        )
    else:
        # 2. DOWNGRADE: Effective next billing cycle
        plan.pending_downgrade_tier = target_tier
        plan.pending_downgrade_effective_at = plan.billing_cycle_end
        plan.updated_at = now
        db.add(plan)
        db.commit()
        db.refresh(plan)

        # Log billing.downgrade_scheduled audit event
        log_audit_event(
            db=db,
            action="billing.downgrade_scheduled",
            actor_type=actor_type,
            actor_id=actor_id,
            company_id=company_id,
            resource_type="company_subscription_plans",
            resource_id=str(plan.id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "current_tier": current_tier,
                "pending_downgrade_tier": target_tier,
                "effective_at": plan.billing_cycle_end.isoformat(),
            }
        )

    return plan
