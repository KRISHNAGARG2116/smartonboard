import pytest
import uuid
from fastapi.testclient import TestClient
from server import app
from db.session import get_db, tenant_context
from models import User, Company
from models.enums import UserRole, AuthProvider, CompanyStatus
from models.candidate_profile import CandidateProfile
from sqlalchemy import select

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


def test_candidate_google_login_frictionless(api_client, db_session):
    """Verify first-time Google candidate login successfully creates a candidate account/profile."""
    # 1. First login (should return 403 as phone is not verified yet)
    payload = {
        "credential": "mock-google-token-candidate@public.com:sub-cand-1:None",
        "role": "candidate"
    }
    resp = api_client.post("/api/v1/auth/google", json=payload)
    assert resp.status_code == 403
    data = resp.json()["detail"]
    assert data["verification_required"] is True
    assert data["email"] == "candidate@public.com"
    assert data["email_verified"] is True
    assert data["phone_verified"] is False

    # Verify user exists in database with candidate profile
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "candidate@public.com"))
        assert user is not None
        assert user.google_subject_id == "sub-cand-1"
        assert user.auth_provider == AuthProvider.GOOGLE
        assert user.email_verified is True

        profile = db_session.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        assert profile is not None
        assert profile.email_verified is True
        assert profile.phone_verified is False

    # 2. Subsequent login with same credential before verification should still return 403
    resp2 = api_client.post("/api/v1/auth/google", json=payload)
    assert resp2.status_code == 403


def test_recruiter_google_login_wizard_flow(api_client, db_session):
    """Verify recruiter login registers with company_id=None, and requires Setup Wizard."""
    # 1. Register recruiter via Google
    payload = {
        "credential": "mock-google-token-recruiter@acme.com:sub-rec-1:None",
        "role": "recruiter"
    }
    resp = api_client.post("/api/v1/auth/google", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    access_token = data["access_token"]
    assert data["user"]["company_id"] is None
    assert data["user"]["role"] == "owner"

    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Try accessing a protected company endpoint - should be blocked by ProtectedRoute equivalent (or company_id missing in JWT context)
    # The API layer requires company_id for standard endpoints. Let's verify /companies/me returns 401/403 or similar
    comp_resp = api_client.get("/api/v1/companies/me", headers=headers)
    assert comp_resp.status_code in [401, 403, 404]

    # 3. Setup Company with mismatching domain -> Fail
    setup_payload_mismatch = {
        "company_name": "Acme Corp",
        "company_website": "https://acme.com",
        "company_domain": "microsoft.com",
        "industry": "Software",
        "company_size": "11-50"
    }
    setup_resp = api_client.post("/api/v1/auth/setup-company", json=setup_payload_mismatch, headers=headers)
    assert setup_resp.status_code == 400
    assert "domain" in setup_resp.json()["detail"].lower()

    # 4. Setup Company with matching domain -> Success
    setup_payload_match = {
        "company_name": "Acme Corp",
        "company_website": "https://acme.com",
        "company_domain": "acme.com",
        "industry": "Software",
        "company_size": "11-50"
    }
    setup_resp = api_client.post("/api/v1/auth/setup-company", json=setup_payload_match, headers=headers)
    assert setup_resp.status_code == 200
    setup_data = setup_resp.json()
    assert setup_data["user"]["company_id"] is not None
    new_access_token = setup_data["access_token"]
    new_headers = {"Authorization": f"Bearer {new_access_token}"}

    # Verify company is created in database
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "recruiter@acme.com"))
        assert user.company_id is not None
        company = db_session.scalar(select(Company).where(Company.id == user.company_id))
        assert company is not None
        assert company.settings["domain"] == "acme.com"
        assert company.settings["website"] == "https://acme.com"

    # 5. Access company endpoint now -> Success
    comp_resp2 = api_client.get("/api/v1/companies/me", headers=new_headers)
    assert comp_resp2.status_code == 200


def test_role_mismatch_protection(api_client, db_session):
    """Verify role mismatch is strictly blocked."""
    # Register candidate first
    payload_cand = {
        "credential": "mock-google-token-mismatch@test.com:sub-mis-1:None",
        "role": "candidate"
    }
    api_client.post("/api/v1/auth/google", json=payload_cand)

    # Attempt to login with same email as Recruiter -> Should fail
    payload_rec = {
        "credential": "mock-google-token-mismatch@test.com:sub-mis-1:None",
        "role": "recruiter"
    }
    resp = api_client.post("/api/v1/auth/google", json=payload_rec)
    assert resp.status_code == 400
    assert "role mismatch" in resp.json()["detail"].lower()


def test_public_email_rejection_for_recruiters(api_client):
    """Verify recruiters are blocked from using public domains (gmail, yahoo, etc.)."""
    payload = {
        "credential": "mock-google-token-hacker@gmail.com:sub-hack-1:None",
        "role": "recruiter"
    }
    resp = api_client.post("/api/v1/auth/google", json=payload)
    assert resp.status_code == 400
    assert "public email" in resp.json()["detail"].lower()


def test_google_workspace_hosted_domain_verification(api_client, db_session):
    """Verify hosted domain claim validation matches company domain."""
    payload = {
        "credential": "mock-google-token-manager@acme.com:sub-work-1:acme.com", # acme.com as hosted domain (hd)
        "role": "recruiter"
    }
    resp = api_client.post("/api/v1/auth/google", json=payload)
    assert resp.status_code == 200
    access_token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Attempt setup company with a domain that is mismatching hd claim
    setup_payload_mismatch = {
        "company_name": "Acme Corp",
        "company_website": "https://acme.com",
        "company_domain": "microsoft.com", # Mismatches hd
        "industry": "Consulting",
        "company_size": "1-10"
    }
    setup_resp = api_client.post("/api/v1/auth/setup-company", json=setup_payload_mismatch, headers=headers)
    assert setup_resp.status_code == 400


def test_failed_login_lockout_rate_limit(api_client):
    """Verify failed login lockout rate limits after 5 failures."""
    # Reset/clear lockout state if any from other tests (uses localhost IP usually)
    import redis
    from core.config import get_settings
    try:
        r = redis.from_url(get_settings().redis_url)
        r.delete("google:failed:testclient")
        r.delete("google:blocked:testclient")
        r.delete("google:failed:127.0.0.1")
        r.delete("google:blocked:127.0.0.1")
    except Exception:
        pass

    try:
        from api.auth import _failed_google_attempts
        _failed_google_attempts.clear()
    except Exception:
        pass

    # We send invalid credentials to trigger failures
    payload = {
        "credential": "invalid-google-token",
        "role": "candidate"
    }

    # Trigger 5 failures
    for i in range(5):
        resp = api_client.post("/api/v1/auth/google", json=payload)
        assert resp.status_code == 400

    # 6th request should be locked out with 429
    resp_lockout = api_client.post("/api/v1/auth/google", json=payload)
    assert resp_lockout.status_code == 429
    assert "too many failed" in resp_lockout.json()["detail"].lower()
