import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select

from server import app
from db.session import get_db, tenant_context
from models import User, CandidateProfile, UserSession
from models.verification_token import VerificationToken
from models.enums import UserRole, AuthProvider
from core.security import create_access_token, create_refresh_token
from core.verification_service import _mock_phone_otps, _mock_phone_lockouts, _mock_phone_rate_limits

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
    
    # Reset in-memory verification service state
    _mock_phone_otps.clear()
    _mock_phone_lockouts.clear()
    _mock_phone_rate_limits.clear()


def test_candidate_registration_withholds_jwt_and_requires_phone(api_client, db_session):
    """Assert that registration requires a phone number, sends OTPs, and withholds JWT tokens."""
    reg_payload = {
        "email": "verify_test@example.com",
        "password": "securepassword123",
        "full_name": "Jane Verification",
        "phone_number": "+15550199011"
    }
    
    resp = api_client.post("/api/v1/auth/register/candidate", json=reg_payload)
    assert resp.status_code == 201
    data = resp.json()
    
    # Assert that no tokens are returned and verification is required
    assert data["access_token"] is None
    assert data["refresh_token"] is None
    assert data["verification_required"] is True
    assert data["user"]["email"] == "verify_test@example.com"
    assert data["user"]["email_verified"] is False
    assert data["user"]["phone_verified"] is False

    # Assert database state
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "verify_test@example.com"))
        assert user is not None
        assert user.email_verified is False
        
        profile = db_session.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        assert profile is not None
        assert profile.phone_number == "+15550199011"
        assert profile.phone_verified is False
        assert profile.email_verified is False

        # Assert email token was created in DB
        email_token = db_session.scalar(
            select(VerificationToken).where(
                VerificationToken.user_id == user.id,
                VerificationToken.token_type == "email_otp",
                VerificationToken.consumed_at.is_(None)
            )
        )
        assert email_token is not None

        # Assert phone OTP was generated in Mock VerificationService
        assert "+15550199011" in _mock_phone_otps
        assert len(_mock_phone_otps["+15550199011"]["code"]) == 6


def test_candidate_login_unverified_blocked_with_403(api_client, db_session):
    """Assert that an unverified candidate cannot log in and receives a 403 carrying status metadata."""
    # 1. Register candidate
    reg_payload = {
        "email": "unverified_login@example.com",
        "password": "securepassword123",
        "full_name": "Jane Unverified",
        "phone_number": "+15550199022"
    }
    api_client.post("/api/v1/auth/register/candidate", json=reg_payload)

    # 2. Attempt login
    login_payload = {
        "email": "unverified_login@example.com",
        "password": "securepassword123"
    }
    resp = api_client.post("/api/v1/auth/login/candidate", json=login_payload)
    assert resp.status_code == 403
    
    data = resp.json()["detail"]
    assert data["verification_required"] is True
    assert data["email"] == "unverified_login@example.com"
    assert data["email_verified"] is False
    assert data["phone_verified"] is False
    assert data["phone_number"] == "+15550199022"


def test_verification_status_endpoint(api_client, db_session):
    """Assert that GET /auth/verification-status returns the correct verification state."""
    # 1. Register candidate
    reg_payload = {
        "email": "status_check@example.com",
        "password": "securepassword123",
        "full_name": "Jane Status",
        "phone_number": "+15550199033"
    }
    api_client.post("/api/v1/auth/register/candidate", json=reg_payload)

    # 2. Check status
    resp = api_client.get("/api/v1/auth/verification-status?email=status_check@example.com")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email_verified"] is False
    assert data["phone_verified"] is False
    assert data["verification_required"] is True
    assert data["phone_number"] == "+15550199033"


