import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from server import app
from db.session import get_db, tenant_context
from models import User, Company, Job, Application, Candidate, CandidateMessage, UserSession
from models.enums import UserRole, ApplicationStatus, JobStatus
from core.security import create_access_token

@pytest.fixture
def test_setup(db_session):
    with tenant_context(auth_mode="true"):
        company = Company(name="Test Company", slug="test-company")
        db_session.add(company)
        db_session.commit()

        candidate = User(
            email="candidate_msg@example.com",
            password_hash="hashed_password",
            full_name="Candidate Message",
            role=UserRole.CANDIDATE,
            is_active=True
        )
        db_session.add(candidate)

        recruiter = User(
            email="recruiter_msg@example.com",
            password_hash="hashed_password",
            full_name="Recruiter Msg",
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

def test_send_and_list_message(api_client, db_session, test_setup):
    headers = test_setup["headers"]
    app_id = str(test_setup["application"].id)

    payload = {
        "application_id": app_id,
        "content": "Hello, I am interested in this role!"
    }
    resp = api_client.post("/api/v1/candidate/messages", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["status"] == "sent"

    # List messages
    resp = api_client.get(f"/api/v1/candidate/messages?application_id={app_id}", headers=headers)
    assert resp.status_code == 200
    list_data = resp.json()
    assert len(list_data) == 1
    assert list_data[0]["content"] == "Hello, I am interested in this role!"

def test_edit_message_optimistic_concurrency(api_client, db_session, test_setup):
    headers = test_setup["headers"]
    app_id = str(test_setup["application"].id)

    payload = {
        "application_id": app_id,
        "content": "Initial Message"
    }
    resp = api_client.post("/api/v1/candidate/messages", json=payload, headers=headers)
    msg_id = resp.json()["id"]

    # Sleep slightly or manually update database timestamp to simulate concurrency
    with tenant_context(auth_mode="true"):
        msg = db_session.get(CandidateMessage, uuid.UUID(msg_id))
        msg.updated_at = datetime.now(timezone.utc)
        db_session.add(msg)
        db_session.commit()
        db_updated_time = msg.updated_at.isoformat()

    # Stale write update: client_updated_at is in the past compared to database
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    edit_payload = {
        "content": "Edited Content",
        "client_updated_at": stale_time
    }
    resp = api_client.put(f"/api/v1/candidate/messages/{msg_id}", json=edit_payload, headers=headers)
    assert resp.status_code == 409
    assert "modified" in resp.json()["detail"].lower()
