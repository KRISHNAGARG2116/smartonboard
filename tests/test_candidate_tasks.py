import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from server import app
from db.session import get_db, tenant_context
from models import User, Company, Job, Application, Candidate, CandidateTask, UserSession
from models.enums import UserRole, ApplicationStatus, JobStatus
from core.security import create_access_token

@pytest.fixture
def test_setup(db_session):
    with tenant_context(auth_mode="true"):
        company = Company(name="Test Company", slug="test-company")
        db_session.add(company)
        db_session.commit()

        candidate = User(
            email="candidate_task@example.com",
            password_hash="hashed_password",
            full_name="Candidate Task",
            role=UserRole.CANDIDATE,
            is_active=True
        )
        db_session.add(candidate)

        recruiter = User(
            email="recruiter_task@example.com",
            password_hash="hashed_password",
            full_name="Recruiter Task",
            role=UserRole.RECRUITER,
            company_id=company.id,
            is_active=True
        )
        db_session.add(recruiter)
        db_session.commit()

        job = Job(
            company_id=company.id,
            title="Test Job",
            description="Job description",
            status=JobStatus.OPEN
        )
        db_session.add(job)
        db_session.commit()

        cand_rec = Candidate(
            company_id=company.id,
            email=candidate.email,
            full_name=candidate.full_name
        )
        db_session.add(cand_rec)
        db_session.commit()

        app_record = Application(
            company_id=company.id,
            job_id=job.id,
            candidate_id=cand_rec.id,
            status=ApplicationStatus.SUBMITTED
        )
        db_session.add(app_record)
        db_session.commit()

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

        # Create onboarding task
        task = CandidateTask(
            company_id=company.id,
            candidate_id=candidate.id,
            title="Complete your background check authorization",
            description="Provide background check authorization details.",
            status="pending",
            task_type="text",
            due_date=None
        )
        db_session.add(task)
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
        "task": task,
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

def test_list_and_update_task(api_client, db_session, test_setup):
    headers = test_setup["headers"]
    task_id = str(test_setup["task"].id)
    task = test_setup["task"]

    # 1. List Tasks
    resp = api_client.get("/api/v1/candidate/tasks", headers=headers)
    assert resp.status_code == 200
    tasks_list = resp.json()
    assert len(tasks_list) == 1
    assert tasks_list[0]["title"] == "Complete your background check authorization"

    # 2. Update Task Status
    payload = {
        "meta_payload": {"signature": "Signed candidate"},
        "client_updated_at": task.updated_at.isoformat()
    }
    resp = api_client.post(f"/api/v1/candidate/tasks/{task_id}/complete", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Assert status updated in db
    with tenant_context(auth_mode="true"):
        db_session.commit()
        db_session.expire_all()
        updated_task = db_session.get(CandidateTask, task.id)
        assert updated_task.status == "completed"

def test_update_task_optimistic_concurrency(api_client, db_session, test_setup):
    headers = test_setup["headers"]
    task_id = str(test_setup["task"].id)

    # Stale write update: client_updated_at is in the past compared to database
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    payload = {
        "meta_payload": {},
        "client_updated_at": stale_time
    }
    resp = api_client.post(f"/api/v1/candidate/tasks/{task_id}/complete", json=payload, headers=headers)
    assert resp.status_code == 409
    assert "modified" in resp.json()["detail"].lower()