def test_independent_verification_and_automatic_jwt_issuance(api_client, db_session):
    """Assert that email and phone verifications are independent and issue a JWT only when both are done."""
    # 1. Register candidate
    email = "independent_verify@example.com"
    phone = "+15550199044"
    reg_payload = {
        "email": email,
        "password": "securepassword123",
        "full_name": "Jane Independent",
        "phone_number": phone
    }
    api_client.post("/api/v1/auth/register/candidate", json=reg_payload)

    # 2. Retrieve email OTP from DB
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == email))
        token_hash = db_session.scalar(
            select(VerificationToken.token_hash).where(
                VerificationToken.user_id == user.id,
                VerificationToken.token_type == "email_otp",
                VerificationToken.consumed_at.is_(None)
            )
        )
        # We need the plaintext token, but it's hashed. Since we're in mock mode,
        # we can bypass or query the token. Wait, DBVerificationTokenProvider.create_token
        # returns the plaintext, but we registered via registration endpoint and didn't capture it.
        # Let's override it or create a new token.
        from core.auth_providers.email import DBVerificationTokenProvider
        email_otp = DBVerificationTokenProvider.create_token(
            db=db_session,
            user_id=user.id,
            token_type="email_otp",
            expires_in_minutes=10
        )

    # 3. Verify email OTP
    resp = api_client.post("/api/v1/auth/email/verify-otp", json={"email": email, "code": email_otp})
    assert resp.status_code == 200
    data = resp.json()
    
    # Assert email is verified but no JWT is returned
    assert "access_token" not in data
    assert data["email_verified"] is True
    assert data["phone_verified"] is False

    # 4. Retrieve phone OTP from Mock service
    phone_otp = _mock_phone_otps[phone]["code"]

    # 5. Verify phone OTP
    resp = api_client.post("/api/v1/auth/phone/verify-otp", json={"email": email, "code": phone_otp})
    assert resp.status_code == 200
    data = resp.json()
    
    # Assert that since both are now verified, JWT IS returned!
    assert "access_token" in data
    assert data["access_token"] is not None
    assert data["user"]["email_verified"] is True
    assert data["user"]["phone_verified"] is True


def test_google_candidate_flow_phone_verification(api_client, db_session):
    """Assert that Google candidates skip email verification and are prompted for phone verification."""
    # Authenticate via Google
    google_payload = {
        "credential": "mock-google-token-candidate_google@example.com:sub-12345:hd-none",
        "role": "candidate"
    }
    
    # Assert that login fails with 403, email is verified, phone is unverified
    resp = api_client.post("/api/v1/auth/google", json=google_payload)
    assert resp.status_code == 403
    data = resp.json()["detail"]
    assert data["verification_required"] is True
    assert data["email"] == "candidate_google@example.com"
    assert data["email_verified"] is True
    assert data["phone_verified"] is False
    assert data["phone_number"] is None

    # Request Phone OTP (specifying phone number for the first time)
    send_payload = {
        "email": "candidate_google@example.com",
        "phone_number": "+15550199055"
    }
    resp = api_client.post("/api/v1/auth/phone/send-otp", json=send_payload)
    assert resp.status_code == 200

    # Retrieve phone OTP
    phone_otp = _mock_phone_otps["+15550199055"]["code"]

    # Verify Phone OTP
    verify_payload = {
        "email": "candidate_google@example.com",
        "code": phone_otp
    }
    resp = api_client.post("/api/v1/auth/phone/verify-otp", json=verify_payload)
    assert resp.status_code == 200
    data = resp.json()
    
    # Assert JWT is issued successfully
    assert "access_token" in data
    assert data["access_token"] is not None
    assert data["user"]["email_verified"] is True
    assert data["user"]["phone_verified"] is True


