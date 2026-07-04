"""
Phase B.3 Hiring Pipeline - Integration & Unit Tests

Tests cover:
- All new ATS model structure (RBAC, ApplicationEvent, BulkOperationLog, SavedSearch, CandidateTag, Notification)
- Stage exit gate validation logic
- Weighted ranking score computation
- Scorecard draft/submit schema
- Notification schema
- Router registrations
- Core workflow functions
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from models.rbac import Role, Permission, UserJobAccess
from models.ats_models import ApplicationEvent, BulkOperationLog, SavedSearch, CandidateTag, Notification
from models.sla import CandidateStageSLATracker


class TestAtsModels:
    """Verify all new Phase B.3 ATS models exist with correct schema attributes."""

    def test_rbac_models_exist(self):
        assert issubclass(Role, object)
        assert issubclass(Permission, object)
        assert issubclass(UserJobAccess, object)
        assert hasattr(Role, "name")
        assert hasattr(Permission, "name")
        assert hasattr(UserJobAccess, "job_id")
        assert Role.__tablename__ == "roles"
        assert Permission.__tablename__ == "permissions"
        assert UserJobAccess.__tablename__ == "user_job_access"

    def test_application_event_model(self):
        assert issubclass(ApplicationEvent, object)
        assert hasattr(ApplicationEvent, "event_type")
        assert hasattr(ApplicationEvent, "actor_id")
        assert hasattr(ApplicationEvent, "actor_name")
        assert hasattr(ApplicationEvent, "metadata_json")
        assert ApplicationEvent.__tablename__ == "application_events"

    def test_bulk_operation_log_model(self):
        assert issubclass(BulkOperationLog, object)
        assert hasattr(BulkOperationLog, "previous_states")
        assert hasattr(BulkOperationLog, "affected_application_ids")
        assert hasattr(BulkOperationLog, "action_type")
        assert BulkOperationLog.__tablename__ == "bulk_operations"

    def test_saved_search_model(self):
        assert issubclass(SavedSearch, object)
        assert hasattr(SavedSearch, "filters")
        assert hasattr(SavedSearch, "name")
        assert hasattr(SavedSearch, "recruiter_id")
        assert SavedSearch.__tablename__ == "saved_searches"

    def test_candidate_tag_model(self):
        assert issubclass(CandidateTag, object)
        assert hasattr(CandidateTag, "color")
        assert hasattr(CandidateTag, "name")
        assert CandidateTag.__tablename__ == "candidate_tags"

    def test_notification_model(self):
        assert issubclass(Notification, object)
        assert hasattr(Notification, "status")
        assert hasattr(Notification, "title")
        assert hasattr(Notification, "message")
        assert hasattr(Notification, "type")
        assert hasattr(Notification, "read_at")
        assert hasattr(Notification, "archived_at")
        assert Notification.__tablename__ == "notifications"

    def test_sla_tracker_model_pause_fields(self):
        assert issubclass(CandidateStageSLATracker, object)
        assert hasattr(CandidateStageSLATracker, "paused_at")
        assert hasattr(CandidateStageSLATracker, "total_paused_seconds")
        assert CandidateStageSLATracker.__tablename__ == "candidate_stage_sla_trackers"


class TestStageExitGateValidation:
    """Verify the stage exit gate validation raises correct errors."""

    def _make_app(self):
        return SimpleNamespace(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            candidate_id=uuid.uuid4(),
            job_id=uuid.uuid4(),
        )

    def _make_stage(self, settings: dict):
        return SimpleNamespace(
            id=uuid.uuid4(),
            name="Test Stage",
            settings=settings,
        )

    def _make_mock_db_returning_none(self):
        mock_db = MagicMock()
        mock_db.scalar.return_value = None
        return mock_db

    def test_scorecard_required_raises_when_missing(self):
        from core.workflows import validate_stage_exit_requirements
        app = self._make_app()
        stage = self._make_stage({"scorecard_required": True})
        db = self._make_mock_db_returning_none()

        with pytest.raises(ValueError) as exc:
            validate_stage_exit_requirements(db, app, stage)
        assert "final scorecard is required" in str(exc.value)

    def test_interview_required_raises_when_missing(self):
        from core.workflows import validate_stage_exit_requirements
        app = self._make_app()
        stage = self._make_stage({"interview_required": True})
        db = self._make_mock_db_returning_none()

        with pytest.raises(ValueError) as exc:
            validate_stage_exit_requirements(db, app, stage)
        assert "completed interview is required" in str(exc.value)

    def test_note_required_raises_when_missing(self):
        from core.workflows import validate_stage_exit_requirements
        app = self._make_app()
        stage = self._make_stage({"note_required": True})
        db = self._make_mock_db_returning_none()

        with pytest.raises(ValueError) as exc:
            validate_stage_exit_requirements(db, app, stage)
        assert "recruiter note is required" in str(exc.value)

    def test_resume_required_raises_when_missing(self):
        from core.workflows import validate_stage_exit_requirements
        app = self._make_app()
        stage = self._make_stage({"resume_required": True})
        db = self._make_mock_db_returning_none()

        with pytest.raises(ValueError) as exc:
            validate_stage_exit_requirements(db, app, stage)
        assert "candidate resume is required" in str(exc.value)

    def test_no_requirements_does_not_raise(self):
        from core.workflows import validate_stage_exit_requirements
        app = self._make_app()
        stage = self._make_stage({})
        db = self._make_mock_db_returning_none()

        # Should complete without error
        validate_stage_exit_requirements(db, app, stage)

    def test_requirements_met_does_not_raise(self):
        from core.workflows import validate_stage_exit_requirements
        app = self._make_app()
        stage = self._make_stage({"scorecard_required": True})

        # DB returns a mock scorecard (not None) → requirement is met
        mock_db = MagicMock()
        mock_db.scalar.return_value = MagicMock()  # non-None = exists

        validate_stage_exit_requirements(mock_db, app, stage)


class TestRankingScoreComputation:
    """Verify the weighted candidate ranking score."""

    def _make_app(self, match_score=0.85):
        return SimpleNamespace(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            candidate_id=uuid.uuid4(),
            job_id=uuid.uuid4(),
            match_score=match_score,
            status=None,
            current_stage=None,
            created_at=datetime.now(timezone.utc),
        )

    def _make_mock_db(self, scorecards=None, events_count=0):
        mock_db = MagicMock()
        mock_db.scalars.return_value.all.return_value = scorecards or []
        mock_db.scalar.return_value = events_count
        return mock_db

    def test_score_structure(self):
        from api.search import compute_ranking_score
        app = self._make_app()
        score, breakdown = compute_ranking_score(app, self._make_mock_db())

        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert "skills" in breakdown
        assert "experience" in breakdown
        assert "activity" in breakdown
        assert "recency" in breakdown
        assert "stage" in breakdown

    def test_ai_score_maps_correctly(self):
        from api.search import compute_ranking_score
        app = self._make_app(match_score=0.85)
        _, breakdown = compute_ranking_score(app, self._make_mock_db())
        assert breakdown["skills"] == 85

    def test_no_match_score_defaults_to_50(self):
        from api.search import compute_ranking_score
        app = self._make_app(match_score=None)
        _, breakdown = compute_ranking_score(app, self._make_mock_db())
        assert breakdown["skills"] == 50

    def test_activity_score_scales_with_events(self):
        from api.search import compute_ranking_score
        app = self._make_app()
        _, breakdown_low = compute_ranking_score(app, self._make_mock_db(events_count=0))
        _, breakdown_high = compute_ranking_score(app, self._make_mock_db(events_count=10))
        assert breakdown_low["activity"] == 0
        assert breakdown_high["activity"] == 100


class TestScorecardSchemas:
    """Verify scorecard draft/submit Pydantic schemas."""

    def test_scorecard_draft_request_schema(self):
        from schemas.scorecard import ScorecardDraftRequest
        req = ScorecardDraftRequest(
            criteria_scores={"coding": 4},
            overall_recommendation="yes",
            notes="Draft notes"
        )
        assert req.criteria_scores["coding"] == 4
        assert req.overall_recommendation == "yes"

    def test_scorecard_draft_request_all_optional(self):
        from schemas.scorecard import ScorecardDraftRequest
        # All fields should have defaults
        req = ScorecardDraftRequest()
        assert req.criteria_scores == {}
        assert req.overall_recommendation is None

    def test_scorecard_response_includes_is_draft(self):
        from schemas.scorecard import ScorecardResponse
        import inspect
        fields = ScorecardResponse.model_fields
        assert "is_draft" in fields


class TestNotificationSchema:
    """Verify notification Pydantic schemas."""

    def test_notification_response_schema(self):
        from schemas.notification import NotificationResponse
        fields = NotificationResponse.model_fields
        assert "id" in fields
        assert "status" in fields
        assert "read_at" in fields
        assert "archived_at" in fields
        assert "type" in fields


class TestRouterRegistrations:
    """Verify all new Phase B.3 routers are correctly registered."""

    def test_notifications_router_registered(self):
        from api.router import v1_router
        paths = [r.path for r in v1_router.routes]
        assert any("/notifications" in p for p in paths)

    def test_search_router_registered(self):
        from api.router import v1_router
        paths = [r.path for r in v1_router.routes]
        assert any("/search" in p for p in paths)

    def test_ai_copilot_router_registered(self):
        from api.router import v1_router
        paths = [r.path for r in v1_router.routes]
        assert any("/ai" in p for p in paths)

    def test_dashboard_router_registered(self):
        from api.router import v1_router
        paths = [r.path for r in v1_router.routes]
        assert any("/dashboard" in p for p in paths)


class TestBulkApplicationSchemas:
    """Verify bulk update operation schemas."""

    def test_bulk_preview_payload_schema(self):
        from schemas.application import BulkUpdatePreviewPayload
        app_id = uuid.uuid4()
        payload = BulkUpdatePreviewPayload(
            application_ids=[app_id],
            target_status="screening"
        )
        assert payload.application_ids[0] == app_id
        assert payload.target_status == "screening"

    def test_bulk_update_payload_schema(self):
        from schemas.application import BulkUpdatePayload
        app_id = uuid.uuid4()
        stage_id = uuid.uuid4()
        payload = BulkUpdatePayload(
            application_ids=[app_id],
            target_stage_id=stage_id
        )
        assert payload.target_stage_id == stage_id

    def test_bulk_preview_response_schema(self):
        from schemas.application import BulkUpdatePreviewResponse, BulkPreviewWarning
        warning = BulkPreviewWarning(
            application_id=uuid.uuid4(),
            candidate_name="John Doe",
            warning_type="rejected",
            message="Candidate is already rejected."
        )
        response = BulkUpdatePreviewResponse(
            total_applications=5,
            warnings=[warning]
        )
        assert response.total_applications == 5
        assert len(response.warnings) == 1
        assert response.warnings[0].candidate_name == "John Doe"


class TestCoreWorkflowFunctions:
    """Verify core workflow functions exist and are callable."""

    def test_transition_candidate_stage_exists(self):
        from core.workflows import transition_candidate_stage
        assert callable(transition_candidate_stage)

    def test_validate_exit_requirements_exists(self):
        from core.workflows import validate_stage_exit_requirements
        assert callable(validate_stage_exit_requirements)

    def test_check_sla_timers_exists(self):
        from core.workflows import check_and_update_sla_timers
        assert callable(check_and_update_sla_timers)

    def test_timeline_logger_exists(self):
        from core.timeline import log_application_event
        assert callable(log_application_event)
