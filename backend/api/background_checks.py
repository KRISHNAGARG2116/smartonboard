import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from api.deps import RequireRecruiter, TenantDb, RequireOwner
from models.background_check import BackgroundCheckRecord
from models.application import Application
from models.candidate import Candidate
from models.integration_audit_log import IntegrationAuditLog
from integrations.base.factory import ProviderFactory

router = APIRouter(prefix="/background-checks", tags=["background_checks"])


class BackgroundCheckTriggerPayload(BaseModel):
    application_id: uuid.UUID
    provider: str  # 'checkr', 'certn'
    check_type: str  # 'criminal', 'employment', 'identity'


class BackgroundCheckResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    provider: str
    check_type: str
    status: str
    result: str | None
    external_check_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/trigger", response_model=BackgroundCheckResponse, status_code=status.HTTP_201_CREATED)
def trigger_background_check(
    payload: BackgroundCheckTriggerPayload,
    current_user: RequireRecruiter,
    db: TenantDb
):
    # Verify application ownership
    app = db.scalar(
        select(Application).where(
            Application.id == payload.application_id,
            Application.company_id == current_user.company_id
        )
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    candidate = db.scalar(select(Candidate).where(Candidate.id == app.candidate_id))
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    # Instantiate provider check
    try:
        provider = ProviderFactory.get_provider("background_check", payload.provider)
        credentials = {"api_key": "mock_api_key"}
        candidate_data = {"email": candidate.email, "name": candidate.full_name}
        
        result = provider.trigger_check(candidate_data, payload.check_type, credentials)
        
        # Save record
        record = BackgroundCheckRecord(
            company_id=current_user.company_id,
            application_id=payload.application_id,
            provider=payload.provider,
            check_type=payload.check_type,
            status=result["status"],
            external_check_id=result["external_check_id"]
        )
        db.add(record)
        
        # Emit billing event
        from core.workflow_engine import emit_billing_event
        emit_billing_event(db, current_user.company_id, "background_check.started", str(record.id))
        
        db.commit()
        db.refresh(record)

        # Log audit trail
        audit = IntegrationAuditLog(
            company_id=current_user.company_id,
            integration_type="background_check",
            action="background_check.started",
            actor_id=current_user.id,
            status="success",
            details_json={"provider": payload.provider, "check_type": payload.check_type, "record_id": str(record.id)}
        )
        db.add(audit)
        db.commit()

        return record
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/records/{application_id}", response_model=List[BackgroundCheckResponse])
def get_background_check_records(
    application_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb
):
    stmt = select(BackgroundCheckRecord).where(
        BackgroundCheckRecord.application_id == application_id,
        BackgroundCheckRecord.company_id == current_user.company_id
    )
    records = db.scalars(stmt).all()
    return list(records)


@router.post("/public/webhooks/{provider}")
def public_background_check_webhook(
    provider: str,
    payload: dict,
    db: TenantDb
):
    # Public endpoint called by background check systems to update statuses
    from db.session import tenant_context
    external_check_id = payload.get("id") or payload.get("external_check_id")
    check_status = payload.get("status")  # 'completed', 'failed'
    check_result = payload.get("result")  # 'clear', 'review'

    with tenant_context(auth_mode="true"):
        record = db.scalar(
            select(BackgroundCheckRecord).where(
                BackgroundCheckRecord.external_check_id == external_check_id,
                BackgroundCheckRecord.provider == provider
            )
        )
        if record:
            record.status = check_status
            record.result = check_result
            record.updated_at = datetime.now(timezone.utc)
            db.add(record)

            # Audit log
            audit = IntegrationAuditLog(
                company_id=record.company_id,
                integration_type="background_check",
                action=f"background_check.{check_status}",
                status="success",
                details_json={"provider": provider, "status": check_status, "result": check_result}
            )
            db.add(audit)
            db.commit()

    return {"status": "received"}
