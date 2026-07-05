"""
Tests for Phase B.3C: Executive Hiring Intelligence, Analytics & Reporting.
All tests use mocked DB sessions and service-layer unit tests —
no live database connection required.
"""
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(role="owner", company_id=None):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.company_id = company_id or uuid.uuid4()
    user.role = MagicMock()
    user.role.value = role
    user.full_name = "Test User"
    return user


def _make_app(status_val="submitted", source="LinkedIn", is_archived=False, created_at=None, updated_at=None):
    from unittest.mock import MagicMock
    app = MagicMock()
    app.id = uuid.uuid4()
    app.job_id = uuid.uuid4()
    app.owner_id = uuid.uuid4()
    app.company_id = uuid.uuid4()
    app.source = source
    app.is_archived = is_archived
    app.interviews = []

    now = datetime.now(timezone.utc)
    app.created_at = created_at or (now - timedelta(days=20))
    app.updated_at = updated_at or now

    status_mock = MagicMock()
    status_mock.value = status_val
    app.status = status_mock
    return app


# ---------------------------------------------------------------------------
# 1. UserPermission constants
# ---------------------------------------------------------------------------

class TestUserPermissions:
    def test_view_executive_analytics_defined(self):
        from models.rbac import UserPermission
        assert UserPermission.VIEW_EXECUTIVE_ANALYTICS == "view_executive_analytics"

    def test_export_executive_reports_defined(self):
        from models.rbac import UserPermission
        assert UserPermission.EXPORT_EXECUTIVE_REPORTS == "export_executive_reports"

    def test_existing_view_analytics_untouched(self):
        from models.rbac import UserPermission
        assert UserPermission.VIEW_ANALYTICS == "view_analytics"


# ---------------------------------------------------------------------------
# 2. ReportExport model
# ---------------------------------------------------------------------------

class TestReportExportModel:
    def test_model_can_be_imported(self):
        from models.report_export import ReportExport
        assert ReportExport.__tablename__ == "report_exports"

    def test_model_fields_exist(self):
        from models.report_export import ReportExport
        cols = [c.name for c in ReportExport.__table__.columns]
        for field in ("id", "company_id", "requested_by", "status", "format", "filters", "file_path", "expires_at", "created_at"):
            assert field in cols, f"Missing column: {field}"

    def test_model_registered_in_init(self):
        from models import ReportExport
        assert ReportExport is not None


# ---------------------------------------------------------------------------
# 3. AnalyticsCache
# ---------------------------------------------------------------------------

class TestAnalyticsCache:
    def test_set_and_get(self):
        from core.cache import AnalyticsCache
        cache = AnalyticsCache()
        cache.set("k1", {"v": 1}, ttl_seconds=60)
        assert cache.get("k1") == {"v": 1}

    def test_get_expired_returns_none(self):
        from core.cache import AnalyticsCache
        cache = AnalyticsCache()
        cache.set("k2", "value", ttl_seconds=-1)  # Already expired
        assert cache.get("k2") is None

    def test_invalidate_by_tag_removes_entries(self):
        from core.cache import AnalyticsCache
        cache = AnalyticsCache()
        cache.set("k3", "x", ttl_seconds=60, tags=["company1:dashboard"])
        cache.set("k4", "y", ttl_seconds=60, tags=["company2:dashboard"])
        cache.invalidate_by_tag("company1:dashboard")
        assert cache.get("k3") is None
        assert cache.get("k4") == "y"

    def test_invalidate_company_clears_dashboard_and_funnel(self):
        from core.cache import AnalyticsCache
        cache = AnalyticsCache()
        cid = str(uuid.uuid4())
        cache.set("d1", "data", ttl_seconds=60, tags=[f"{cid}:dashboard"])
        cache.set("f1", "data", ttl_seconds=60, tags=[f"{cid}:funnel"])
        cache.invalidate_company(cid)
        assert cache.get("d1") is None
        assert cache.get("f1") is None

    def test_cache_miss_returns_none(self):
        from core.cache import AnalyticsCache
        cache = AnalyticsCache()
        assert cache.get("nonexistent_key") is None


# ---------------------------------------------------------------------------
# 4. AnalyticsService — Forecasting & explanation
# ---------------------------------------------------------------------------

class TestForecasting:
    def _make_db_with_hired_apps(self, count=10):
        db = MagicMock()
        from models.enums import ApplicationStatus
        apps = []
        for _ in range(count):
            app = _make_app(status_val="hired")
            apps.append(app)
        db.scalars.return_value.all.return_value = apps
        db.scalar.return_value = 5  # active_requisitions
        return db

    def test_forecast_returns_expected_structure(self):
        from core.analytics_service import AnalyticsService
        db = self._make_db_with_hired_apps(12)
        user = _make_user()
        with patch.object(AnalyticsService, "_get_allowed_job_ids", return_value=None):
            result = AnalyticsService.get_forecasting(db, user, window_days=90)
        assert "forecast" in result
        assert "explanation" in result
        assert "expected_hires" in result["forecast"]
        assert "recruiter_capacity" in result["forecast"]
        assert "historical_average" in result["explanation"]
        assert "window_used" in result["explanation"]
        assert "confidence" in result["explanation"]

    def test_low_data_returns_low_confidence(self):
        from core.analytics_service import AnalyticsService
        db = self._make_db_with_hired_apps(2)
        user = _make_user()
        with patch.object(AnalyticsService, "_get_allowed_job_ids", return_value=None):
            result = AnalyticsService.get_forecasting(db, user, window_days=90)
        assert result["explanation"]["confidence"] == "Low"

    def test_window_days_reflected_in_explanation(self):
        from core.analytics_service import AnalyticsService
        db = self._make_db_with_hired_apps(8)
        user = _make_user()
        with patch.object(AnalyticsService, "_get_allowed_job_ids", return_value=None):
            result = AnalyticsService.get_forecasting(db, user, window_days=60)
        assert result["explanation"]["window_used"] == "60 days"

    def test_forecast_uses_deterministic_math(self):
        from core.analytics_service import AnalyticsService
        db = self._make_db_with_hired_apps(6)  # 6 hires in 90 days → ~2/month
        user = _make_user()
        with patch.object(AnalyticsService, "_get_allowed_job_ids", return_value=None):
            result = AnalyticsService.get_forecasting(db, user, window_days=90)
        # historical_average ≈ 2.0 hires/month
        assert result["explanation"]["historical_average"] == pytest.approx(2.0, rel=0.5)


