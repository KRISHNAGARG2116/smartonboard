import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.deps import RequireOwner, TenantDb
from models.api_key import ApiKey
from models.integration_audit_log import IntegrationAuditLog

router = APIRouter(prefix="/apikeys", tags=["api_keys"])


class ApiKeyCreate(BaseModel):
    name: str
    scopes: List[str] = Field(default_factory=list)  # e.g. ["jobs.read", "applications.write"]
    expires_in_days: int | None = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    scopes: List[str]
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    last_ip: str | None
    rotated_at: datetime | None
    revoked_at: datetime | None
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyDetailResponse(ApiKeyResponse):
    raw_key: str | None = None


@router.post("", response_model=ApiKeyDetailResponse, status_code=status.HTTP_201_CREATED)
def generate_api_key(
    payload: ApiKeyCreate,
    request: Request,
    current_user: RequireOwner,
    db: TenantDb
):
    # Create secure token: smartonboard_live_xxxx
    raw_key = f"so_live_{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)

    key = ApiKey(
        company_id=current_user.company_id,
        name=payload.name,
        key_hash=key_hash,
        scopes=payload.scopes,
        is_active=True,
        created_by=current_user.id,
        expires_at=expires_at
    )
    db.add(key)
    db.commit()
    db.refresh(key)

    # Log to integration audits
    audit = IntegrationAuditLog(
        company_id=current_user.company_id,
        integration_type="api_key",
        action="api_key.generated",
        actor_id=current_user.id,
        status="success",
        details_json={"key_id": str(key.id), "name": key.name, "scopes": key.scopes}
    )
    db.add(audit)
    db.commit()

    resp = ApiKeyDetailResponse.model_validate(key)
    resp.raw_key = raw_key
    return resp


@router.get("", response_model=List[ApiKeyResponse])
def list_api_keys(
    current_user: RequireOwner,
    db: TenantDb
):
    stmt = select(ApiKey).where(
        ApiKey.company_id == current_user.company_id,
        ApiKey.is_active == True
    ).order_by(ApiKey.created_at.desc())
    keys = db.scalars(stmt).all()
    return list(keys)


@router.post("/{key_id}/rotate", response_model=ApiKeyDetailResponse)
def rotate_api_key(
    key_id: uuid.UUID,
    request: Request,
    current_user: RequireOwner,
    db: TenantDb
):
    key = db.scalar(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.company_id == current_user.company_id
        )
    )
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")

    raw_key = f"so_live_{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    key.key_hash = key_hash
    key.rotated_at = datetime.now(timezone.utc)
    db.add(key)
    db.commit()
    db.refresh(key)

    # Audit log
    audit = IntegrationAuditLog(
        company_id=current_user.company_id,
        integration_type="api_key",
        action="api_key.rotated",
        actor_id=current_user.id,
        status="success",
        details_json={"key_id": str(key.id), "name": key.name}
    )
    db.add(audit)
    db.commit()

    resp = ApiKeyDetailResponse.model_validate(key)
    resp.raw_key = raw_key
    return resp


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: uuid.UUID,
    current_user: RequireOwner,
    db: TenantDb
):
    key = db.scalar(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.company_id == current_user.company_id
        )
    )
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    key.is_active = False
    key.revoked_at = datetime.now(timezone.utc)
    db.add(key)
    db.commit()

    # Audit log
    audit = IntegrationAuditLog(
        company_id=current_user.company_id,
        integration_type="api_key",
        action="api_key.revoked",
        actor_id=current_user.id,
        status="success",
        details_json={"key_id": str(key.id)}
    )
    db.add(audit)
    db.commit()
    return None
