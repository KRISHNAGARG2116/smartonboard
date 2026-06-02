import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import select

from server import app
from db.session import get_db, tenant_context
from models.quarantine import QuarantinedFile


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


def test_content_security_policy_headers(api_client):
    """Verify that strict CSP, XSS, and frame blocking headers are present on all responses."""
    response = api_client.get("/api/health")
    assert response.status_code == 200
    assert "Content-Security-Policy" in response.headers
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_html_input_sanitization_xss(api_client):
    """Verify that incoming JSON body requests automatically sanitize HTML tags via bleach."""
    # Register request payload containing XSS injection payload
    malicious_payload = {
        "company_name": "Injected Corp <script>alert('xss')</script>",
        "email": "xss@corp.com",
        "password": "super-secure-password-123",
        "full_name": "<img src=x onerror=alert('xss')> John XSS"
    }
    
    # We patch register inside DB session to inspect what is written
    with patch("api.auth.create_user_session_and_tokens") as mock_tokens, \
         patch("core.audit.log_audit_event") as mock_audit:
        mock_tokens.return_value = ("access", "refresh")
        
        response = api_client.post("/api/v1/auth/register", json=malicious_payload)
        print("RCA_TEST_RESP:", response.status_code, response.text)
        assert response.status_code == 201
        
        # Verify JSON response and database/mock arguments contain stripped strings
        res_data = response.json()
        print("RCA_TEST_DATA:", json.dumps(res_data, indent=2))
        assert "<script>" not in res_data["user"]["full_name"]
        assert "onerror" not in res_data["user"]["full_name"]
        # The bleach clean strips HTML elements, leaving clean plain text
        assert "John XSS" in res_data["user"]["full_name"]


def test_account_takeover_ip_lockout(api_client):
    """Verify that 5 failed login attempts in 5 minutes blocks the IP address with a 429."""
    from api.auth import record_failed_login, is_ip_blocked, clear_failed_logins
    
    ip = "192.168.1.99"
    clear_failed_logins(ip)
    assert not is_ip_blocked(ip)
    
    # Simulate 5 failed logins
    for _ in range(5):
        record_failed_login(ip)
        
    assert is_ip_blocked(ip)
    
    # Verify login attempt from blocked IP gets 429
    payload = {"email": "test@corp.com", "password": "wrong-password"}
    with patch("fastapi.Request.client", new_callable=MagicMock) as mock_client:
        mock_client.host = ip
        response = api_client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 429
        assert "temporarily locked out" in response.json()["detail"]
        
    # Reset lockout
    clear_failed_logins(ip)
    assert not is_ip_blocked(ip)


def test_otp_verification_throttle_and_lockout(api_client):
    """Verify OTP limit verify triggers (1/min) and 3-strike verification lockout."""
    import redis
    from core.config import get_settings
    
    phone = "+15550199"
    settings = get_settings()
    r = redis.from_url(settings.redis_url)
    
    # Clear keys first
    r.delete(f"otp:code:{phone}")
    r.delete(f"otp:rate:{phone}")
    
    # First OTP request is successful
    response1 = api_client.post("/api/v1/auth/otp/send", json={"phone_number": phone})
    assert response1.status_code == 200
    assert response1.json()["success"] is True
    
    # Immediate second OTP request triggers 429 throttle lockout (1/minute limit)
    response2 = api_client.post("/api/v1/auth/otp/send", json={"phone_number": phone})
    assert response2.status_code == 429
    assert "wait 1 minute" in response2.json()["detail"]
    
    # Check 3-strike verify attempts limit lockout
    # Stored key format is "code:attempts"
    r.setex(f"otp:code:{phone}", 300, "123456:0")
    
    # Try invalid code 3 times
    for i in range(3):
        verify_resp = api_client.post("/api/v1/auth/otp/verify", json={"phone_number": phone, "code": "000000"})
        if i < 2:
            assert verify_resp.status_code == 400
            assert "Invalid verification code" in verify_resp.json()["detail"]
        else:
            # 3rd failed attempt deletes key and throws lockout 403
            assert verify_resp.status_code == 403
            assert "Too many failed attempts" in verify_resp.json()["detail"]
            
    # Stored OTP is deleted in Redis
    assert not r.exists(f"otp:code:{phone}")


def test_quarantined_files_db_logging(api_client, db_session):
    """Verify that uploading files to async endpoints correctly creates a record in quarantined_files table."""
    valid_pdf_data = b"%PDF-1.4\n%%EOF"
    files = {"file": ("resume.pdf", valid_pdf_data, "application/pdf")}
    data = {"job_role": "Rust Engineer"}

    with patch("celery_worker.scan_and_promote_resume_task.delay") as mock_celery_task:
        mock_task_instance = MagicMock()
        mock_task_instance.id = "mocked-celery-id-999"
        mock_celery_task.return_value = mock_task_instance
        
        response = api_client.post("/api/screen/upload", files=files, data=data)
        assert response.status_code == 202
        q_file_id = response.json()["quarantine_file_id"]
        
        # Verify database record
        with tenant_context(auth_mode="true"):
            q_rec = db_session.get(QuarantinedFile, q_file_id)
            assert q_rec is not None
            assert q_rec.filename == "resume.pdf"
            assert q_rec.is_safe is None  # Initially Pending
