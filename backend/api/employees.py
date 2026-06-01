import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from db.session import get_db, tenant_context, set_tenant_context, tenant_id_var
from api.deps import TenantDb, RequireRecruiter, PortalSession, PortalDb, get_portal_session, get_portal_db
from schemas.employee import (
    EmployeeConvertRequest,
    EmployeeConvertResponse,
    EmployeeResponse,
    HRISFieldMappingCreate,
    HRISFieldMappingResponse,
    SyncMetricResponse,
    DLQRecordResponse,
    EmployeeSyncHistoryResponse,
    PortalAuthRequest,
    PortalAuthResponse,
    PortalChecklistResponse,
    PortalTaskResponse,
    DocumentSignRequest,
    DocumentSignResponse,
    OnboardingActivityLogResponse,
    EmployeeOnboardingProgressResponse,
    EscalationResolveRequest
)
from core.lifecycle import CandidateToEmployeeService
from models import (
    Employee,
    HRISFieldMapping,
    SyncMetric,
    DLQRecord,
    EmployeeSyncHistory,
    OnboardingEventOutbox,
    OnboardingPortalToken,
    OnboardingDocumentSignature,
    OnboardingTaskReminder,
    OnboardingTaskEscalation,
    OnboardingActivityLog,
    OnboardingWorkflow,
    OnboardingTask,
    OnboardingDocument,
    Company
)

router = APIRouter(prefix="", tags=["employees"])

@router.post("/applications/{application_id}/convert", response_model=EmployeeConvertResponse, status_code=status.HTTP_201_CREATED)
def convert_candidate(
    application_id: uuid.UUID,
    body: EmployeeConvertRequest,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb
):
    """
    Atomically converts a candidate application into an employee profile.
    Sets application status to hired, creates the Employee record, instantiates
    the onboarding checklist, and logs audit and outbox events.
    """
    try:
        employee = CandidateToEmployeeService.convert_candidate_to_employee(
            db=db,
            application_id=application_id,
            employment_type=body.employment_type,
            employee_number=body.employee_number,
            supervisor_id=body.supervisor_id,
            current_user_id=current_user.id,
            request_ip=request.client.host if request.client else None,
            request_ua=request.headers.get("user-agent"),
            company_id=current_user.company_id
        )
        
        workflow_id = None
        if employee.onboarding_workflow:
            workflow_id = employee.onboarding_workflow.id
            
        return EmployeeConvertResponse(
            id=employee.id,
            email=employee.email,
            full_name=employee.full_name,
            job_title=employee.job_title,
            employment_type=employee.employment_type,
            employee_number=employee.employee_number,
            status=employee.status,
            start_date=employee.start_date,
            workflow_id=workflow_id
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "already exists" in msg.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee with this email or employee number already exists"
        )


@router.get("/employees", response_model=list[EmployeeResponse])
def list_employees(
    current_user: RequireRecruiter,
    db: TenantDb
):
    """
    List employee profiles for the company.
    RLS enforces that recruiters only see their own company's employee records.
    """
    stmt = select(Employee).where(Employee.company_id == current_user.company_id).order_by(Employee.created_at.desc())
    employees = db.scalars(stmt).all()
    return list(employees)


@router.post("/employees/mappings", response_model=HRISFieldMappingResponse, status_code=status.HTTP_201_CREATED)
def create_field_mapping(
    body: HRISFieldMappingCreate,
    current_user: RequireRecruiter,
    db: TenantDb
):
    """
    Creates or updates a custom field mapping mapping for a specific provider.
    """
    # Check if duplicate key exists
    stmt = select(HRISFieldMapping).where(
        HRISFieldMapping.company_id == current_user.company_id,
        HRISFieldMapping.provider == body.provider.lower(),
        HRISFieldMapping.local_field == body.local_field
    )
    mapping = db.scalar(stmt)
    
    if mapping:
        mapping.provider_field = body.provider_field
        mapping.is_custom = body.is_custom
        mapping.transform_rules = body.transform_rules
    else:
        mapping = HRISFieldMapping(
            company_id=current_user.company_id,
            provider=body.provider.lower(),
            local_field=body.local_field,
            provider_field=body.provider_field,
            is_custom=body.is_custom,
            transform_rules=body.transform_rules
        )
        db.add(mapping)
        
    db.commit()
    db.refresh(mapping)
    return mapping


@router.get("/employees/metrics", response_model=list[SyncMetricResponse])
def list_sync_metrics(
    current_user: RequireRecruiter,
    db: TenantDb
):
    """
    List sync metrics for dashboard visualization.
    """
    stmt = select(SyncMetric).where(
        SyncMetric.company_id == current_user.company_id
    ).order_by(SyncMetric.timestamp.desc()).limit(100)
    metrics = db.scalars(stmt).all()
    return list(metrics)


