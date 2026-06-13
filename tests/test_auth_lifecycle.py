import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from server import app
from db.session import get_db, tenant_context
from models import User, Company
from models.session import UserSession, RevokedToken
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


def test_registration_and_login_creates_session(api_client, db_session):
    """Verify that registering and logging in successfully creates active UserSession records."""
    # 1. Register a new user
    register_payload = {
        "company_name": "Lifecycle Inc",
        "email": "lifecycle@test.com",
        "password": "super-secure-password-123",
        "full_name": "Lifecycle Tester"
    }
    
    response = api_client.post("/api/v1/auth/register", json=register_payload)
    assert response.status_code == 201
    reg_data = response.json()
    assert reg_data["access_token"] is not None
    assert reg_data["refresh_token"] is not None
    assert response.cookies.get("refresh_token") == reg_data["refresh_token"]

    # Check database to verify that UserSession was created with correct metadata
    with tenant_context(auth_mode="true"):
        # Set email_verified=True to allow logging in
        user = db_session.get(User, reg_data["user"]["id"])
        if user:
            user.email_verified = True
            db_session.add(user)
            db_session.commit()

        sessions = db_session.scalars(
            select(UserSession).where(UserSession.user_id == reg_data["user"]["id"])
        ).all()
        assert len(sessions) == 1
        assert sessions[0].is_revoked is False
        assert sessions[0].ip_address == "testclient"
        assert sessions[0].created_at is not None

    # 2. Login
    login_payload = {
        "email": "lifecycle@test.com",
        "password": "super-secure-password-123"
    }
    
    login_response = api_client.post("/api/v1/auth/login", json=login_payload)
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["access_token"] is not None
    assert login_data["refresh_token"] is not None
    
    # Database should now have a second active session
    with tenant_context(auth_mode="true"):
        sessions = db_session.scalars(
            select(UserSession).where(UserSession.user_id == reg_data["user"]["id"])
        ).all()
        assert len(sessions) == 2


def test_refresh_token_flow(api_client, db_session):
    """Verify that exchanging a valid refresh token yields new tokens and updates the session."""
    register_payload = {
        "company_name": "Refresh Inc",
        "email": "refresh@test.com",
        "password": "super-secure-password-123",
        "full_name": "Refresh Tester"
    }
    response = api_client.post("/api/v1/auth/register", json=register_payload)
    reg_data = response.json()
    refresh_token = reg_data["refresh_token"]

    # Exchange refresh token via request body
    refresh_response = api_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    print("REFRESH RESPONSE DETAIL:", refresh_response.json())
    assert refresh_response.status_code == 200
    new_data = refresh_response.json()
    assert new_data["access_token"] != reg_data["access_token"]
    assert new_data["refresh_token"] != reg_data["refresh_token"]
    
    # Exchanging again with the OLD rotated token should trigger replay attack detection!
    replay_response = api_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert replay_response.status_code == 401
    assert "reuse detected" in replay_response.json()["detail"].lower()

    # The session in DB should now be marked as revoked
    with tenant_context(auth_mode="true"):
        session = db_session.scalar(
            select(UserSession).where(UserSession.user_id == reg_data["user"]["id"])
        )
        assert session.is_revoked is True


def test_logout_revokes_tokens(api_client, db_session):
    """Verify that logging out revokes the active session and blacklists the access token JTI."""
    register_payload = {
        "company_name": "Logout Inc",
        "email": "logout@test.com",
        "password": "super-secure-password-123",
        "full_name": "Logout Tester"
    }
    response = api_client.post("/api/v1/auth/register", json=register_payload)
    reg_data = response.json()
    access_token = reg_data["access_token"]
    refresh_token = reg_data["refresh_token"]

    # Set up client headers and cookies
    headers = {"Authorization": f"Bearer {access_token}"}
    api_client.cookies.set("refresh_token", refresh_token)

    logout_response = api_client.post("/api/v1/auth/logout", headers=headers)
    assert logout_response.status_code == 200
    assert logout_response.json()["success"] is True

    # Accessing /auth/me with the revoked access token should now be blocked
    me_response = api_client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 401
    assert "revoked" in me_response.json()["detail"].lower()

    # Exchanging the revoked refresh token should be blocked
    refresh_response = api_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401


def test_session_listing_and_revocation(api_client, db_session):
    """Verify that users can list their active sessions and revoke specific ones by ID."""
    register_payload = {
        "company_name": "Sessions Inc",
        "email": "sessions@test.com",
        "password": "super-secure-password-123",
        "full_name": "Sessions Tester"
    }
    response = api_client.post("/api/v1/auth/register", json=register_payload)
    reg_data = response.json()
    access_token = reg_data["access_token"]

    # Mark user as verified so that sessions endpoint is authorized
    with tenant_context(auth_mode="true"):
        user = db_session.get(User, reg_data["user"]["id"])
        if user:
            user.email_verified = True
            db_session.add(user)
            db_session.commit()

    headers = {"Authorization": f"Bearer {access_token}"}

    # 1. List active sessions
    sessions_response = api_client.get("/api/v1/auth/sessions", headers=headers)
    assert sessions_response.status_code == 200
    sessions_list = sessions_response.json()
    assert len(sessions_list) == 1
    session_id = sessions_list[0]["id"]

    # 2. Revoke session by ID
    revoke_response = api_client.post(
        "/api/v1/auth/sessions/revoke",
        json={"session_id": session_id},
        headers=headers
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["success"] is True

    # 3. Listing sessions again should be blocked with 401 (since the active session was revoked)
    sessions_response_after = api_client.get("/api/v1/auth/sessions", headers=headers)
    assert sessions_response_after.status_code == 401
