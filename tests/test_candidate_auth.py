import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select

from server import app
from db.session import get_db, tenant_context
from models import User, CandidateProfile
from models.enums import UserRole

@pytest.fixture
def api_client(db_session):
    # Override get_db to use our test database session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_candidate_registration_and_login_flow(api_client, db_session):
    """Verify that candidate register, login, and get profile me endpoints function properly."""
    # 1. Register candidate
    reg_payload = {
        "email": "candidate_test@example.com",
        "password": "securepassword123",
        "full_name": "Jane Candidate",
    }
    resp = api_client.post("/api/v1/auth/register/candidate", json=reg_payload)
    assert resp.status_code == 201
    reg_data = resp.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == "candidate_test@example.com"
    assert reg_data["user"]["role"] == "candidate"
    assert reg_data["user"]["company_id"] is None

    # Check database persistence
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "candidate_test@example.com"))
        assert user is not None
        assert user.role == UserRole.CANDIDATE
        
        profile = db_session.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        assert profile is not None
        assert profile.full_name == "Jane Candidate"

    # 2. Login candidate
    login_payload = {
        "email": "candidate_test@example.com",
        "password": "securepassword123",
    }
    resp = api_client.post("/api/v1/auth/login/candidate", json=login_payload)
    assert resp.status_code == 200
    login_data = resp.json()
    assert "access_token" in login_data
    token = login_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Get candidate profile
    resp = api_client.get("/api/v1/auth/candidate/me", headers=headers)
    assert resp.status_code == 200
    me_data = resp.json()
    assert me_data["user"]["email"] == "candidate_test@example.com"
    assert me_data["user"]["role"] == "candidate"

    # 4. Enforce role: candidate cannot access recruiter me endpoint
    resp = api_client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 403  # get_current_user expects company_id in token


def test_recruiter_cannot_access_candidate_me(api_client, db_session):
    """Verify that recruiter tokens are rejected on candidate-only routes."""
    # Register recruiter
    payload = {
        "email": "recruiter_test@corp.com",
        "password": "securepassword123",
        "full_name": "John Recruiter",
        "company_name": "Test Company",
    }
    resp = api_client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    rec_token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {rec_token}"}

    # Recruiter attempts candidate me
    resp = api_client.get("/api/v1/auth/candidate/me", headers=headers)
    assert resp.status_code == 403  # requires role == candidate