@router.get("/employees/dlq", response_model=list[DLQRecordResponse])
def list_dlq_records(
    current_user: RequireRecruiter,
    db: TenantDb
):
    """
    Lists failed outbox transfers inside the Dead Letter Queue.
    """
    stmt = select(DLQRecord).where(
        DLQRecord.company_id == current_user.company_id
    ).order_by(DLQRecord.created_at.desc())
    records = db.scalars(stmt).all()
    return list(records)


@router.post("/employees/dlq/{id}/retry", response_model=DLQRecordResponse)
def retry_dlq_record(
    id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb
):
    """
    Manually overrides a DLQ sync failure, launching a background retry execution.
    Transitions employee state back to manual_review and triggers sync worker.
    """
    dlq = db.scalar(select(DLQRecord).where(
        DLQRecord.company_id == current_user.company_id,
        DLQRecord.id == id
    ))
    
    if not dlq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DLQ record not found")
        
    outbox = db.scalar(select(OnboardingEventOutbox).where(
        OnboardingEventOutbox.id == dlq.outbox_id
    ))
    
    if outbox:
        # Reset outbox status to queued
        outbox.status = "queued"
        outbox.retry_count = 0
        db.add(outbox)
        
        employee_id_str = outbox.payload.get("employee_id")
        if employee_id_str:
            emp = db.scalar(select(Employee).where(Employee.id == uuid.UUID(employee_id_str)))
            if emp:
                emp.sync_status = "manual_review"
                db.add(emp)
                
                # Write to history logs
                from tasks.hris import log_sync_history_record, sync_employee_to_hris_task
                import hashlib
                import json
                
                payload_str = json.dumps(outbox.payload, sort_keys=True)
                p_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
                
                log_sync_history_record(
                    db=db,
                    company_id=current_user.company_id,
                    employee_id=emp.id,
                    provider=dlq.provider,
                    request_id=outbox.id,
                    state="manual_review",
                    attempt=1,
                    started_at=datetime.now(timezone.utc),
                    payload_hash=p_hash
                )

    # Resolve DLQ Record status
    dlq.status = "resolved"
    dlq.resolved_at = datetime.now(timezone.utc)
    dlq.resolved_by_id = current_user.id
    db.add(dlq)
    
    db.commit()
    db.refresh(dlq)

    # Trigger Celery Task directly after committing changes to release row locks
    if outbox:
        from tasks.hris import sync_employee_to_hris_task
        sync_employee_to_hris_task.delay(str(outbox.id))

    return dlq


@router.get("/employees/{employee_id}/sync-history", response_model=list[EmployeeSyncHistoryResponse])
def get_employee_sync_history(
    employee_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb
):
    """
    List state transition history logs for a specific employee.
    """
    # First verify employee exists and belongs to the company (defense-in-depth API lock)
    emp = db.scalar(select(Employee).where(
        Employee.company_id == current_user.company_id,
        Employee.id == employee_id
    ))
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    stmt = select(EmployeeSyncHistory).where(
        EmployeeSyncHistory.company_id == current_user.company_id,
        EmployeeSyncHistory.employee_id == employee_id
    ).order_by(EmployeeSyncHistory.created_at.asc())
    
    history = db.scalars(stmt).all()
    return list(history)


