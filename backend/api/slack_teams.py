import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select

from api.deps import RequireOwner, TenantDb
from models.slack_teams import SlackTeamsIntegration
from core.audit import log_audit_event
from models.integration_audit_log import IntegrationAuditLog
from integrations.base.factory import ProviderFactory

router = APIRouter(prefix="/slack-teams", tags=["slack_teams"])


class SlackTeamsConfigPayload(BaseModel):
    webhook_url: str


class SlackTeamsResponse(BaseModel):
    id: uuid.UUID
    webhook_url: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=SlackTeamsResponse | None)
def get_slack_teams_integration(
    current_user: RequireOwner,
    db: TenantDb
):
    integration = db.scalar(
        select(SlackTeamsIntegration).where(SlackTeamsIntegration.company_id == current_user.company_id)
    )
    return integration


@router.post("", response_model=SlackTeamsResponse, status_code=status.HTTP_201_CREATED)
def configure_slack_teams(
    payload: SlackTeamsConfigPayload,
    current_user: RequireOwner,
    db: TenantDb
):
    integration = db.scalar(
        select(SlackTeamsIntegration).where(SlackTeamsIntegration.company_id == current_user.company_id)
    )
    if integration:
        integration.webhook_url = payload.webhook_url
    else:
        integration = SlackTeamsIntegration(
            company_id=current_user.company_id,
            webhook_url=payload.webhook_url
        )
        db.add(integration)

    db.commit()
    db.refresh(integration)

    # Log to integration audits
    audit = IntegrationAuditLog(
        company_id=current_user.company_id,
        integration_type="slack",
        action="slack.configured",
        actor_id=current_user.id,
        status="success",
        details_json={"webhook_url": integration.webhook_url}
    )
    db.add(audit)
    db.commit()
    return integration


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def remove_slack_teams(
    current_user: RequireOwner,
    db: TenantDb
):
    integration = db.scalar(
        select(SlackTeamsIntegration).where(SlackTeamsIntegration.company_id == current_user.company_id)
    )
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slack/Teams integration not found")

    db.delete(integration)
    db.commit()

    # Log to audits
    audit = IntegrationAuditLog(
        company_id=current_user.company_id,
        integration_type="slack",
        action="slack.removed",
        actor_id=current_user.id,
        status="success"
    )
    db.add(audit)
    db.commit()
    return None


@router.post("/test")
def test_slack_teams_connection(
    current_user: RequireOwner,
    db: TenantDb
):
    integration = db.scalar(
        select(SlackTeamsIntegration).where(SlackTeamsIntegration.company_id == current_user.company_id)
    )
    if not integration:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No Slack/Teams webhook configured")

    chat_provider = ProviderFactory.get_provider("chat", "slack")
    success = chat_provider.send_message(
        webhook_url=integration.webhook_url,
        message="SmartOnboard Webhook Connection Test: SUCCESS!"
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to post message to Slack webhook")
    return {"status": "success"}
