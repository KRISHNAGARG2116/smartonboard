import os
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock
import dns.resolver

# Allow importing backend modules before any backend code is loaded
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


# Force fallback storage mode during tests if native pgvector not available/tested
os.environ["USE_PGVECTOR"] = "false"
# Force Celery to execute tasks synchronously and in-process for all tests
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
# Set testing flag so models/deps know they are running inside pytest
os.environ["TESTING"] = "true"

# Import the process-level test flag — must happen AFTER sys.path is set and
# AFTER os.environ["TESTING"] is set so the backend config picks it up.
from core.test_flags import ENFORCE_ONBOARDING, BYPASS_EMAIL_VERIFICATION  # noqa: E402

# Global DNS mock for dummy domains to prevent API register failures in integration tests
_original_resolve = dns.resolver.resolve

def _mock_dns_resolve(qname, rdtype="A", *args, **kwargs):
    qname_str = str(qname).lower().strip()
    if "nonexistent" in qname_str:
        raise dns.resolver.NXDOMAIN(f"Mocked NXDOMAIN for {qname_str}")
    if rdtype == "MX":
        mock_mx = MagicMock()
        mock_mx.exchange = f"mail.{qname_str}."
        return [mock_mx]
    return [MagicMock()]

dns.resolver.resolve = _mock_dns_resolve


from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from core.config import get_settings
from db.session import tenant_context
from core.limiter import limiter

settings = get_settings()

# Disable rate limiting globally for all unit/integration tests by default
limiter.enabled = False


