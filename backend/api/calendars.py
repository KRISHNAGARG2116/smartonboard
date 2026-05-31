import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_tenant_db, get_current_user
from models import User, Company, CalendarCredentials, OAuthState, AuditLog
from models.enums import UserRole
from core.vault import SecretVaultService
from core.calendar_provider import GoogleCalendarProvider, MicrosoftGraphProvider
from core.audit import log_audit_event
from db.session import tenant_context

router = APIRouter(prefix="/auth/calendars", tags=["calendars"])


# Whitelisted Redirect URIs for secure OAuth
ALLOWED_REDIRECT_URIS = {
    "http://mock-idp.com/oauth/google/callback",
    "http://mock-idp.com/oauth/outlook/callback",
    "http://localhost:3000/oauth/callback",
    "https://smartonboard.com/oauth/callback"
}


class ConnectRequest(BaseModel):
    provider: str  # "google" or "outlook"
    redirect_uri: str


class ConnectResponse(BaseModel):
    redirect_url: str


class CallbackRequest(BaseModel):
    provider: str  # "google" or "outlook"
    code: str
    state: str
    nonce: str | None = None
    redirect_uri: str


class SyncResponse(BaseModel):
    status: str
    message: str


def get_provider_class(provider_name: str):
    if provider_name.lower() == "google":
        return GoogleCalendarProvider()
    elif provider_name.lower() in ("outlook", "microsoft"):
        return MicrosoftGraphProvider()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported calendar provider: {provider_name}"
        )


@router.post("/connect", response_model=ConnectResponse)
def connect_calendar(
    request: Request,
    body: ConnectRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_tenant_db)
):
    provider_name = body.provider.lower()
    redirect_uri = body.redirect_uri

    # 1. Whitelist gating
    if redirect_uri not in ALLOWED_REDIRECT_URIS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redirect URI not whitelisted"
        )

    # 2. Get provider instance (to trigger check and get details)
    provider_inst = get_provider_class(provider_name)

    # 3. Generate secure state & nonce tokens
    state_token = secrets.token_urlsafe(32)
    nonce_token = secrets.token_urlsafe(32)

    state_hash = hashlib.sha256(state_token.encode("utf-8")).hexdigest()
    nonce_hash = hashlib.sha256(nonce_token.encode("utf-8")).hexdigest()

    # 4. Persist OAuth state under RLS tenant isolation
    oauth_state = OAuthState(
        company_id=current_user.company_id,
        user_id=current_user.id,
        provider=provider_name,
        state_hash=state_hash,
        nonce_hash=nonce_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    db.add(oauth_state)
    db.commit()

    # Retrieve company slug (running under tenant bypass/read)
    with tenant_context(auth_mode="true"):
        company = db.scalar(select(Company).where(Company.id == current_user.company_id))
    company_slug = company.slug if company else "unknown"

    # Append raw tokens to state so they can be sent back in the auth flow (the client receives the raw state token)
    # The callback will pass the raw state, and we will verify against the SHA-256 state_hash.
    auth_url = provider_inst.get_auth_url(company_slug, state_token)

    return ConnectResponse(redirect_url=auth_url)


@router.post("/callback")
def oauth_callback(
    request: Request,
    body: CallbackRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_tenant_db)
):
    provider_name = body.provider.lower()
    redirect_uri = body.redirect_uri

    # 1. Whitelist check
    if redirect_uri not in ALLOWED_REDIRECT_URIS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redirect URI not whitelisted"
        )

    # 2. Retrieve state
    state_hash = hashlib.sha256(body.state.encode("utf-8")).hexdigest()
    
    oauth_state = db.scalar(
        select(OAuthState).where(
            OAuthState.state_hash == state_hash,
            OAuthState.company_id == current_user.company_id
        )
    )
    if not oauth_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )

    # 3. Validate state expiration and usage
    if oauth_state.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State has expired"
        )
    if oauth_state.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State has already been consumed"
        )

    # 4. Nonce validation
    if body.nonce:
        nonce_hash = hashlib.sha256(body.nonce.encode("utf-8")).hexdigest()
        if oauth_state.nonce_hash != nonce_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nonce mismatch verification failed"
            )

    # Consumed successfully
    oauth_state.used_at = datetime.now(timezone.utc)
    db.add(oauth_state)
    db.commit()

    # 5. Exchange OAuth authorization code
    provider_inst = get_provider_class(provider_name)
    try:
        token_payload = provider_inst.exchange_code(body.code, redirect_uri)
    except Exception as e:
        log_audit_event(
            db=db,
            action="calendar.sync_failed",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"provider": provider_name, "error": f"Token exchange failed: {str(e)}"}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token exchange failed: {str(e)}"
        )

    # 6. Envelope Encryption via Vault Service
    vault = SecretVaultService()
    encrypted_access = vault.encrypt_secret(token_payload["access_token"])
    encrypted_refresh = vault.encrypt_secret(token_payload.get("refresh_token", ""))
    expires_in = token_payload.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    account_email = current_user.email  # Simulating authenticated account email

    # 7. Check if credentials already exist
    cred = db.scalar(
        select(CalendarCredentials).where(
            CalendarCredentials.company_id == current_user.company_id,
            CalendarCredentials.user_id == current_user.id,
            CalendarCredentials.provider == provider_name,
            CalendarCredentials.account_email == account_email
        )
    )

    if not cred:
        cred = CalendarCredentials(
            company_id=current_user.company_id,
            user_id=current_user.id,
            provider=provider_name,
            account_email=account_email,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            expires_at=expires_at,
            status="active"
        )
    else:
        cred.encrypted_access_token = encrypted_access
        if encrypted_refresh:
            cred.encrypted_refresh_token = encrypted_refresh
        cred.expires_at = expires_at
        cred.status = "active"
        cred.retry_count = 0
        cred.last_sync_error = None

    db.add(cred)
    db.commit()
    db.refresh(cred)

    # 8. Webhook registration if capability supported
    # Rely strictly on capability flag instead of provider name checks
    if provider_inst.supports_webhooks:
        try:
            webhook_url = f"https://smartonboard.com/api/v1/webhooks/calendar/{cred.id}"
            sub_payload = provider_inst.subscribe_webhook(
                email=account_email,
                access_token=token_payload["access_token"],
                webhook_url=webhook_url
            )
            cred.channel_id = sub_payload["subscription_id"]
            db.add(cred)
            db.commit()

            # Audit event
            log_audit_event(
                db=db,
                action="calendar.webhook_registered",
                actor_type="RECRUITER",
                actor_id=current_user.id,
                company_id=current_user.company_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={"provider": provider_name, "subscription_id": sub_payload["subscription_id"], "expires_at": sub_payload.get("expires_at")}
            )
        except Exception as e:
            # We don't block auth success if webhook subscription fails, but we log the error
            cred.last_sync_error = f"Webhook subscription failed: {str(e)}"
            db.add(cred)
            db.commit()

    # Log successful connection
    log_audit_event(
        db=db,
        action="calendar.connected",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"provider": provider_name, "account_email": account_email}
    )

    return {
        "status": "connected",
        "credential_id": str(cred.id),
        "account_email": cred.account_email,
        "provider": cred.provider
    }