# ---------------------------------------------------------------------------
# 5. AnalyticsService — Tenant isolation
# ---------------------------------------------------------------------------

class TestTenantIsolation:
    def test_get_allowed_job_ids_owner_returns_none(self):
        from core.analytics_service import AnalyticsService
        db = MagicMock()
        user = _make_user(role="owner")
        result = AnalyticsService._get_allowed_job_ids(db, user)
        # Owner should have unrestricted access
        assert result is None

    def test_sla_compliance_structure(self):
        from core.analytics_service import AnalyticsService
        db = MagicMock()
        tracker = MagicMock()
        tracker.status = "active"
        tracker.breached_at = None
        tracker.escalation_count = 0
        db.scalars.return_value.all.return_value = [tracker, tracker]
        user = _make_user()
        with patch.object(AnalyticsService, "_get_allowed_job_ids", return_value=None):
            result = AnalyticsService.get_sla_compliance(db, user)
        assert "total_trackers" in result
        assert "compliance_rate" in result
        assert result["total_trackers"] == 2
        assert result["compliance_rate"] == 100.0


# ---------------------------------------------------------------------------
# 6. Reporting Engine
# ---------------------------------------------------------------------------

class TestReportingEngine:
    def test_generate_csv_returns_bytes(self):
        from core.reporting import generate_csv
        headers = ["name", "score"]
        rows = [{"name": "Alice", "score": "95"}, {"name": "Bob", "score": "80"}]
        result = generate_csv(headers, rows)
        assert isinstance(result, bytes)
        assert b"name" in result
        assert b"Alice" in result

    def test_generate_csv_empty_rows(self):
        from core.reporting import generate_csv
        result = generate_csv(["col1", "col2"], [])
        assert isinstance(result, bytes)
        assert b"col1" in result

    def test_generate_xlsx_returns_bytes(self):
        from core.reporting import generate_xlsx
        headers = ["recruiter", "hires"]
        rows = [{"recruiter": "Sarah", "hires": "12"}]
        result = generate_xlsx(headers, rows, sheet_title="Recruiter Report")
        assert isinstance(result, bytes)
        # xlsx starts with PK (zip file magic bytes)
        assert result[:2] == b"PK"

    def test_generate_pdf_returns_bytes(self):
        from core.reporting import generate_pdf
        headers = ["stage", "count"]
        rows = [{"stage": "Applied", "count": "100"}, {"stage": "Offer", "count": "10"}]
        kpi = {"Active Jobs": 5, "Hires": 3}
        result = generate_pdf("Pipeline Report", headers, rows, kpi_summary=kpi)
        assert isinstance(result, bytes)
        # PDF starts with %PDF
        assert result[:4] == b"%PDF"

    def test_generate_report_dispatcher_csv(self):
        from core.reporting import generate_report
        content, media_type = generate_report("CSV", "Test", ["a", "b"], [{"a": "1", "b": "2"}])
        assert media_type == "text/csv"
        assert b"a" in content

    def test_generate_report_dispatcher_xlsx(self):
        from core.reporting import generate_report
        content, media_type = generate_report("XLSX", "Test", ["a"], [{"a": "1"}])
        assert "spreadsheetml" in media_type

    def test_generate_report_dispatcher_pdf(self):
        from core.reporting import generate_report
        content, media_type = generate_report("PDF", "Test", ["a"], [{"a": "1"}])
        assert media_type == "application/pdf"

    def test_generate_report_invalid_format_raises(self):
        from core.reporting import generate_report
        with pytest.raises(ValueError, match="Unsupported report format"):
            generate_report("DOCX", "Test", ["a"], [])


# ---------------------------------------------------------------------------
# 7. Diversity metrics privacy guarantee
# ---------------------------------------------------------------------------

class TestDiversityMetrics:
    def test_returns_no_candidate_details(self):
        from core.analytics_service import AnalyticsService
        db = MagicMock()
        user = _make_user()
        result = AnalyticsService.get_diversity_metrics(db, user)
        # Must not contain anything that could identify candidates
        result_str = str(result)
        assert "name" not in result_str.lower()
        assert "email" not in result_str.lower()
        assert "resume" not in result_str.lower()
        assert "anonymized_fairness_index" in result


# ---------------------------------------------------------------------------
# 8. generate_executive_summary — AI service method
# ---------------------------------------------------------------------------

class TestExecutiveSummaryMethod:
    def test_method_exists_on_service(self):
        from core.intelligence import GenerativeIntelligenceService
        assert hasattr(GenerativeIntelligenceService, "generate_executive_summary")
        assert callable(GenerativeIntelligenceService.generate_executive_summary)

    def test_returns_fallback_on_error(self):
        from core.intelligence import GenerativeIntelligenceService
        with patch("core.intelligence.invoke_with_retry", side_effect=Exception("API timeout")):
            result = GenerativeIntelligenceService.generate_executive_summary("Hires: 10")
        assert isinstance(result, str)
        assert "Executive Briefing" in result or "Unable" in result