def test_phone_number_change_flow(api_client, db_session):
    """Assert that candidates can change their phone number and request a fresh OTP."""
    # 1. Register candidate
    email = "phone_change@example.com"
    reg_payload = {
        "email": email,
        "password": "securepassword123",
        "full_name": "Jane Phone Change",
        "phone_number": "+15550199066"
    }
    api_client.post("/api/v1/auth/register/candidate", json=reg_payload)
    assert "+15550199066" in _mock_phone_otps

    # 2. Change phone number and send OTP
    send_payload = {
        "email": email,
        "phone_number": "+15550199077"
    }
    resp = api_client.post("/api/v1/auth/phone/send-otp", json=send_payload)
    assert resp.status_code == 200

    # Assert new phone is stored and has active OTP, old phone is cleared
    assert "+15550199066" not in _mock_phone_otps
    assert "+15550199077" in _mock_phone_otps

    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == email))
        assert user.candidate_profile.phone_number == "+15550199077"
        assert user.candidate_profile.phone_verified is False


def test_backend_enforced_route_protection_by_verified_candidate(api_client, db_session):
    """Assert that candidate workspace APIs require VerifiedCandidate and reject unverified tokens."""
    # 1. Register candidate (unverified)
    email = "unverified_route@example.com"
    reg_payload = {
        "email": email,
        "password": "securepassword123",
        "full_name": "Jane Route Protection",
        "phone_number": "+15550199088"
    }
    api_client.post("/api/v1/auth/register/candidate", json=reg_payload)

    # 2. Manually generate a JWT token for the unverified user to simulate bypassing frontend guards
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == email))
        
        # Create a session
        session_id = uuid.uuid4()
        session = UserSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash="mock_hash",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc)
        )
        db_session.add(session)
        db_session.commit()

        token = create_access_token(
            str(user.id),
            {
                "company_id": None,
                "role": UserRole.CANDIDATE.value,
                "email": user.email,
                "session_id": str(session_id)
            }
        )

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Attempt to access candidate resumes (protected workspace route)
    resp = api_client.get("/api/v1/auth/candidate/resumes", headers=headers)
    
    # Assert that the backend rejects the request with a 403 Forbidden
    assert resp.status_code == 403
    assert "verified" in resp.json()["detail"].lower()


def test_twilio_verify_mock_lockout_and_rate_limiting(api_client, db_session):
    """Assert that the phone OTP service enforces rate limits (5 sends/hr) and lockouts (5 failed checks/15min)."""
    # 1. Register candidate
    email = "lockout_test@example.com"
    phone = "+15550199099"
    reg_payload = {
        "email": email,
        "password": "securepassword123",
        "full_name": "Jane Lockout",
        "phone_number": phone
    }
    api_client.post("/api/v1/auth/register/candidate", json=reg_payload)

    # 2. Enforce Rate Limits: Request OTP 4 more times (total 5 sends in last hour)
    for _ in range(4):
        resp = api_client.post("/api/v1/auth/phone/send-otp", json={"email": email, "phone_number": phone})
        assert resp.status_code == 200

    # 6th request should fail with a 429 Too Many Requests
    resp = api_client.post("/api/v1/auth/phone/send-otp", json={"email": email, "phone_number": phone})
    assert resp.status_code == 429
    assert "limit exceeded" in resp.json()["detail"].lower()

    # Clear rate limits for lockout test
    _mock_phone_rate_limits.clear()

    # Request fresh OTP
    api_client.post("/api/v1/auth/phone/send-otp", json={"email": email, "phone_number": phone})

    # 3. Enforce Lockout: Submit incorrect code 4 times (total 4 failed attempts)
    for _ in range(4):
        resp = api_client.post("/api/v1/auth/phone/verify-otp", json={"email": email, "code": "000000"})
        assert resp.status_code == 400
        assert "remaining" in resp.json()["detail"]

    # 5th incorrect code should trigger a 403 Forbidden lockout
    resp = api_client.post("/api/v1/auth/phone/verify-otp", json={"email": email, "code": "000000"})
    assert resp.status_code == 403
    assert "locked out" in resp.json()["detail"].lower()

    # Subsequent verification requests (even with correct code) should immediately fail with 403
    resp = api_client.post("/api/v1/auth/phone/verify-otp", json={"email": email, "code": "123456"})
    assert resp.status_code == 403
