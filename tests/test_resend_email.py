import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from server import app
from db.session import get_db, tenant_context
from models import User, VerificationToken, AuditLog
from models.enums import UserRole, AuthProvider
from sqlalchemy import select
import resend
from core.auth_providers.email import DBVerificationTokenProvider

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


@pytest.fixture
def clean_redis():
    import redis
    from core.config import get_settings
    try:
        r = redis.from_url(get_settings().redis_url)
        # Flush keys used in rate limiting
        for key in r.scan_iter("otp:email:rate:*"):
            r.delete(key)
        for key in r.scan_iter("forgot:rate:*"):
            r.delete(key)
    except Exception:
        pass


def test_resend_provider_mock_fallback_and_api_call():
    """Verify ResendEmailProvider falls back cleanly if unconfigured, and calls SDK when configured."""
    from core.auth_providers.resend_provider import ResendEmailProvider

    # 1. Unconfigured API Key (starts with mock- or is None)
    with patch.dict("os.environ", {"RESEND_API_KEY": "mock-api-key"}):
        res = ResendEmailProvider.send_verification_email("test@example.com", "123456")
        assert res is False  # returns False to let the chain continue

    # 2. Configured API Key
    with patch.dict("os.environ", {"RESEND_API_KEY": "re_valid_key", "RESEND_SENDER_EMAIL": "no-reply@domain.com"}):
        with patch.object(resend.Emails, "send") as mock_send:
            res = ResendEmailProvider.send_verification_email("test@example.com", "123456")
            assert res is True
            mock_send.assert_called_once()
            args = mock_send.call_args[0][0]
            assert args["from"] == "no-reply@domain.com"
            assert args["to"] == "test@example.com"
            assert "123456" in args["html"]


def test_email_provider_fallback_chain():
    """Verify EmailProvider fallback chain: Resend -> SMTP -> Mock."""
    from core.auth_providers.email import EmailProvider

    # Scenario A: Resend succeeds -> SMTP & Mock skipped
    with patch("core.auth_providers.resend_provider.ResendEmailProvider._deliver", return_value=True) as mock_resend:
        with patch("core.auth_providers.email.EmailProvider._send_via_smtp") as mock_smtp:
            res = EmailProvider.send_verification_email("test@example.com", "123456")
            assert res is True
            mock_resend.assert_called_once()
            mock_smtp.assert_not_called()

    # Scenario B: Resend fails, SMTP succeeds -> Mock skipped
    with patch("core.auth_providers.resend_provider.ResendEmailProvider._deliver", return_value=False) as mock_resend:
        with patch("core.auth_providers.email.EmailProvider._send_via_smtp", return_value=True) as mock_smtp:
            res = EmailProvider.send_verification_email("test@example.com", "123456")
            assert res is True
            mock_resend.assert_called_once()
            mock_smtp.assert_called_once()

    # Scenario C: Resend fails, SMTP fails -> Mock fallback logs and prints
    with patch("core.auth_providers.resend_provider.ResendEmailProvider._deliver", return_value=False) as mock_resend:
        with patch("core.auth_providers.email.EmailProvider._send_via_smtp", return_value=False) as mock_smtp:
            with patch("core.auth_providers.email.logger.info") as mock_log:
                res = EmailProvider.send_verification_email("test@example.com", "123456")
                assert res is True  # Mock fallback resolves successfully
                mock_resend.assert_called_once()
                mock_smtp.assert_called_once()
                mock_log.assert_called_with("[EMAIL MOCK FALLBACK] Email verification code sent to test@example.com with code 123456")