@router.post("/onboarding/portal/authenticate", response_model=PortalAuthResponse)
def authenticate_portal(
    body: PortalAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Exchange a high-entropy portal token for an ephemeral 4-hour JWT session.
    """
    import hashlib
    token_hash = hashlib.sha256(body.token.encode("utf-8")).hexdigest()
    
    # RLS bypass to verify the portal token across all tenants securely
    with tenant_context(auth_mode="true"):
        portal_token = db.scalar(
            select(OnboardingPortalToken).where(
                OnboardingPortalToken.token_hash == token_hash,
                OnboardingPortalToken.is_revoked.is_(False),
                OnboardingPortalToken.expires_at > datetime.now(timezone.utc)
            )
        )
        if not portal_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid, expired or revoked portal token")
            
        emp = db.scalar(select(Employee).where(Employee.id == portal_token.employee_id))
        if not emp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Associated employee profile not found")
            
        comp = db.scalar(select(Company).where(Company.id == portal_token.company_id))
        comp_name = comp.name if comp else ""

    # Set context variables
    tenant_id_var.set(str(portal_token.company_id))
    set_tenant_context(db, str(portal_token.company_id))

    # Log Portal Authentication in timeline
    from core.signatures import log_onboarding_activity
    log_onboarding_activity(
        db=db,
        company_id=portal_token.company_id,
        employee_id=portal_token.employee_id,
        actor_id=portal_token.employee_id,
        actor_type="candidate",
        event_type="portal_authenticated",
        metadata={"token_id": str(portal_token.id)}
    )
    
    # Log Audit Log
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="onboarding.portal_authenticated",
        actor_type="candidate",
        company_id=portal_token.company_id,
        actor_id=portal_token.employee_id,
        resource_type="onboarding_portal_token",
        resource_id=str(portal_token.id)
    )
    db.commit()

    # Generate the short-lived portal token payload (4 hours)
    from jose import jwt
    from core.config import get_settings
    from datetime import timedelta
    import uuid
    
    settings = get_settings()
    expires_in_seconds = 14400
    expire = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
    payload = {
        "sub": str(portal_token.employee_id),
        "company_id": str(portal_token.company_id),
        "scopes": portal_token.access_scopes,
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": "portal"
    }
    access_token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    return PortalAuthResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        employee_id=portal_token.employee_id,
        full_name=emp.full_name,
        company_name=comp_name
    )


@router.get("/onboarding/portal/checklist", response_model=PortalChecklistResponse)
def get_portal_checklist(
    portal_session: PortalSession,
    db: PortalDb
):
    """
    Returns the dynamic checklist and task statuses for the pre-boarding candidate.
    """
    employee_id = portal_session["employee_id"]
    company_id = portal_session["company_id"]
    
    if "onboarding:read" not in portal_session["scopes"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient portal scope privileges")

    wf = db.scalar(select(OnboardingWorkflow).where(
        OnboardingWorkflow.company_id == company_id,
        OnboardingWorkflow.employee_id == employee_id
    ))
    if not wf:
        return PortalChecklistResponse(
            employee_id=employee_id,
            completion_percentage=0.0,
            tasks=[]
        )
        
    tasks = db.scalars(select(OnboardingTask).where(
        OnboardingTask.workflow_id == wf.id
    ).order_by(OnboardingTask.sequence.asc())).all()
    
    portal_tasks = []
    completed_count = 0
    total_count = 0
    
    for t in tasks:
        requires_sig = False
        doc_id = None
        doc_name = None
        
        if t.task_type == "document_signature":
            doc = db.scalar(select(OnboardingDocument).where(OnboardingDocument.task_id == t.id))
            if doc:
                requires_sig = doc.signature_status in ("pending_candidate", "pending_company") or doc.signature_status == "signed"
                doc_id = doc.id
                doc_name = doc.document_name
                
        portal_tasks.append(PortalTaskResponse(
            id=t.id,
            title=t.title,
            description=t.description,
            status=t.status,
            task_type=t.task_type,
            due_date=t.due_date,
            requires_signature=requires_sig,
            document_id=doc_id,
            document_name=doc_name
        ))
        
        total_count += 1
        if t.status == "completed":
            completed_count += 1
            
    completion_percentage = (completed_count / total_count * 100.0) if total_count > 0 else 0.0
    
    return PortalChecklistResponse(
        employee_id=employee_id,
        completion_percentage=round(completion_percentage, 2),
        tasks=portal_tasks
    )


@router.post("/onboarding/portal/documents/{id}/sign", response_model=DocumentSignResponse)
def sign_portal_document(
    id: uuid.UUID,
    body: DocumentSignRequest,
    request: Request,
    portal_session: PortalSession,
    db: PortalDb
):
    """
    Digitally sign a compliance document inside the onboarding checklist.
    Computes a cryptographic signature fingerprint and updates task status.
    """
    employee_id = portal_session["employee_id"]
    company_id = portal_session["company_id"]
    
    if "onboarding:write" not in portal_session["scopes"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient portal scope privileges")

    if not body.agree_to_electronic_terms:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You must agree to electronic signature terms to sign this document")

    doc = db.scalar(select(OnboardingDocument).where(
        OnboardingDocument.company_id == company_id,
        OnboardingDocument.id == id
    ))
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding document not found")
        
    if doc.signature_status == "signed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document has already been signed")

    from core.signatures import OnboardingSignatureService
    
    ip_addr = request.client.host if request.client else "0.0.0.0"
    ua = request.headers.get("user-agent", "unknown")
    
    try:
        sig = OnboardingSignatureService.sign_document(
            db=db,
            employee_id=employee_id,
            document_id=id,
            signer_name=body.signer_name,
            signature_text=body.signature_text,
            ip_address=ip_addr,
            user_agent=ua,
            actor_id=employee_id,
            actor_type="candidate"
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        
    return DocumentSignResponse(
        signature_id=sig.id,
        document_id=id,
        signature_hash=sig.signature_hash,
        signed_at=sig.signed_at
    )


@router.get("/employees/{employee_id}/onboarding-progress", response_model=EmployeeOnboardingProgressResponse)
def get_recruiter_onboarding_progress(
    employee_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb
):
    """
    Oversight endpoint for recruiters to view detailed onboarding task metrics and overdue flags.
    """
    emp = db.scalar(select(Employee).where(
        Employee.company_id == current_user.company_id,
        Employee.id == employee_id
    ))
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    wf = db.scalar(select(OnboardingWorkflow).where(
        OnboardingWorkflow.company_id == current_user.company_id,
        OnboardingWorkflow.employee_id == employee_id
    ))
    if not wf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding workflow has not been initialized for this employee")
        
    tasks = db.scalars(select(OnboardingTask).where(
        OnboardingTask.workflow_id == wf.id
    ).order_by(OnboardingTask.sequence.asc())).all()
    
    portal_tasks = []
    completed_count = 0
    total_count = 0
    overdue_count = 0
    now = datetime.now(timezone.utc).date()
    
    for t in tasks:
        requires_sig = False
        doc_id = None
        doc_name = None
        
        if t.task_type == "document_signature":
            doc = db.scalar(select(OnboardingDocument).where(OnboardingDocument.task_id == t.id))
            if doc:
                requires_sig = doc.signature_status in ("pending_candidate", "pending_company") or doc.signature_status == "signed"
                doc_id = doc.id
                doc_name = doc.document_name
                
        portal_tasks.append(PortalTaskResponse(
            id=t.id,
            title=t.title,
            description=t.description,
            status=t.status,
            task_type=t.task_type,
            due_date=t.due_date,
            requires_signature=requires_sig,
            document_id=doc_id,
            document_name=doc_name
        ))
        
        total_count += 1
        if t.status == "completed":
            completed_count += 1
        elif t.status == "pending" and t.due_date and t.due_date < now:
            overdue_count += 1
            
    return EmployeeOnboardingProgressResponse(
        employee_id=employee_id,
        status=wf.status,
        completed_tasks=completed_count,
        total_tasks=total_count,
        overdue_tasks=overdue_count,
        tasks=portal_tasks
    )


@router.post("/employees/tasks/{task_id}/escalations/resolve")
def resolve_onboarding_escalation(
    task_id: uuid.UUID,
    body: EscalationResolveRequest,
    current_user: RequireRecruiter,
    db: TenantDb
):
    """
    Manually overrides and resolves active escalations for an onboarding task.
    """
    task = db.scalar(select(OnboardingTask).where(
        OnboardingTask.company_id == current_user.company_id,
        OnboardingTask.id == task_id
    ))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding task not found")

    escalations = db.scalars(select(OnboardingTaskEscalation).where(
        OnboardingTaskEscalation.company_id == current_user.company_id,
        OnboardingTaskEscalation.task_id == task_id,
        OnboardingTaskEscalation.resolved_at.is_(None)
    )).all()
    
    if not escalations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active escalations found for this onboarding task")

    now = datetime.now(timezone.utc)
    for esc in escalations:
        esc.resolved_at = now
        esc.acknowledged_at = now
        db.add(esc)

    # Fetch workflow & employee to log activity log
    wf = db.get(OnboardingWorkflow, task.workflow_id)
    employee_id = wf.employee_id if wf else None

    if employee_id:
        from core.signatures import log_onboarding_activity
        log_onboarding_activity(
            db=db,
            company_id=current_user.company_id,
            employee_id=employee_id,
            actor_id=current_user.id,
            actor_type="recruiter",
            event_type="escalation_resolved",
            metadata={
                "task_id": str(task_id),
                "task_title": task.title,
                "resolution_notes": body.resolution_notes
            }
        )

    # Log Audit Event
    from core.audit import log_audit_event
    log_audit_event(
        db=db,
        action="onboarding.escalation_resolved",
        actor_type="recruiter",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        resource_type="onboarding_task",
        resource_id=str(task_id),
        metadata={"resolution_notes": body.resolution_notes}
    )

    db.commit()
    return {"status": "resolved", "resolved_escalations": len(escalations)}


from fastapi import Query

@router.get("/employees/{employee_id}/activity", response_model=list[OnboardingActivityLogResponse])
def get_employee_activity_timeline(
    employee_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb,
    limit: int = Query(default=50, ge=1, le=250),
    offset: int = Query(default=0, ge=0)
):
    """
    Returns the chronological onboarding activity log timeline for an employee, bound strictly by company RLS.
    """
    emp = db.scalar(select(Employee).where(
        Employee.company_id == current_user.company_id,
        Employee.id == employee_id
    ))
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    stmt = select(OnboardingActivityLog).where(
        OnboardingActivityLog.company_id == current_user.company_id,
        OnboardingActivityLog.employee_id == employee_id
    ).order_by(OnboardingActivityLog.created_at.asc()).limit(limit).offset(offset)
    
    activities = db.scalars(stmt).all()
    return list(activities)

