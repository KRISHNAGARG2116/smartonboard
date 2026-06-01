import hashlib
import json
import secrets
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select

from api.deps import RequireOwner, TenantDb
from core.audit import log_audit_event
from core.vault import SecretVaultService
from models.webhook import WebhookSubscription, WebhookDeliveryLog
from schemas.webhook import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionResponse,
    WebhookSubscriptionDetailResponse,
    WebhookDeliveryLogResponse,
)

router = APIRouter(prefix="/enterprise/webhooks", tags=["enterprise_webhooks"])


@router.post("", response_model=WebhookSubscriptionDetailResponse, status_code=status.HTTP_201_CREATED)
def create_webhook_subscription(
    body: WebhookSubscriptionCreate,
    request: Request,
    current_user: RequireOwner,
    db: TenantDb,
):
    # Generate secure, random signing key
    raw_secret = f"whsec_{secrets.token_hex(24)}"
    secret_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()

    # Encrypt raw secret key using SecretVaultService
    vault = SecretVaultService()
    encrypted_json = vault.encrypt_secret(raw_secret)
    encrypted_dict = json.loads(encrypted_json)

    subscription = WebhookSubscription(
        company_id=current_user.company_id,
        url=body.url,
        encrypted_secret=encrypted_dict["ciphertext"],
        iv=encrypted_dict["iv"],
        tag=encrypted_dict["tag"],
        key_version=encrypted_dict.get("key_version", "v1"),
        secret_key_hash=secret_hash,
        active_events=body.active_events,
        status="active",
        consecutive_failures=0,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    # Log audit event
    log_audit_event(
        db=db,
        action="webhook.subscribed",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="webhook_subscriptions",
        resource_id=str(subscription.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "subscription_id": str(subscription.id),
            "url": body.url,
            "active_events": body.active_events,
        }
    )

    # Create response with the raw secret included exactly once
    response_data = WebhookSubscriptionDetailResponse.model_validate(subscription)
    response_data.signing_secret = raw_secret
    return response_data


@router.get("", response_model=List[WebhookSubscriptionResponse])
def list_webhook_subscriptions(
    current_user: RequireOwner,
    db: TenantDb,
):
    stmt = select(WebhookSubscription).where(
        WebhookSubscription.company_id == current_user.company_id
    ).order_by(WebhookSubscription.created_at.desc())
    return list(db.scalars(stmt).all())


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook_subscription(
    subscription_id: uuid.UUID,
    request: Request,
    current_user: RequireOwner,
    db: TenantDb,
):
    subscription = db.scalar(
        select(WebhookSubscription).where(
            WebhookSubscription.id == subscription_id,
            WebhookSubscription.company_id == current_user.company_id
        )
    )
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")

    db.delete(subscription)
    db.commit()

    # Log audit event
    log_audit_event(
        db=db,
        action="webhook.unsubscribed",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="webhook_subscriptions",
        resource_id=str(subscription_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "subscription_id": str(subscription_id),
            "url": subscription.url,
        }
    )


@router.get("/{subscription_id}/logs", response_model=List[WebhookDeliveryLogResponse])
def get_webhook_delivery_logs(
    subscription_id: uuid.UUID,
    current_user: RequireOwner,
    db: TenantDb,
):
    # Verify subscription exists and belongs to the company
    subscription = db.scalar(
        select(WebhookSubscription).where(
            WebhookSubscription.id == subscription_id,
            WebhookSubscription.company_id == current_user.company_id
        )
    )
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")

    stmt = select(WebhookDeliveryLog).where(
        WebhookDeliveryLog.subscription_id == subscription_id,
        WebhookDeliveryLog.company_id == current_user.company_id
    ).order_by(WebhookDeliveryLog.executed_at.desc()).limit(100)

    return list(db.scalars(stmt).all())
