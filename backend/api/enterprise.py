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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SMTP handshake verification failed: {str(e)}"
        )

    db.commit()
    db.refresh(smtp)
    return smtp
