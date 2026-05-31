import uuid
import csv
import io
import json
from datetime import datetime
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from api.deps import RequireOwner, TenantDb
from models import AuditLog
from models.enums import UserRole
from schemas.audit import AuditLogResponse
from core.audit import log_audit_event
from core.archive import LocalArchiveProvider, archive_old_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogResponse])
def search_audit_logs(
    db: TenantDb,
    current_user: RequireOwner,
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    action: Optional[str] = Query(default=None),
    actor_type: Optional[str] = Query(default=None),
    resource_type: Optional[str] = Query(default=None),
    resource_id: Optional[str] = Query(default=None),
    sort_by: str = Query(default="timestamp"),
    sort_order: str = Query(default="desc"),
    limit: int = Query(default=50, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
):
    """Expose secure search and filtering of audit logs, bound strictly by company RLS."""
    stmt = select(AuditLog).where(AuditLog.company_id == current_user.company_id)
    
    if start_date:
        stmt = stmt.where(AuditLog.timestamp >= start_date)
    if end_date:
        stmt = stmt.where(AuditLog.timestamp <= end_date)
    if action:
        if "%" in action or "_" in action:
            stmt = stmt.where(AuditLog.action.like(action))
        else:
            stmt = stmt.where(AuditLog.action == action)
    if actor_type:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(AuditLog.resource_id == resource_id)
        
    order_col = getattr(AuditLog, sort_by, AuditLog.timestamp)
    if sort_order.lower() == "asc":
        stmt = stmt.order_by(order_col.asc())
    else:
        stmt = stmt.order_by(order_col.desc())
        
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


@router.get("/logs/export")
def export_audit_logs(
    request: Request,
    db: TenantDb,
    current_user: RequireOwner,
    format: str = Query(default="csv"),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    action: Optional[str] = Query(default=None),
    actor_type: Optional[str] = Query(default=None),
):
    """Export audit logs as CSV or JSON stream for compliance review."""
    # 1. Fetch filtered logs
    stmt = select(AuditLog).where(AuditLog.company_id == current_user.company_id).order_by(AuditLog.timestamp.desc())
    if start_date:
        stmt = stmt.where(AuditLog.timestamp >= start_date)
    if end_date:
        stmt = stmt.where(AuditLog.timestamp <= end_date)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if actor_type:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
        
    logs = db.scalars(stmt).all()
    
    # 2. Log export action in the audit trail
    log_audit_event(
        db=db,
        action="security.audit_exported",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"format": format, "log_count": len(logs)}
    )
    
    if format.lower() == "json":
        # Stream JSON
        log_list = []
        for log in logs:
            log_list.append({
                "id": str(log.id),
                "timestamp": log.timestamp.isoformat(),
                "action": log.action,
                "actor_type": log.actor_type,
                "actor_id": str(log.actor_id) if log.actor_id else None,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "ip_address": log.ip_address,
                "metadata_json": log.metadata_json
            })
        json_content = json.dumps(log_list, indent=2)
        return StreamingResponse(
            io.StringIO(json_content),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_export.json"}
        )
    else:
        # Stream CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Timestamp", "Action", "Actor Type", "Actor ID", "Resource Type", "Resource ID", "IP Address", "Metadata"])
        for log in logs:
            writer.writerow([
                str(log.id),
                log.timestamp.isoformat(),
                log.action,
                log.actor_type,
                str(log.actor_id) if log.actor_id else "",
                log.resource_type or "",
                log.resource_id or "",
                log.ip_address or "",
                json.dumps(log.metadata_json) if log.metadata_json else ""
            ])
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_export.csv"}
        )


@router.post("/archive/run", status_code=status.HTTP_200_OK)
def run_archival_worker(
    db: TenantDb,
    current_user: RequireOwner,
    days: int = Query(default=90, ge=0)
):
    """Archival worker endpoint to cold-archive logs older than X days using the storage abstraction."""
    local_provider = LocalArchiveProvider()
    archive_uri = archive_old_audit_logs(db=db, company_id=current_user.company_id, provider=local_provider, days=days)
    
    if not archive_uri:
        return {"success": True, "detail": "No logs matching cutoff date found for archival", "uri": None}
        
    return {"success": True, "detail": "Audit logs archived successfully", "uri": archive_uri}


@router.get("/archive/retrieve")
def retrieve_archived_batch(
    filename: str,
    db: TenantDb,
    current_user: RequireOwner
):
    """Retrieve cold-archived audit batches verifying strict tenant isolation."""
    # 1. Enforce tenant isolation by verifying the company ID prefix in the filename
    company_id_str = str(current_user.company_id)
    if f"audit_archive_{company_id_str}" not in filename:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permissions to access this archive batch."
        )
        
    # 2. Retrieve the batch using LocalArchiveProvider
    local_provider = LocalArchiveProvider()
    try:
        content = local_provider.download_archive(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive batch not found")
        
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