def test_forgot_and_reset_password_flow_e2e(api_client, db_session, clean_redis):
    """Verify Forgot Password requesting, rate limits, token invalidation, and Reset Password completion."""
    # 1. Create a user
    with tenant_context(auth_mode="true"):
        user = User(
            email="reset-user@example.com",
            password_hash="old_password_hash",
            full_name="Reset User",
            role=UserRole.CANDIDATE,
            email_verified=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        user_id = user.id

    # 2. Trigger forgot password -> check token created with 30-min expiry
    with patch("core.auth_providers.email.EmailProvider.send_password_reset_email", return_value=True) as mock_send:
        resp = api_client.post("/api/v1/auth/forgot-password", json={"email": "reset-user@example.com"})
        assert resp.status_code == 200
        mock_send.assert_called_once()
        token_sent = mock_send.call_args[0][1]

        # Verify token in DB
        with tenant_context(auth_mode="true"):
            tokens = db_session.scalars(
                select(VerificationToken).where(
                    VerificationToken.user_id == user_id,
                    VerificationToken.token_type == "password_reset",
                    VerificationToken.consumed_at.is_(None)
                )
            ).all()
            assert len(tokens) == 1
            assert tokens[0].expires_at > datetime.now(timezone.utc) + timedelta(minutes=28)
            assert tokens[0].expires_at <= datetime.now(timezone.utc) + timedelta(minutes=30)

            # Check audit event auth.password_reset_requested
            audit = db_session.scalar(
                select(AuditLog).where(
                    AuditLog.action == "auth.password_reset_requested",
                    AuditLog.actor_id == user_id
                )
            )
            assert audit is not None

    # 3. Create a second reset token -> check it invalidates the first token (Invalidation Check)
    with patch("core.auth_providers.email.EmailProvider.send_password_reset_email", return_value=True):
        resp2 = api_client.post("/api/v1/auth/forgot-password", json={"email": "reset-user@example.com"})
        assert resp2.status_code == 200
        
        with tenant_context(auth_mode="true"):
            # Old token must be consumed
            old_token = db_session.scalar(
                select(VerificationToken).where(
                    VerificationToken.user_id == user_id,
                    VerificationToken.token_type == "password_reset",
                    VerificationToken.token_hash == DBVerificationTokenProvider.hash_token(token_sent)
                )
            )
            assert old_token.consumed_at is not None

            # New token must be active
            new_tokens = db_session.scalars(
                select(VerificationToken).where(
                    VerificationToken.user_id == user_id,
                    VerificationToken.token_type == "password_reset",
                    VerificationToken.consumed_at.is_(None)
                )
            ).all()
            assert len(new_tokens) == 1
            new_token_val = new_tokens[0]

    # 4. Trigger rate limit for forgot-password: 3 requests per 15 minutes
    # We already sent 2. Sending 3rd: should pass. Sending 4th: should be blocked.
    with patch("core.auth_providers.email.EmailProvider.send_password_reset_email", return_value=True):
        # 3rd request
        resp3 = api_client.post("/api/v1/auth/forgot-password", json={"email": "reset-user@example.com"})
        assert resp3.status_code == 200

        # 4th request -> Should fail with 429
        resp4 = api_client.post("/api/v1/auth/forgot-password", json={"email": "reset-user@example.com"})
        assert resp4.status_code == 429
        assert "limit exceeded" in resp4.json()["detail"].lower()

    # Clear rate limits to reset password
    from core.config import get_settings
    import redis
    try:
        r = redis.from_url(get_settings().redis_url)
        r.delete("forgot:rate:reset-user@example.com")
    except Exception:
        pass

    # Retrieve plaintext of the active token to reset
    # Find plaintext token: since we mocked it, let's grab it by querying DB, but we only have hash.
    # In test, we can query the token hash and mock a new token verification, or we can just fetch the active token code.
    # Let's create a known token value to reset with.
    with tenant_context(auth_mode="true"):
        known_token = "my-secure-reset-token-123"
        DBVerificationTokenProvider.create_token(
            db=db_session,
            user_id=user_id,
            token_type="password_reset",
            code=known_token,
            expires_in_minutes=30
        )

    # 5. Complete password reset with incorrect token -> Fail
    reset_payload_fail = {
        "email": "reset-user@example.com",
        "token": "wrong-token",
        "new_password": "super_new_password_123"
    }
    resp_reset_fail = api_client.post("/api/v1/auth/reset-password", json=reset_payload_fail)
    assert resp_reset_fail.status_code == 400

    # 6. Complete password reset with correct token -> Success
    reset_payload_success = {
        "email": "reset-user@example.com",
        "token": known_token,
        "new_password": "super_new_password_123"
    }
    resp_reset_success = api_client.post("/api/v1/auth/reset-password", json=reset_payload_success)
    assert resp_reset_success.status_code == 200
    assert "reset successfully" in resp_reset_success.json()["message"].lower()

    # Verify password hash updated in DB and audit log written
    with tenant_context(auth_mode="true"):
        updated_user = db_session.scalar(select(User).where(User.id == user_id))
        assert updated_user.password_hash != "old_password_hash"

        # Check audit event auth.password_reset_completed
        audit_comp = db_session.scalar(
            select(AuditLog).where(
                AuditLog.action == "auth.password_reset_completed",
                AuditLog.actor_id == user_id
            )
        )
        assert audit_comp is not None


def test_verification_otp_resend_rate_limit(api_client, db_session, clean_redis):
    """Verify Verification OTP resend limits after 5 requests per hour."""
    # Create user
    with tenant_context(auth_mode="true"):
        user = User(
            email="resend-limit@example.com",
            password_hash="pass_hash",
            full_name="Resend User",
            role=UserRole.RECRUITER,
            email_verified=False
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    # Trigger 5 requests
    with patch("core.auth_providers.email.EmailProvider.send_verification_email", return_value=True):
        for i in range(5):
            resp = api_client.post("/api/v1/auth/verify-email/resend", json={"email": "resend-limit@example.com"})
            assert resp.status_code == 200

        # 6th request should fail with 429
        resp_blocked = api_client.post("/api/v1/auth/verify-email/resend", json={"email": "resend-limit@example.com"})
        assert resp_blocked.status_code == 429
        assert "limit exceeded" in resp_blocked.json()["detail"].lower()
