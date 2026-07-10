import uuid
import hashlib
from datetime import datetime, timezone
from typing import Annotated, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from api.deps import TenantDb, RequireRecruiter
from models.audit import AuditLog
from db.session import tenant_context

router = APIRouter(prefix="/security-audit", tags=["security_audit"])


@router.get("/logs")
def get_security_audit_logs(
    db: TenantDb,
    current_user: RequireRecruiter
):
    """Retrieves all immutable audit log events associated with this tenant."""
    logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.company_id == current_user.company_id)
        .order_by(AuditLog.timestamp.desc())
    ).all()
    
    return [
        {
            "id": str(log.id),
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "actor_type": log.actor_type,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "timestamp": log.timestamp.isoformat(),
            "metadata": log.metadata_json
        }
        for log in logs
    ]


@router.get("/verify-integrity")
def verify_audit_log_integrity(
    db: TenantDb,
    current_user: RequireRecruiter
):
    """
    Validates the cryptographic hash chain of all audit logs sequentially.
    Returns details on any detected gaps or modifications.
    """
    # Fetch all logs from the database sequentially
    with tenant_context(auth_mode="true"):
        logs = db.scalars(
            select(AuditLog).order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
        ).all()

    if not logs:
        return {"status": "success", "verified_records": 0, "tamper_detected": False}

    prev_hash = "0" * 64
    verified_count = 0
    tamper_detected = False
    details = []

    for log in logs:
        meta = log.metadata_json or {}
        stored_hash = meta.get("hash_chain")
        stored_prev_hash = meta.get("prev_hash_chain")

        if not stored_hash or not stored_prev_hash:
            # Skip old logs populated before hash chaining was active
            continue

        # Recalculate hash
        act_uuid = str(log.actor_id) if log.actor_id else "None"
        timestamp_str = log.timestamp.isoformat()
        record_content = f"{act_uuid}|{log.action}|{timestamp_str}|{prev_hash}"
        computed_hash = hashlib.sha256(record_content.encode()).hexdigest()

        if computed_hash != stored_hash or stored_prev_hash != prev_hash:
            tamper_detected = True
            details.append({
                "record_id": str(log.id),
                "action": log.action,
                "timestamp": log.timestamp.isoformat(),
                "error": "Hash mismatch or chain breakage detected."
            })
            break

        prev_hash = stored_hash
        verified_count += 1

    if tamper_detected:
        raise HTTPException(
            status_code=status.HTTP_418_IM_A_TEAPOT,  # Cryptographic warning
            detail={"status": "tampered", "verified_records": verified_count, "details": details}
        )

    return {
        "status": "success",
        "verified_records": verified_count,
        "tamper_detected": False
    }