@router.post("/{credential_id}/disconnect")
def disconnect_calendar(
    credential_id: str,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_tenant_db)
):
    cred = db.scalar(
        select(CalendarCredentials).where(
            CalendarCredentials.id == credential_id,
            CalendarCredentials.company_id == current_user.company_id
        )
    )
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar credentials not found"
        )

    # 1. Enforce calendar ownership check
    if cred.user_id != current_user.id and current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only the credential owner or OWNER role may disconnect calendar integrations."
        )

    provider_inst = get_provider_class(cred.provider)

    # 2. Webhook removal / cleanup if capability supported
    # Rely strictly on capability flag instead of provider name checks
    if provider_inst.supports_webhooks and cred.channel_id:
        try:
            # For simplicity, cancel webhook subscription
            vault = SecretVaultService()
            decrypted_access = vault.decrypt_secret(cred.encrypted_access_token)
            provider_inst.cancel_event(
                email=cred.account_email,
                access_token=decrypted_access,
                external_event_id=cred.channel_id
            )
            # Log webhook expiration/removal
            log_audit_event(
                db=db,
                action="calendar.webhook_expired",
                actor_type="RECRUITER",
                actor_id=current_user.id,
                company_id=current_user.company_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={"provider": cred.provider, "subscription_id": cred.channel_id}
            )
        except Exception:
            pass

    # 3. Disconnect credential
    db.delete(cred)
    db.commit()

    # 4. Audit logging
    log_audit_event(
        db=db,
        action="calendar.disconnected",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"provider": cred.provider, "account_email": cred.account_email}
    )

    return {"status": "disconnected"}


@router.post("/{credential_id}/sync", response_model=SyncResponse)
def trigger_delta_sync(
    credential_id: str,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_tenant_db)
):
    cred = db.scalar(
        select(CalendarCredentials).where(
            CalendarCredentials.id == credential_id,
            CalendarCredentials.company_id == current_user.company_id
        )
    )
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar credentials not found"
        )

    # 1. Enforce calendar ownership check
    if cred.user_id != current_user.id and current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only the credential owner or OWNER role may manage calendar integrations."
        )

    # Dispatched delta sync engine synchronously here or via background task
    # For robust manual triggers, we execute the sync call and catch exceptions
    from tasks.calendar_sync import run_delta_sync_for_credential
    try:
        run_delta_sync_for_credential(db=db, credential_id=cred.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synchronization failed: {str(e)}"
        )

    return SyncResponse(
        status="success",
        message="Incremental calendar sync completed successfully"
    )
