import pytest
import uuid
from datetime import datetime, timezone, date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from server import app
from db.session import get_db, tenant_context
from models import User, Company, Job, Application, Offer, CandidateTask, Notification, UserSession, Candidate
from models.enums import UserRole, ApplicationStatus, JobStatus
from core.security import create_access_token

@pytest.fixture
def test_setup(db_session):
    with tenant_context(auth_mode="true"):
        # Create company
        company = Company(name="Test Company", slug="test-company")
        db_session.add(company)
        db_session.commit()

        # Create candidate User
        candidate = User(
            email="candidate_test@example.com",
            password_hash="hashed_password",
            full_name="Candidate Test",
            role=UserRole.CANDIDATE,
            is_active=True
        )
        db_session.add(candidate)

        # Create recruiter User
        recruiter = User(
            email="recruiter_test@example.com",
            password_hash="hashed_password",
            full_name="Recruiter Test",
            role=UserRole.RECRUITER,
            company_id=company.id,
            is_active=True
        )
        db_session.add(recruiter)
        db_session.commit()

        # Create job
        job = Job(
            company_id=company.id,
            title="Test Job",
            description="Job description",
            status=JobStatus.OPEN
        )
        db_session.add(job)
        db_session.commit()

        # Create recruiter Candidate record
        cand_rec = Candidate(
            company_id=company.id,
            email=candidate.email,
            full_name=candidate.full_name
        )
        db_session.add(cand_rec)
        db_session.commit()

        # Create application
        app_record = Application(
            company_id=company.id,
            job_id=job.id,
            candidate_id=cand_rec.id,
            status=ApplicationStatus.SUBMITTED
        )
        db_session.add(app_record)
        db_session.commit()

        # Create candidate session
        session_id = uuid.uuid4()
        session = UserSession(
            id=session_id,
            user_id=candidate.id,
            refresh_token_hash=str(uuid.uuid4()),
            is_revoked=False,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc)
        )
        db_session.add(session)
        db_session.commit()

    token = create_access_token(
        str(candidate.id),
        {
            "company_id": None,
            "role": UserRole.CANDIDATE.value,
            "email": candidate.email,
            "session_id": str(session_id)
        }
    )

    return {
        "company": company,
        "candidate": candidate,
        "recruiter": recruiter,
        "job": job,
        "application": app_record,
        "headers": {"Authorization": f"Bearer {token}"}
    }

@pytest.fixture
def api_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

from datetime import timedelta

def test_get_dashboard_initial(api_client, db_session, test_setup):
    headers = test_setup["headers"]
    resp = api_client.get("/api/v1/candidate/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["computed_state"] == "Application Submitted"
    assert data["unread_count"] == 0
    assert data["metrics"]["applications_count"] == 1

def test_get_dashboard_onboarding_state(api_client, db_session, test_setup):
    headers = test_setup["headers"]
    candidate = test_setup["candidate"]
    company = test_setup["company"]

    with tenant_context(auth_mode="true"):
        # Add onboarding task to trigger state change
        task = CandidateTask(
            company_id=company.id,
            candidate_id=candidate.id,
            title="Swag Selection",
            task_type="choice",
            status="pending",
            due_date=date.today()
        )
        db_session.add(task)
        db_session.commit()

    resp = api_client.get("/api/v1/candidate/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["computed_state"] == "Onboarding"