@pytest.fixture(scope="session")
def db_engine():
    # 1. Connect as the main superuser with AUTOCOMMIT enabled to run DDL statements
    super_engine = create_engine(settings.database_url, execution_options={"isolation_level": "AUTOCOMMIT"})
    try:
        with super_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            
            # Check if standard non-superuser test role exists
            role_exists = conn.execute(
                text("SELECT 1 FROM pg_roles WHERE rolname = 'smartonboard_test_user'")
            ).scalar()
            
            if not role_exists:
                conn.execute(text("CREATE ROLE smartonboard_test_user WITH LOGIN PASSWORD 'smartonboard'"))
            
            # Grant privileges on all schemas, tables, and sequences to the test user
            conn.execute(text("GRANT USAGE ON SCHEMA public TO smartonboard_test_user"))
            conn.execute(text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO smartonboard_test_user"))
            conn.execute(text("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO smartonboard_test_user"))
            
    except OperationalError:
        pytest.skip(
            "PostgreSQL database is not reachable at {}. "
            "Please run 'docker compose up -d && alembic upgrade head' "
            "to start the database before running RLS tests.".format(settings.database_url)
        )
    
    # 2. Return the test engine configured to connect as the standard non-superuser role
    test_db_url = settings.database_url.replace("smartonboard:smartonboard@", "smartonboard_test_user:smartonboard@")
    return create_engine(test_db_url)


@pytest.fixture(autouse=True)
def _set_onboarding_enforcement(request):
    """Set ENFORCE_ONBOARDING=True only when running test_recruiter_onboarding.py.
    Set BYPASS_EMAIL_VERIFICATION=False only when running test_auth_hardening.py or test_candidate_verification.py.

    All other test modules bypass the onboarding and email verification checks so they can run efficiently.
    """
    module_name = request.module.__name__ if request.module else ""
    ENFORCE_ONBOARDING.value = "test_recruiter_onboarding" in module_name
    BYPASS_EMAIL_VERIFICATION.value = "test_auth_hardening" not in module_name and "test_candidate_verification" not in module_name
    yield
    ENFORCE_ONBOARDING.value = False  # always reset after each test
    BYPASS_EMAIL_VERIFICATION.value = True  # always reset after each test


@pytest.fixture
def db_session(db_engine):
    SessionTest = sessionmaker(bind=db_engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = SessionTest()
    session.execute(text("SELECT set_config('app.bypass_audit_immutability', 'false', false)"))
    
    # Reset rate limits / lockout blocks in Redis for each test
    import redis
    try:
        r = redis.from_url(settings.redis_url)
        r.flushall()
    except Exception:
        pass

    try:
        yield session
    finally:
        session.close()
        # Clean up database tables under RLS bypass mode so teardown has visibility to delete all records
        with tenant_context(auth_mode="true"):
            with db_engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("SELECT set_config('app.bypass_audit_immutability', 'true', false)"))
                    # Full table list — ordered to respect FK constraints (children first)
                    for table in (
                        # Leaf / child tables first
                        "verification_tokens",
                        "revoked_tokens",
                        "user_sessions",
                        "candidate_resumes",
                        "candidate_profiles",
                        "candidate_tag_associations",
                        "candidate_tags",
                        "candidate_embeddings",
                        "candidate_stage_histories",
                        "candidate_stage_transitions",
                        "candidate_stage_sla_trackers",
                        "application_events",
                        "application_snapshots",
                        "application_secondary_recruiters",
                        "application_watchers",
                        "candidate_notes",
                        "scorecards",
                        "scorecard_template_skills",
                        "scorecard_templates",
                        "interview_slots",
                        "interviews",
                        "interview_kits",
                        "scheduling_links",
                        "offers",
                        "audit_logs",
                        "ai_insight_interactions",
                        "ai_recruiter_insights",
                        "recruiter_productivity_aggregates",
                        "funnel_aggregates",
                        "export_jobs",
                        "report_exports",
                        "saved_searches",
                        "notifications",
                        "duplicate_warnings",
                        "bulk_operations",
                        "quarantined_files",
                        "permissions",
                        "role_permissions",
                        "user_roles",
                        "roles",
                        "user_job_access",
                        "job_revisions",
                        "stage_definitions",
                        "pipelines",
                        "pipeline_templates",
                        "approval_step_escalations",
                        "approval_escalation_rules",
                        "approval_steps",
                        "approval_chains",
                        "approval_template_steps",
                        "approval_templates",
                        "stage_slas",
                        "hiring_committee_members",
                        "committee_review_reviewers",
                        "committee_reviews",
                        "hiring_committees",
                        "applications",
                        "candidates",
                        "jobs",
                        # Integration tables
                        "webhook_delivery_logs",
                        "webhook_subscriptions",
                        "workflow_runs",
                        "workflow_rules",
                        "email_templates",
                        "sent_emails",
                        "api_keys",
                        "slack_teams_integrations",
                        "background_check_records",
                        "hris_imports",
                        "integration_audit_logs",
                        "integration_health",
                        "usage_billing_events",
                        "calendar_credentials",
                        "oauth_states",
                        "scheduling_links",
                        # Analytics
                        "funnel_aggregates",
                        "recruiter_productivity_aggregates",
                        # Company settings
                        "company_subscription_plans",
                        "company_usage_ledgers",
                        "company_usage_histories",
                        "company_ip_whitelists",
                        "company_smtp_settings",
                        "company_sso_settings",
                        "company_trust_metrics",
                        "company_hris_integrations",
                        # Legacy onboarding (preserved per AGENTS.md)
                        "onboarding_portal_tokens",
                        "onboarding_document_signatures",
                        "onboarding_task_reminders",
                        "onboarding_task_escalations",
                        "onboarding_activity_log",
                        "onboarding_event_outbox",
                        "onboarding_documents",
                        "onboarding_tasks",
                        "onboarding_workflows",
                        "onboarding_template_tasks",
                        "onboarding_templates",
                        # HRIS / employee
                        "employee_sync_history",
                        "sync_metrics",
                        "hris_field_mappings",
                        "dlq_records",
                        "employees",
                        # Top-level
                        "users",
                        "companies",
                    ):
                        try:
                            conn.execute(text(f"DELETE FROM {table}"))
                        except Exception:
                            pass  # table may not exist in this migration state

                    conn.execute(text("SELECT set_config('app.bypass_audit_immutability', 'false', false)"))
