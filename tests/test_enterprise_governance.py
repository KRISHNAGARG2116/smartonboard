import json
import uuid
import ipaddress
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest
from sqlalchemy import select

from server import app
from db.session import get_db, tenant_context
from models import Company, User, AuditLog
from models.enterprise import CompanyIPWhitelist, CompanySMTPSettings
from core.vault import SecretVaultService
from core.smtp import get_smtp_transport_details
from tasks.smtp import reverify_all_smtp_settings_task
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(db_session):
    def override_get_db():
        try:
            db_session.expire_all()
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# =========================================================================
# 1. IP Whitelisting Middleware, Proxy Spoofing & Lockout Protection Tests
# =========================================================================

def test_ip_whitelist_middleware_and_lockout_protection(api_client, db_session, monkeypatch):
    """
    Validates that:
    1. Lockout protection blocks recruiters from saving a CIDR excluding their current connection IP.
    2. IPWhitelistMiddleware blocks unauthorized client IPs with 403 Forbidden and logs violations.
    3. Standard public asset paths bypass whitelisting.
    4. X-Forwarded-For is parsed from TRUSTED_PROXIES, but ignored if the socket is not trusted (spoof guard).
    """
    # Force trusted proxies list
    monkeypatch.setenv("TRUSTED_PROXIES", "127.0.0.1, 10.0.0.0/8")

    # 1. Register recruiter and company
    resp_reg = api_client.post("/api/v1/auth/register", json={
        "company_name": "Perimeter Corp",
        "email": "admin@perimeter.com",
        "password": "secure-password",
        "full_name": "Admin User"
    })
    assert resp_reg.status_code == 201
    reg_data = resp_reg.json()
    headers = {"Authorization": f"Bearer {reg_data['access_token']}"}
    company_id = uuid.UUID(reg_data["user"]["company_id"])

    # Mark recruiter as email verified
    with tenant_context(auth_mode="true"):
        user = db_session.get(User, uuid.UUID(reg_data["user"]["id"]))
        if user:
            user.email_verified = True
            db_session.add(user)
            db_session.commit()

    # 2. Test Lockout Protection
    # Client IP is mock socket host (default FastAPI TestClient socket host is 'testclient' or '127.0.0.1')
    # If client IP is resolved as '127.0.0.1', submitting '192.168.1.0/24' should trigger a lockout error!
    resp_lockout = api_client.post(
        "/api/v1/enterprise/ip-whitelist",
        headers=headers,
        json={
            "cidr_block": "192.168.1.0/24",
            "description": "Excludes loopback (fails lockout protection)"
        }
    )
    assert resp_lockout.status_code == 400
    assert "Lockout protection" in resp_lockout.json()["detail"]

    # Now create a valid whitelist containing our connection IP (127.0.0.1 belongs to '127.0.0.0/8')
    resp_whitelist = api_client.post(
        "/api/v1/enterprise/ip-whitelist",
        headers=headers,
        json={
            "cidr_block": "127.0.0.0/8",
            "description": "Includes loopback (succeeds)"
        }
    )
    assert resp_whitelist.status_code == 201
    whitelist_id = uuid.UUID(resp_whitelist.json()["id"])

    # Assert enterprise.ip_whitelisted audit event logged
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        audit_event = db_session.scalar(select(AuditLog).where(AuditLog.action == "enterprise.ip_whitelisted"))
        assert audit_event is not None
        assert audit_event.company_id == company_id
        assert audit_event.metadata_json["cidr_block"] == "127.0.0.0/8"

    # 3. Test listing and active matching: Access from 127.0.0.1 is whitelisted, so access to a route (e.g. GET /smtp) should pass whitelisting
    # Wait, GET /smtp returns 404 because SMTP is not configured yet, but it's not a 403 Forbidden!
    resp_access_ok = api_client.get("/api/v1/enterprise/smtp", headers=headers)
    assert resp_access_ok.status_code == 404

    # 4. Test Ingress IP Blocking (Middleware)
    # If we connect with X-Forwarded-For = '192.168.5.5' via trusted proxy 127.0.0.1, resolved client IP is 192.168.5.5.
    # 192.168.5.5 is not inside '127.0.0.0/8', so access should be blocked with 403!
    headers_via_proxy = {
        "Authorization": f"Bearer {resp_reg.json()['access_token']}",
        "X-Forwarded-For": "192.168.5.5"
    }
    resp_access_blocked = api_client.get("/api/v1/enterprise/smtp", headers=headers_via_proxy)
    assert resp_access_blocked.status_code == 403
    assert "Access denied: Your IP address (192.168.5.5) is not whitelisted" in resp_access_blocked.json()["detail"]

    # Verify enterprise.ip_whitelist_violated was logged in audit logs
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        violation_event = db_session.scalar(select(AuditLog).where(AuditLog.action == "enterprise.ip_whitelist_violated"))
        assert violation_event is not None
        assert violation_event.company_id == company_id
        assert violation_event.metadata_json["blocked_ip"] == "192.168.5.5"

    # 5. Test Public Path Bypassing: Auth login route is public, should bypass middleware regardless of IP
    resp_public_bypass = api_client.post("/api/v1/auth/login", json={
        "email": "admin@perimeter.com",
        "password": "secure-password"
    }, headers=headers_via_proxy)
    # Public auth logins bypass whitelisting (succeeds or returns normal auth error, never 403)
    assert resp_public_bypass.status_code != 403

    # 6. Test Spoofing Guard: Client socket host is mock socket. If socket is NOT a trusted proxy,
    # X-Forwarded-For is ignored completely.
    # To test this, let's configure trusted proxies to EXCLUDE 127.0.0.1 (e.g. only '10.0.0.0/8')
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.0/8")

    # Access via 127.0.0.1 socket with X-Forwarded-For: 192.168.5.5 should succeed (or 404),
    # since socket 127.0.0.1 is no longer trusted, XFF is ignored, and client IP resolves to 127.0.0.1
    resp_access_spoof_ignored = api_client.get("/api/v1/enterprise/smtp", headers=headers_via_proxy)
    assert resp_access_spoof_ignored.status_code == 404  # Passes whitelist check!

    # 7. Delete Whitelist
    monkeypatch.setenv("TRUSTED_PROXIES", "127.0.0.1, 10.0.0.0/8")
    resp_delete = api_client.delete(f"/api/v1/enterprise/ip-whitelist/{whitelist_id}", headers=headers)
    assert resp_delete.status_code == 204

    # Verify enterprise.ip_whitelist_removed audit event logged
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        del_event = db_session.scalar(select(AuditLog).where(AuditLog.action == "enterprise.ip_whitelist_removed"))
        assert del_event is not None
        assert del_event.company_id == company_id
        assert del_event.metadata_json["ip_whitelist_id"] == str(whitelist_id)


