import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.audit import AuditLog
from db.session import tenant_context, tenant_id_var

logger = logging.getLogger("security")


def sanitize_metadata(data: dict) -> dict:
    """Recursively sanitize metadata payloads to strip passwords, tokens, and secrets."""
    if not data:
        return {}
    sanitized = {}
    forbidden_keywords = {
        "password",
        "pass",
        "pwd",
        "token",
        "secret",
        "key",
        "api_key",
        "authorization",
        "auth",
    }
    for k, v in data.items():
        k_lower = k.lower()
        if any(keyword in k_lower for keyword in forbidden_keywords):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_metadata(v)
        elif isinstance(v, list):
            sanitized[k] = [
                sanitize_metadata(item) if isinstance(item, dict) else item for item in v
            ]
        else:
            sanitized[k] = v
    return sanitized


def log_audit_event(
    db: Session,
    action: str,
    actor_type: str,
    company_id: str | uuid.UUID | None = None,
    actor_id: str | uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    """Create a sanitized, immutable audit log entry.

    Ensures that DB-level RLS policies are bypassed during the append operation
    to prevent logging insertion deadlocks on unauthenticated paths.
    """
    # 1. Resolve company_id from context if not explicitly provided
    resolved_company_id = company_id
    if not resolved_company_id:
        active_tenant = tenant_id_var.get()
        if active_tenant:
            resolved_company_id = active_tenant

    # 2. Sanitize metadata
    sanitized_meta = sanitize_metadata(metadata)

    # 3. Handle UUID parsing
    comp_uuid = None
    if resolved_company_id:
        comp_uuid = (
            uuid.UUID(str(resolved_company_id))
            if isinstance(resolved_company_id, str)
            else resolved_company_id
        )

    act_uuid = None
    if actor_id:
        act_uuid = (
            uuid.UUID(str(actor_id)) if isinstance(actor_id, str) else actor_id
        )

    # 4. Write to DB under tenant bypass context
    with tenant_context(auth_mode="true"):
        log_entry = AuditLog(
            company_id=comp_uuid,
            actor_id=act_uuid,
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=sanitized_meta,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

    # 5. Mirror to system security logger for log collection systems (ELK, CloudWatch, etc.)
    logger.info(
        f"AUDIT EVENT: action={action} company_id={comp_uuid} actor_type={actor_type} actor_id={act_uuid}"
    )
    return log_entry
