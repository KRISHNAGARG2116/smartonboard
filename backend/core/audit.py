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
    if metadata is None:
        metadata = {}
    if actor_id and actor_type == "candidate":
        metadata["candidate_actor_id"] = str(actor_id)
        
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
    if actor_id and actor_type != "candidate":
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


from sqlalchemy import select, text

DEFAULT_SCRUB_LIST = [
    "name", "full_name", "first_name", "last_name", "email", "personal_email",
    "work_email", "phone", "mobile", "telephone", "address", "city", "state",
    "country", "postal_code", "linkedin", "github", "portfolio_url", "website",
    "resume_text", "resume_url", "resume_file", "cover_letter", "candidate_notes",
    "assessment_answers", "candidate_links", "candidate_id_external", "ip_address",
    "ai_explanation", "ai_reasoning", "ai_summary", "ai_feedback"
]

def recursively_scrub_metadata(data, scrub_set, marker="[PSEUDONYMIZED]"):
    """Recursively scrub sensitive keys from metadata dictionary or list."""
    if isinstance(data, dict):
        scrubbed = {}
        for k, v in data.items():
            if k.lower() in scrub_set:
                scrubbed[k] = marker
            else:
                scrubbed[k] = recursively_scrub_metadata(v, scrub_set, marker)
        return scrubbed
    elif isinstance(data, list):
        return [recursively_scrub_metadata(item, scrub_set, marker) for item in data]
    else:
        return data


def pseudonymize_audit_logs(
    db: Session,
    candidate_id: str | uuid.UUID,
    candidate_email: str | None = None,
    custom_scrub_list: list[str] = None,
    commit: bool = True
) -> int:
    """Scrub personal data recursively from historical audit logs to comply with GDPR Right-to-Be-Forgotten.
    
    Finds and updates any logs associated with the candidate_id or email, recursively scrubbing
    the 31 default keys in their metadata_json payloads and masking client IP addresses.
    
    Returns the count of modified logs.
    """
    scrub_fields = custom_scrub_list if custom_scrub_list is not None else DEFAULT_SCRUB_LIST
    scrub_set = {f.lower() for f in scrub_fields}
    
    candidate_id_str = str(candidate_id)
    email_str = candidate_email.lower() if candidate_email else None
    
    modified_count = 0
    with tenant_context(auth_mode="true"):
        # 1. Query for candidate-related audit logs under auth_mode="true" to bypass RLS restrictions
        logs_stmt = select(AuditLog)
        all_logs = db.scalars(logs_stmt).all()
        
        matched_logs = []
        for log in all_logs:
            matches = False
            if log.actor_id and str(log.actor_id) == candidate_id_str:
                matches = True
            elif log.resource_id and log.resource_id == candidate_id_str:
                matches = True
                
            # Inspect metadata
            if log.metadata_json:
                meta_str = str(log.metadata_json).lower()
                if candidate_id_str in meta_str:
                    matches = True
                elif email_str and email_str in meta_str:
                    matches = True
                    
            if matches:
                matched_logs.append(log)
                
        # 2. Scrub metadata recursively and mask column values
        db.execute(text("SELECT set_config('app.bypass_audit_immutability', 'true', true)"))
        for log in matched_logs:
            # Recursive metadata scrubbing
            if log.metadata_json:
                log.metadata_json = recursively_scrub_metadata(log.metadata_json, scrub_set)
                
            # Column-level IP address scrubbing
            if "ip_address" in scrub_set and log.ip_address:
                log.ip_address = "[PSEUDONYMIZED]"
                
            db.add(log)
            modified_count += 1
            
        if modified_count > 0 and commit:
            db.commit()
        if commit:
            db.execute(text("SELECT set_config('app.bypass_audit_immutability', 'false', true)"))
            
    return modified_count