# =========================================================================
# 2. Custom SMTP Settings verification, rotation and 90-day sweep tests
# =========================================================================

def test_smtp_settings_rotation_handshake_and_expiry_sweeper(api_client, db_session):
    """
    Validates that:
    1. Creating SMTP settings encrypts credentials, sets status to 'pending', and logs audit event.
    2. Rotation of credentials resets status to 'pending', updates last_rotated_at, and logs rotations.
    3. Handshake verify promotes settings to 'verified' on success, or 'failed' on error.
    4. get_smtp_transport_details returns global fallback unless custom settings are 'verified' and < 90 days.
    5. Daily sweeper reverifies expired (>90 days) credentials, transitioning states and logging audit actions.
    """
    # 1. Register company
    resp_reg = api_client.post("/api/v1/auth/register", json={
        "company_name": "Mail Gateway Corp",
        "email": "owner@gateway.com",
        "password": "secure-password",
        "full_name": "Owner User"
    })
    assert resp_reg.status_code == 201
    reg_data = resp_reg.json()
    headers = {"Authorization": f"Bearer {reg_data['access_token']}"}
    company_id = uuid.UUID(reg_data["user"]["company_id"])

    # Mark recruiter as email verified
    with tenant_context(auth_mode="true"):
        user = db_session.get(User, uuid.UUID(reg_data["user"]["id"]))
        if user:
            user.email_verified = True
            db_session.add(user)
            db_session.commit()

    # 2. Create Custom SMTP Settings
    resp_create = api_client.post(
        "/api/v1/enterprise/smtp",
        headers=headers,
        json={
            "hostname": "smtp.mail.corporate.com",
            "port": 587,
            "username": "smtp_user",
            "password": "super-secret-smtp-password",
            "sender_email": "notifications@corporate.com"
        }
    )
    assert resp_create.status_code == 200
    smtp_data = resp_create.json()
    assert smtp_data["verification_status"] == "pending"
    assert smtp_data["hostname"] == "smtp.mail.corporate.com"
    assert smtp_data["sender_email"] == "notifications@corporate.com"

    # Verify RLS-encrypted password is correct and vault is populated
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        smtp_obj = db_session.scalar(select(CompanySMTPSettings).where(CompanySMTPSettings.company_id == company_id))
        assert smtp_obj is not None
        assert smtp_obj.encrypted_password is not None
        assert smtp_obj.verification_status == "pending"

        # Verify enterprise.smtp_rotation audit event
        audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "enterprise.smtp_rotation"))
        assert audit is not None
        assert audit.company_id == company_id

    # 3. Verify get_smtp_transport_details falls back to global default (since custom status is 'pending')
    with tenant_context(tenant_id=str(company_id)):
        transport_details = get_smtp_transport_details(db_session, company_id)
    assert transport_details["use_custom"] is False
    assert transport_details["hostname"] == "smtp.example.com"  # Fallback host

    # 4. Test SMTP Handshake Success (Mocked)
    with patch("api.enterprise.verify_smtp_credentials") as mock_handshake:
        # Mock success
        mock_handshake.return_value = None

        resp_verify = api_client.post("/api/v1/enterprise/smtp/test", headers=headers)
        assert resp_verify.status_code == 200
        assert resp_verify.json()["verification_status"] == "verified"
        assert resp_verify.json()["last_verified_at"] is not None

        # Assert enterprise.smtp_configured audit event logged
        with tenant_context(auth_mode="true"):
            db_session.expire_all()
            audit_ok = db_session.scalar(select(AuditLog).where(AuditLog.action == "enterprise.smtp_configured"))
            assert audit_ok is not None
            assert audit_ok.company_id == company_id

    # 5. Verify get_smtp_transport_details returns custom verified details
    with tenant_context(tenant_id=str(company_id)):
        transport_details_custom = get_smtp_transport_details(db_session, company_id)
    assert transport_details_custom["use_custom"] is True
    assert transport_details_custom["hostname"] == "smtp.mail.corporate.com"
    assert transport_details_custom["password"] == "super-secret-smtp-password"

    # 6. Test Rotation Triggers: Modifying any field (e.g. hostname) shifts status back to 'pending'
    resp_rotate = api_client.post(
        "/api/v1/enterprise/smtp",
        headers=headers,
        json={
            "hostname": "smtp.rotated-gateway.com",
            "port": 587,
            "username": "smtp_user",
            "password": "super-secret-smtp-password",
            "sender_email": "notifications@corporate.com"
        }
    )
    assert resp_rotate.status_code == 200
    assert resp_rotate.json()["verification_status"] == "pending"

    # 7. Test SMTP Handshake Failure (Mocked)
    with patch("api.enterprise.verify_smtp_credentials") as mock_handshake:
        # Mock failure
        mock_handshake.side_effect = ValueError("Authentication rejected by server")

        # Test route should raise 400 Bad Request
        resp_verify_fail = api_client.post("/api/v1/enterprise/smtp/test", headers=headers)
        assert resp_verify_fail.status_code == 400
        assert "SMTP handshake verification failed" in resp_verify_fail.json()["detail"]

        # Assert status is demoted to 'failed'
        with tenant_context(auth_mode="true"):
            db_session.expire_all()
            smtp_failed = db_session.scalar(select(CompanySMTPSettings).where(CompanySMTPSettings.company_id == company_id))
            assert smtp_failed.verification_status == "failed"
            assert "Authentication rejected by server" in smtp_failed.last_verification_error

            # Assert enterprise.smtp_test_failed audit event logged
            audit_fail = db_session.scalar(select(AuditLog).where(AuditLog.action == "enterprise.smtp_test_failed"))
            assert audit_fail is not None
            assert audit_fail.company_id == company_id

    # 8. Test 90-Day Periodic Expiry Sweeper
    # We set status back to 'verified', but make last_verified_at 95 days old in the database
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        smtp_old = db_session.scalar(select(CompanySMTPSettings).where(CompanySMTPSettings.company_id == company_id))
        smtp_old.verification_status = "verified"
        smtp_old.last_verified_at = datetime.now(timezone.utc) - timedelta(days=95)
        db_session.commit()

    # Verify transport returns global fallback since custom credentials have expired (>90 days)
    with tenant_context(tenant_id=str(company_id)):
        transport_expired = get_smtp_transport_details(db_session, company_id)
    assert transport_expired["use_custom"] is False

    # Execute the Celery sweeper task eagerly
    # Scenario 8a: Re-verification Handshake Succeeds
    with patch("tasks.smtp.verify_smtp_credentials") as mock_sweep_handshake:
        mock_sweep_handshake.return_value = None

        reverified_count = reverify_all_smtp_settings_task()
        assert reverified_count == 1

        # Assert status is renewed back to 'verified' with a fresh last_verified_at
        with tenant_context(auth_mode="true"):
            db_session.expire_all()
            smtp_renewed = db_session.scalar(select(CompanySMTPSettings).where(CompanySMTPSettings.company_id == company_id))
            assert smtp_renewed.verification_status == "verified"
            assert datetime.now(timezone.utc) - smtp_renewed.last_verified_at < timedelta(minutes=5)

            # Assert enterprise.smtp_reverified audit event logged
            audit_reverified = db_session.scalar(select(AuditLog).where(AuditLog.action == "enterprise.smtp_reverified"))
            assert audit_reverified is not None
            assert audit_reverified.company_id == company_id

    # Scenario 8b: Re-verification Handshake Fails (demotes back to failed)
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        smtp_old = db_session.scalar(select(CompanySMTPSettings).where(CompanySMTPSettings.company_id == company_id))
        smtp_old.verification_status = "verified"
        smtp_old.last_verified_at = datetime.now(timezone.utc) - timedelta(days=95)
        db_session.commit()

    with patch("tasks.smtp.verify_smtp_credentials") as mock_sweep_handshake:
        mock_sweep_handshake.side_effect = ValueError("Timeout connecting to server")

        reverified_count = reverify_all_smtp_settings_task()
        assert reverified_count == 1

        # Assert status is demoted to 'failed'
        with tenant_context(auth_mode="true"):
            db_session.expire_all()
            smtp_demoted = db_session.scalar(select(CompanySMTPSettings).where(CompanySMTPSettings.company_id == company_id))
            assert smtp_demoted.verification_status == "failed"
            assert "Timeout connecting to server" in smtp_demoted.last_verification_error

            # Assert enterprise.smtp_test_failed audit event logged for sweep failure
            audit_sweep_fail = db_session.scalars(
                select(AuditLog).where(AuditLog.action == "enterprise.smtp_test_failed")
            ).all()
            assert len(audit_sweep_fail) >= 2  # Includes previous test fail and fresh sweep fail
