import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from api.deps import TenantDb, RequireRecruiter
from schemas.employee import (
    EmployeeConvertRequest,
    EmployeeConvertResponse,
    EmployeeResponse,
    HRISFieldMappingCreate,
    HRISFieldMappingResponse,
    SyncMetricResponse,
    DLQRecordResponse,
    EmployeeSyncHistoryResponse
)
from core.lifecycle import CandidateToEmployeeService
from models import Employee, HRISFieldMapping, SyncMetric, DLQRecord, EmployeeSyncHistory, OnboardingEventOutbox

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
