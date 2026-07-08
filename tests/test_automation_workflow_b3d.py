import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from db.session import SessionLocal
from models import (
    ApiKey, WorkflowRule, WorkflowRun, SentEmail, EmailTemplate,
    SlackTeamsIntegration, BackgroundCheckRecord, GreenhouseLeverImport,
    IntegrationAuditLog, IntegrationHealth, UsageBillingEvent
)
from core.workflow_engine import WorkflowEngine, evaluate_conditions
from core.email_tracking import EmailTrackingService
from integrations.base.registry import IntegrationRegistry
from integrations.base.factory import ProviderFactory


# ---------------------------------------------------------------------------
# 1. Models & Registry Checks
# ---------------------------------------------------------------------------

class TestB3DModelsAndRegistry:
    def test_models_exist(self):
        assert WorkflowRule.__tablename__ == "workflow_rules"
        assert WorkflowRun.__tablename__ == "workflow_runs"
        assert SentEmail.__tablename__ == "sent_emails"
        assert ApiKey.__tablename__ == "api_keys"
        assert SlackTeamsIntegration.__tablename__ == "slack_teams_integrations"
        assert BackgroundCheckRecord.__tablename__ == "background_check_records"
        assert GreenhouseLeverImport.__tablename__ == "hris_imports"
        assert IntegrationHealth.__tablename__ == "integration_health"
        assert UsageBillingEvent.__tablename__ == "usage_billing_events"

    def test_integration_registry(self):
        # Retrieve calendar google provider
        google_cal = IntegrationRegistry.get("calendar", "google")
        assert google_cal is not None

        # Retrieve slack provider
        slack_chat = IntegrationRegistry.get("chat", "slack")
        assert slack_chat is not None


# ---------------------------------------------------------------------------
# 2. Workflow Automation Engine
# ---------------------------------------------------------------------------

class TestWorkflowAutomationEngine:
    def test_evaluate_conditions_and(self):
        context = {"source": "LinkedIn", "job": {"title": "Software Engineer"}}
        conditions = {
            "operator": "AND",
            "rules": [
                {"field": "source", "operator": "==", "value": "LinkedIn"},
                {"field": "job.title", "operator": "contains", "value": "Engineer"}
            ]
        }
        assert evaluate_conditions(conditions, context) is True

    def test_evaluate_conditions_or(self):
        context = {"source": "LinkedIn", "job": {"title": "Software Engineer"}}
        conditions = {
            "operator": "OR",
            "rules": [
                {"field": "source", "operator": "==", "value": "Indeed"},
                {"field": "job.title", "operator": "contains", "value": "Engineer"}
            ]
        }
        assert evaluate_conditions(conditions, context) is True

    def test_workflow_engine_simulation(self):
        db = MagicMock()
        rule = MagicMock()
        rule.company_id = uuid.uuid4()
        rule.trigger_type = "application.created"
        rule.conditions_json = {
            "operator": "AND",
            "rules": [{"field": "source", "operator": "==", "value": "LinkedIn"}]
        }
        rule.actions_json = [{"type": "slack_notification", "value": "SLA Alert!"}]
        db.get.return_value = rule

        # Mock app and candidate
        app = MagicMock()
        app.candidate_id = uuid.uuid4()
        app.job_id = uuid.uuid4()
        app.status = MagicMock()
        app.status.value = "screening"
        app.source = "LinkedIn"
        
        db.scalar.side_effect = [app, None, None] # app, candidate, job fetch

        with patch.object(WorkflowEngine, "build_context") as mock_ctx:
            mock_ctx.return_value = {
                "source": "LinkedIn",
                "job": {"title": "Software Engineer"}
            }
            res = WorkflowEngine.simulate_workflow(db, uuid.uuid4(), uuid.uuid4())

        assert res["trigger_matched"] is True
        assert res["conditions_passed"] is True
        assert len(res["projected_actions"]) == 1
        assert "slack_notification" in res["projected_actions"][0]


# ---------------------------------------------------------------------------
# 3. Email Campaign Tracking
# ---------------------------------------------------------------------------

class TestEmailCampaignTracking:
    def test_track_open_increments_count(self):
        db = MagicMock()
        sent_email = MagicMock()
        sent_email.open_count = 0
        db.get.return_value = sent_email

        pixel = EmailTrackingService.track_open(db, uuid.uuid4())
        assert isinstance(pixel, bytes)
        assert sent_email.open_count == 1
        db.commit.assert_called_once()

    def test_track_click_increments_count(self):
        db = MagicMock()
        sent_email = MagicMock()
        sent_email.click_count = 0
        db.get.return_value = sent_email

        url = EmailTrackingService.track_click(db, uuid.uuid4(), "https://google.com")
        assert url == "https://google.com"
        assert sent_email.click_count == 1
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 4. Slack Connectivity Integration
# ---------------------------------------------------------------------------

class TestSlackTeamsConnectivity:
    def test_slack_provider_sends_alert(self):
        provider = ProviderFactory.get_provider("chat", "slack")
        # Direct verify using mock URL
        success = provider.send_message("https://hooks.slack.com/services/mock-slack", "Hello Slack!")
        assert success is True
