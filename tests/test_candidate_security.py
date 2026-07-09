import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from server import app
from db.session import get_db, tenant_context
from models import User, Company, UserSession
from models.enums import UserRole
from core.security import create_access_token

@pytest.fixture
def test_setup(db_session):
    with tenant_context(auth_mode="true"):
        company = Company(name="Test Company", slug="test-company")
        db_session.add(company)
        db_session.commit()

        candidate = User(
            email="candidate_sec@example.com",
            password_hash="hashed_password",
            full_name="Candidate Sec",
            role=UserRole.CANDIDATE,
            is_active=True
        )
        db_session.add(candidate)

        recruiter = User(
            email="recruiter_sec@example.com",
            password_hash="hashed_password",
            full_name="Recruiter Sec",
            role=UserRole.RECRUITER,
            company_id=company.id,
            is_active=True
        )
        db_session.add(recruiter)
        db_session.commit()

        session_cand = UserSession(
            id=uuid.uuid4(),
            user_id=candidate.id,
            refresh_token_hash=str(uuid.uuid4()),
            is_revoked=False,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc)
        )
        db_session.add(session_cand)

        session_rec = UserSession(
            id=uuid.uuid4(),
            user_id=recruiter.id,
            refresh_token_hash=str(uuid.uuid4()),
            is_revoked=False,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc)
        )
        db_session.add(session_rec)
        db_session.commit()

    candidate_token = create_access_token(
        str(candidate.id),
        {
            "company_id": None,
            "role": UserRole.CANDIDATE.value,
            "email": candidate.email,
            "session_id": str(session_cand.id)
        }
    )

    recruiter_token = create_access_token(
        str(recruiter.id),
        {
            "company_id": str(company.id),
            "role": UserRole.RECRUITER.value,
            "email": recruiter.email,
            "session_id": str(session_rec.id)
        }
    )

    return {
        "company": company,
        "candidate": candidate,
        "recruiter": recruiter,
        "candidate_headers": {"Authorization": f"Bearer {candidate_token}"},
        "recruiter_headers": {"Authorization": f"Bearer {recruiter_token}"}
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

def test_recruiter_accessing_candidate_endpoints_forbidden(api_client, db_session, test_setup):
    # Recruiter token accessing candidate workspace dashboard must return HTTP 403 Forbidden
    headers = test_setup["recruiter_headers"]
    resp = api_client.get("/api/v1/candidate/dashboard", headers=headers)
    assert resp.status_code == 403
    assert "candidate" in resp.json()["detail"].lower()

def test_candidate_accessing_recruiter_endpoints_forbidden(api_client, db_session, test_setup):
    # Candidate token accessing recruiter settings / jobs must return HTTP 403 Forbidden
    headers = test_setup["candidate_headers"]
    resp = api_client.get("/api/v1/jobs", headers=headers)
    assert resp.status_code == 403
