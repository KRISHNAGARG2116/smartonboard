import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select

from server import app
from db.session import get_db, tenant_context
from models import User, CandidateProfile
from models.enums import UserRole
from models.verification_token import VerificationToken
from core.verification_service import _mock_phone_otps

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
    """Verify that candidate register, verify, login, and get profile me endpoints function properly."""
    # 1. Register candidate
    reg_payload = {
        "email": "candidate_test@example.com",
        "password": "securepassword123",
        "full_name": "Jane Candidate",
        "phone_number": "+15551112222"
    }
    resp = api_client.post("/api/v1/auth/register/candidate", json=reg_payload)
    assert resp.status_code == 201
    reg_data = resp.json()
    assert reg_data["access_token"] is None
    assert reg_data["verification_required"] is True

    # Get email OTP from DB
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "candidate_test@example.com"))
        from core.auth_providers.email import DBVerificationTokenProvider
        email_otp = DBVerificationTokenProvider.create_token(
            db=db_session,
            user_id=user.id,
            token_type="email_otp",
            expires_in_minutes=10
        )

    # Verify Email OTP
    resp = api_client.post("/api/v1/auth/email/verify-otp", json={"email": "candidate_test@example.com", "code": email_otp})
    assert resp.status_code == 200

    # Get Phone OTP from mock service and verify
    phone_otp = _mock_phone_otps["+15551112222"]["code"]
    resp = api_client.post("/api/v1/auth/phone/verify-otp", json={"email": "candidate_test@example.com", "code": phone_otp})
    assert resp.status_code == 200
    login_data = resp.json()
    assert "access_token" in login_data
    token = login_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Login candidate (should now succeed since verified)
    login_payload = {
        "email": "candidate_test@example.com",
        "password": "securepassword123",
    }
    resp = api_client.post("/api/v1/auth/login/candidate", json=login_payload)
    assert resp.status_code == 200
    assert resp.json()["access_token"] is not None

    # 3. Get candidate profile
    resp = api_client.get("/api/v1/auth/candidate/me", headers=headers)
    assert resp.status_code == 200
    me_data = resp.json()
    assert me_data["user"]["email"] == "candidate_test@example.com"
    assert me_data["user"]["role"] == "candidate"

    # 4. Enforce role: candidate cannot access recruiter me endpoint
    resp = api_client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 403


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
    assert resp.status_code == 403


def test_candidate_profile_update_including_summary(api_client, db_session):
    """Verify that updating a candidate's profile full name, location, and summary works."""
    # 1. Register candidate
    email = "summary_test@example.com"
    phone = "+15552223333"
    reg_payload = {
        "email": email,
        "password": "securepassword123",
        "full_name": "Sam Candidate",
        "phone_number": phone
    }
    resp = api_client.post("/api/v1/auth/register/candidate", json=reg_payload)
    assert resp.status_code == 201

    # Verify Email and Phone to get active session
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == email))
        from core.auth_providers.email import DBVerificationTokenProvider
        email_otp = DBVerificationTokenProvider.create_token(
            db=db_session,
            user_id=user.id,
            token_type="email_otp",
            expires_in_minutes=10
        )

    resp = api_client.post("/api/v1/auth/email/verify-otp", json={"email": email, "code": email_otp})
    assert resp.status_code == 200

    phone_otp = _mock_phone_otps[phone]["code"]
    resp = api_client.post("/api/v1/auth/phone/verify-otp", json={"email": email, "code": phone_otp})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get candidate profile (initial summary is None)
    resp = api_client.get("/api/v1/auth/candidate/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["profile"]["summary"] is None

    # 3. Update candidate profile
    update_payload = {
        "full_name": "Sam Candidate Updated",
        "phone_number": "+15551234567",
        "location": "San Francisco, CA",
        "summary": "Experienced Full Stack Engineer specialized in React and FastAPI",
    }
    resp = api_client.put("/api/v1/auth/candidate/profile", json=update_payload, headers=headers)
    assert resp.status_code == 200
    updated_data = resp.json()
    assert updated_data["profile"]["full_name"] == "Sam Candidate Updated"
    assert updated_data["profile"]["location"] == "San Francisco, CA"
    assert updated_data["profile"]["summary"] == "Experienced Full Stack Engineer specialized in React and FastAPI"

    # 4. Fetch /candidate/me again to ensure persistence
    resp = api_client.get("/api/v1/auth/candidate/me", headers=headers)
    assert resp.status_code == 200
    me_data = resp.json()
    assert me_data["profile"]["full_name"] == "Sam Candidate Updated"
    assert me_data["profile"]["location"] == "San Francisco, CA"
    assert me_data["profile"]["summary"] == "Experienced Full Stack Engineer specialized in React and FastAPI"
