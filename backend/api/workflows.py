import json
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.deps import RequireRecruiter, TenantDb, RequireOwner
from models.workflow import WorkflowRule, WorkflowRun
from models.webhook import WebhookDeliveryLog
from core.workflow_engine import WorkflowEngine, execute_workflow_run_task
from core.audit import log_audit_event
from models.integration_audit_log import IntegrationAuditLog

router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowRuleCreate(BaseModel):
    name: str
    trigger_type: str
    conditions_json: dict = Field(default_factory=dict)
    actions_json: list = Field(default_factory=list)


class WorkflowRuleResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    parent_rule_id: uuid.UUID | None
    name: str
    version: int
    status: str
    trigger_type: str
    conditions_json: dict
    actions_json: list
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SimulateRequest(BaseModel):
    application_id: uuid.UUID


@router.post("", response_model=WorkflowRuleResponse, status_code=status.HTTP_201_CREATED)
def create_workflow_rule(
    payload: WorkflowRuleCreate,
    current_user: RequireRecruiter,
    db: TenantDb
):
    rule = WorkflowRule(
        company_id=current_user.company_id,
        name=payload.name,
        trigger_type=payload.trigger_type,
        conditions_json=payload.conditions_json,
        actions_json=payload.actions_json,
        status="draft",
        version=1,
        is_active=False
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    log_audit_event(
        db=db,
        action="workflow.created",
        actor_type="user",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        resource_type="workflow_rules",
        resource_id=str(rule.id)
    )
    return rule


@router.get("", response_model=List[WorkflowRuleResponse])
def list_workflow_rules(
    current_user: RequireRecruiter,
    db: TenantDb,
    status_filter: str | None = Query(None, alias="status")
):
    stmt = select(WorkflowRule).where(WorkflowRule.company_id == current_user.company_id)
    if status_filter:
        stmt = stmt.where(WorkflowRule.status == status_filter)
    rules = db.scalars(stmt).all()
    return list(rules)


@router.get("/{rule_id}", response_model=WorkflowRuleResponse)
def get_workflow_rule(
    rule_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb
):
    rule = db.scalar(
        select(WorkflowRule).where(
            WorkflowRule.id == rule_id,
            WorkflowRule.company_id == current_user.company_id
        )
    )
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow rule not found")
    return rule


@router.put("/{rule_id}", response_model=WorkflowRuleResponse)
def update_workflow_rule(
    rule_id: uuid.UUID,
    payload: WorkflowRuleCreate,
    current_user: RequireRecruiter,
    db: TenantDb
):
    rule = db.scalar(
        select(WorkflowRule).where(
            WorkflowRule.id == rule_id,
            WorkflowRule.company_id == current_user.company_id
        )
    )
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow rule not found")

    if rule.status == "active":
        # Immutability Check: Create a new version
        new_version = WorkflowRule(
            company_id=current_user.company_id,
            parent_rule_id=rule.id,
            name=payload.name,
            trigger_type=payload.trigger_type,
            conditions_json=payload.conditions_json,
            actions_json=payload.actions_json,
            status="draft",
            version=rule.version + 1,
            is_active=False
        )
        # Deactivate old version
        rule.status = "disabled"
        rule.is_active = False
        db.add(rule)
        db.add(new_version)
        db.commit()
        db.refresh(new_version)

        # Log audit trail
        audit = IntegrationAuditLog(
            company_id=current_user.company_id,
            integration_type="workflow",
            action="workflow.version_created",
            actor_id=current_user.id,
            status="success",
            details_json={"parent_id": str(rule.id), "new_id": str(new_version.id), "version": new_version.version}
        )
        db.add(audit)
        db.commit()
        return new_version

    # If it is draft, disabled, or archived, update in place
    rule.name = payload.name
    rule.trigger_type = payload.trigger_type
    rule.conditions_json = payload.conditions_json
    rule.actions_json = payload.actions_json
    rule.updated_at = datetime.now(timezone.utc)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/{rule_id}/publish", response_model=WorkflowRuleResponse)
def publish_workflow_rule(
    rule_id: uuid.UUID,
    current_user: RequireOwner,
    db: TenantDb
):
    rule = db.scalar(
        select(WorkflowRule).where(
            WorkflowRule.id == rule_id,
            WorkflowRule.company_id == current_user.company_id
        )
    )
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow rule not found")

    rule.status = "active"
    rule.is_active = True
    rule.updated_at = datetime.now(timezone.utc)
    db.add(rule)
    db.commit()
    db.refresh(rule)

    # Log to integration audits
    audit = IntegrationAuditLog(
        company_id=current_user.company_id,
        integration_type="workflow",
        action="workflow.published",
        actor_id=current_user.id,
        status="success",
        details_json={"rule_id": str(rule.id), "version": rule.version}
    )
    db.add(audit)
    db.commit()
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow_rule(
    rule_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb
):
    rule = db.scalar(
        select(WorkflowRule).where(
            WorkflowRule.id == rule_id,
            WorkflowRule.company_id == current_user.company_id
        )
    )
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow rule not found")

    rule.status = "archived"
    rule.is_active = False
    db.add(rule)
    db.commit()
    return None


@router.get("/{rule_id}/export")
def export_workflow_json(
    rule_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb
):
    rule = db.scalar(
        select(WorkflowRule).where(
            WorkflowRule.id == rule_id,
            WorkflowRule.company_id == current_user.company_id
        )
    )
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow rule not found")

    payload = {
        "name": rule.name,
        "trigger_type": rule.trigger_type,
        "conditions_json": rule.conditions_json,
        "actions_json": rule.actions_json,
        "version": rule.version
    }
    return payload


@router.post("/import", response_model=WorkflowRuleResponse, status_code=status.HTTP_201_CREATED)
def import_workflow_json(
    payload: dict,
    current_user: RequireRecruiter,
    db: TenantDb
):
    # Validate payload structure
    required = ["name", "trigger_type", "conditions_json", "actions_json"]
    if not all(r in payload for r in required):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Malformed workflow JSON payload")

    rule = WorkflowRule(
        company_id=current_user.company_id,
        name=payload["name"],
        trigger_type=payload["trigger_type"],
        conditions_json=payload["conditions_json"],
        actions_json=payload["actions_json"],
        status="draft",
        version=1,
        is_active=False
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/{rule_id}/simulate")
def simulate_workflow_run(
    rule_id: uuid.UUID,
    body: SimulateRequest,
    current_user: RequireRecruiter,
    db: TenantDb
):
    try:
        res = WorkflowEngine.simulate_workflow(db, rule_id, body.application_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/runs/all")
def list_workflow_runs(
    current_user: RequireRecruiter,
    db: TenantDb
):
    stmt = select(WorkflowRun).where(WorkflowRun.company_id == current_user.company_id).order_by(WorkflowRun.created_at.desc())
    runs = db.scalars(stmt).all()
    return [{
        "id": str(r.id),
        "rule_name": r.rule.name,
        "status": r.status,
        "attempt_number": r.attempt_number,
        "created_at": r.created_at.isoformat(),
        "error_message": r.error_message
    } for r in runs]


@router.post("/runs/{run_id}/replay")
def replay_workflow_run(
    run_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb
):
    run = db.scalar(
        select(WorkflowRun).where(
            WorkflowRun.id == run_id,
            WorkflowRun.company_id == current_user.company_id
        )
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    # Reset attempts and status
    run.status = "pending"
    run.attempt_number = 1
    run.error_message = None
    db.add(run)
    db.commit()

    # Trigger async replay task
    execute_workflow_run_task.delay(str(run.company_id), str(run.id))
    return {"status": "replaying"}


@router.post("/webhooks/logs/{log_id}/replay")
def replay_outbound_webhook(
    log_id: uuid.UUID,
    current_user: RequireOwner,
    db: TenantDb
):
    log = db.scalar(
        select(WebhookDeliveryLog).where(
            WebhookDeliveryLog.id == log_id,
            WebhookDeliveryLog.company_id == current_user.company_id
        )
    )
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook log not found")

    # Dispatch webhooks task
    from tasks.webhooks import dispatch_webhook_event_task
    dispatch_webhook_event_task.delay(str(log.company_id), log.event_type, log.payload)
    return {"status": "webhook_queued"}
