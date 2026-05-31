import os
import pytest
import sys
from pathlib import Path

# Allow importing backend modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

# Force fallback storage mode during tests if native pgvector not available/tested
os.environ["USE_PGVECTOR"] = "false"
# Force Celery to execute tasks synchronously and in-process for all tests
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

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


@pytest.fixture
def db_session(db_engine):
    SessionTest = sessionmaker(bind=db_engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = SessionTest()
    session.execute(text("SELECT set_config('app.bypass_audit_immutability', 'false', false)"))
    
    try:
        yield session
    finally:
        session.close()
        # Clean up database tables under RLS bypass mode so teardown has visibility to delete all records
        with tenant_context(auth_mode="true"):
            with db_engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("SELECT set_config('app.bypass_audit_immutability', 'true', false)"))
                    for table in ("export_jobs", "ai_insight_interactions", "ai_recruiter_insights", "recruiter_productivity_aggregates", "funnel_aggregates", "candidate_stage_transitions", "candidate_embeddings", "offers", "scorecards", "interviews", "candidate_notes", "audit_logs", "applications", "candidates", "jobs", "users", "companies"):
                        conn.execute(text(f"DELETE FROM {table}"))
                    conn.execute(text("SELECT set_config('app.bypass_audit_immutability', 'false', false)"))
