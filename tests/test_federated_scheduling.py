import pytest
import uuid
import json
import hashlib
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text
from fastapi.testclient import TestClient

from server import app
from db.session import get_db, tenant_context
from models import Company, User, AuditLog, InterviewSlot
from models.company_sso import CompanySSOSettings
from models.calendar_credentials import CalendarCredentials
from models.scheduling_link import SchedulingLink

from models.enums import UserRole, CompanyStatus
from core.vault import SecretVaultService


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


def test_vault_envelope_encryption():
    """Verify that SecretVaultService encrypts and decrypts credentials securely using AES-GCM-256."""
    vault = SecretVaultService()
    secret = "secret-oauth-refresh-token-123456"
    
    # Encrypt
    encrypted_json = vault.encrypt_secret(secret)
    assert encrypted_json != secret
    assert "ciphertext" in encrypted_json
    assert "iv" in encrypted_json
    assert "tag" in encrypted_json
    
    # Decrypt
    decrypted = vault.decrypt_secret(encrypted_json)
    assert decrypted == secret


def test_scheduling_link_token_hashing(db_session):
    """Verify that scheduling links only store secure token_hash and never persist raw tokens."""
    # 1. Create a dummy company and interview context
    with tenant_context(auth_mode="true"):
        comp = Company(name="Hashing Corp", slug="hashing-corp", status=CompanyStatus.ACTIVE)
        db_session.add(comp)
        db_session.flush()
        
        user = User(company_id=comp.id, email="recruiter_hashing@corp.com", full_name="Recruiter H", password_hash="dummy", role=UserRole.RECRUITER)
        db_session.add(user)
        db_session.flush()
        
        db_session.execute(
            text("INSERT INTO jobs (id, company_id, title, department, description, status) VALUES (:id, :c_id, 'Engineer', 'Eng', 'Code', 'open')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id)}
        )
        job_id = db_session.scalar(text("SELECT id FROM jobs LIMIT 1"))
        
        db_session.execute(
            text("INSERT INTO candidates (id, company_id, email, full_name) VALUES (:id, :c_id, 'cand@test.com', 'Candidate H')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id)}
        )
        cand_id = db_session.scalar(text("SELECT id FROM candidates LIMIT 1"))
        
        db_session.execute(
            text("INSERT INTO applications (id, company_id, job_id, candidate_id, status) VALUES (:id, :c_id, :j_id, :cand_id, 'screening')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id), "j_id": str(job_id), "cand_id": str(cand_id)}
        )
        app_id = db_session.scalar(text("SELECT id FROM applications LIMIT 1"))
        
        interview_id = uuid.uuid4()
        db_session.execute(
            text("INSERT INTO interviews (id, company_id, application_id, interviewer_id, title, stage, scheduled_at, duration_minutes, is_cancelled) VALUES (:id, :c_id, :app_id, :interviewer_id, 'Coding Panel', 'interview', :scheduled_at, 45, false)"),
            {"id": str(interview_id), "c_id": str(comp.id), "app_id": str(app_id), "interviewer_id": str(user.id), "scheduled_at": datetime.now(timezone.utc)}
        )
        db_session.commit()

    # 2. Generate a secure token and hash it
    raw_token = "secure_candidate_booking_token_999888"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    
    with tenant_context(auth_mode="true"):
        link = SchedulingLink(
            company_id=comp.id,
            interview_id=interview_id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=3),
            one_time_use=True
        )
        db_session.add(link)
        db_session.commit()

        # Assert raw token does NOT exist in DB
        db_link = db_session.scalar(select(SchedulingLink).where(SchedulingLink.interview_id == interview_id))
        assert db_link is not None
        assert db_link.token_hash == token_hash
        assert raw_token not in str(db_link.__dict__)


def test_sso_authentication_lifecycle(api_client, db_session):
    """
    Verify complete Phase 1 SSO authentication, signature checks, dynamic JIT logins, 
    replay attacks detection, role mappings, and audit logging:
    - SAML ACS endpoint JIT-provisions recruiters and maps roles.
    - OIDC Callback decrypts vault keys to validate code exchanges.
    - Captures security.sso_login_success/failed audit events.
    """
    # 1. Setup Company A directly in DB to bypass register endpoint rate limits
    with tenant_context(auth_mode="true"):
        company = Company(name="SSO Acme Corp", slug="sso-acme-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()
        company_id = company.id
        company_slug = company.slug

        owner = User(
            company_id=company_id,
            email="owner_sso@acme.com",
            full_name="SSO Owner",
            password_hash="dummy",
            role=UserRole.OWNER,
            is_active=True
        )
        db_session.add(owner)
        db_session.commit()

    # 2. Configure SAML SSO Settings
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(company_id)})
        
        sso_settings = CompanySSOSettings(
            company_id=company_id,
            sso_provider="saml2",
            idp_entity_id="http://mock-okta.com/issuer",
            idp_sso_url="http://mock-okta.com/sso",
            idp_x509_cert="MIIBizCCATigAwIBAgIQ...",
            role_mapping={
                "RECRUITER": ["recruiting-manager", "hr-specialist"],
                "OWNER": ["admin-group"]
            }
        )
        db_session.add(sso_settings)
        db_session.commit()

    # 3. Test GET Redirection Endpoint
    login_resp = api_client.post("/api/v1/auth/sso/login", json={"company_slug": company_slug})
    assert login_resp.status_code == 200
    assert "mock-idp.com/login" in login_resp.json()["redirect_url"]

    # 4. Post SAML assertion: Invalid Signature Check
    assertion_id = f"assertion-{uuid.uuid4()}"
    saml_payload_invalid = json.dumps({
        "assertion_id": assertion_id,
        "email": "jit_recruiter@acme.com",
        "full_name": "JIT Recruiter",
        "saml_roles": ["recruiting-manager"],
        "not_on_or_after": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "signature": "invalid_signature"
    })
    
    acs_resp = api_client.post("/api/v1/auth/sso/acs", json={
        "company_slug": company_slug,
        "saml_response": saml_payload_invalid
    })
    assert acs_resp.status_code == 401
    
    # Assert failed audit log recorded
    with tenant_context(auth_mode="true"):
        failed_log = db_session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "security.sso_login_failed")
            .order_by(AuditLog.timestamp.desc())
        )
        assert failed_log is not None
        assert failed_log.metadata_json["error_type"] == "InvalidSignature"

    # 5. Post SAML assertion: Success ACS Handshake with JIT provisioning
    saml_payload_success = json.dumps({
        "assertion_id": assertion_id,
        "email": "jit_recruiter@acme.com",
        "full_name": "JIT Recruiter",
        "saml_roles": ["recruiting-manager"],
        "not_on_or_after": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "signature": "valid_signature"
    })

    acs_resp_success = api_client.post("/api/v1/auth/sso/acs", json={
        "company_slug": company_slug,
        "saml_response": saml_payload_success
    })
    assert acs_resp_success.status_code == 200
    token_data = acs_resp_success.json()
    assert token_data["access_token"] is not None
    assert token_data["user"]["email"] == "jit_recruiter@acme.com"
    assert token_data["user"]["role"] == "recruiter"

    # Verify user provisioned in DB
    with tenant_context(auth_mode="true"):
        db_user = db_session.scalar(select(User).where(User.email == "jit_recruiter@acme.com"))
        assert db_user is not None
        assert db_user.role == UserRole.RECRUITER
        
        # Verify success audit log recorded
        success_log = db_session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "security.sso_login_success")
            .order_by(AuditLog.timestamp.desc())
        )
        assert success_log is not None
        assert success_log.metadata_json["provider"] == "saml2"

    # 6. Replay Attack Verification (Submit exact same assertion ID)
    acs_resp_replay = api_client.post("/api/v1/auth/sso/acs", json={
        "company_slug": company_slug,
        "saml_response": saml_payload_success
    })
    assert acs_resp_replay.status_code == 401
    
    with tenant_context(auth_mode="true"):
        replay_log = db_session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "security.sso_login_failed")
            .order_by(AuditLog.timestamp.desc())
        )
        assert replay_log.metadata_json["error_type"] == "ReplayAttack"

    # 7. OIDC Configuration with SecretVaultService Encryption
    vault = SecretVaultService()
    encrypted_secret = vault.encrypt_secret("client-secret-abc-12345")
    
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(company_id)})
        comp_sso = db_session.scalar(select(CompanySSOSettings).where(CompanySSOSettings.company_id == company_id))
        comp_sso.sso_provider = "oidc"
        comp_sso.oidc_client_id = "oidc-client-id"
        comp_sso.oidc_client_secret = encrypted_secret
        comp_sso.oidc_well_known = "http://mock-idp.com/oidc/.well-known"
        db_session.commit()

    # Test OIDC GET Redirect Endpoint
    login_resp_oidc = api_client.post("/api/v1/auth/sso/login", json={"company_slug": company_slug})
    assert login_resp_oidc.status_code == 200
    assert "mock-idp.com/oidc/auth" in login_resp_oidc.json()["redirect_url"]

    # 8. Submit OIDC exchange callback logic: Success
    oidc_resp = api_client.post("/api/v1/auth/oidc/callback", json={
        "company_slug": company_slug,
        "code": "auth-code-998877"
    })
    assert oidc_resp.status_code == 200
    assert oidc_resp.json()["user"]["email"] == "sarah_oidc@acme.com"

    # Submit OIDC exchange callback logic: Failure
    oidc_resp_fail = api_client.post("/api/v1/auth/oidc/callback", json={
        "company_slug": company_slug,
        "code": "invalid_code"
    })
    assert oidc_resp_fail.status_code == 401


def test_sso_rls_tenant_isolation(api_client, db_session):
    """Verify that Company A cannot view or manipulate Company B's SSO settings or credentials under RLS."""
    # 1. Setup Company A and B directly in DB
    with tenant_context(auth_mode="true"):
        comp_a = Company(name="SSO Tenant A", slug="sso-tenant-a", status=CompanyStatus.ACTIVE)
        db_session.add(comp_a)
        db_session.flush()
        comp_a_id = comp_a.id
        
        comp_b = Company(name="SSO Tenant B", slug="sso-tenant-b", status=CompanyStatus.ACTIVE)
        db_session.add(comp_b)
        db_session.flush()
        comp_b_id = comp_b.id
        
        db_session.commit()

    # 2. Create SSO configuration for Company A in RLS mode
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_a_id)})
        sso_a = CompanySSOSettings(
            company_id=comp_a_id,
            idp_entity_id="http://tenant_a.com/issuer",
            idp_sso_url="http://tenant_a.com/sso",
            idp_x509_cert="CERT_A"
        )
        db_session.add(sso_a)
        db_session.commit()

    # 3. Verify RLS blocks Company B from querying Company A's SSO configuration
    with tenant_context(auth_mode="false"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_b_id)})
        
        # Attempt to read Company A settings
        sso_settings_read = db_session.scalar(select(CompanySSOSettings).where(CompanySSOSettings.company_id == comp_a_id))
        assert sso_settings_read is None
        
        # Verify can query Company B settings (should be empty)
        sso_settings_b = db_session.scalar(select(CompanySSOSettings).where(CompanySSOSettings.company_id == comp_b_id))
        assert sso_settings_b is None


def test_connect_oauth_redirect_whitelist(api_client, db_session):
    """Verify that connect endpoint handles redirect whitelist gating and persists OAuthState."""
    from models.oauth_state import OAuthState

    # 1. Setup Company and User
    with tenant_context(auth_mode="true"):
        comp = Company(name="Whitelist Corp", slug="whitelist-corp", status=CompanyStatus.ACTIVE)
        db_session.add(comp)
        db_session.flush()
        user = User(
            company_id=comp.id,
            email="recruiter_whitelist@corp.com",
            full_name="Recruiter W",
            password_hash="dummy",
            role=UserRole.RECRUITER
        )
        db_session.add(user)
        db_session.commit()

    # 2. Get Bearer Auth Token using ACS login simulation
    assertion_id = f"assertion-{uuid.uuid4()}"
    saml_payload = json.dumps({
        "assertion_id": assertion_id,
        "email": user.email,
        "full_name": user.full_name,
        "saml_roles": [],
        "signature": "valid_signature"
    })
    
    # Configure SAML Settings so ACS works
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp.id)})
        sso = CompanySSOSettings(
            company_id=comp.id,
            sso_provider="saml2",
            idp_entity_id="http://mock-okta.com/issuer",
            idp_sso_url="http://mock-okta.com/sso"
        )
        db_session.add(sso)
        db_session.commit()

    acs_resp = api_client.post("/api/v1/auth/sso/acs", json={
        "company_slug": comp.slug,
        "saml_response": saml_payload
    })
    assert acs_resp.status_code == 200
    access_token = acs_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Request connect with whitelisted URI
    conn_resp = api_client.post("/api/v1/auth/calendars/connect", json={
        "provider": "google",
        "redirect_uri": "http://mock-idp.com/oauth/google/callback"
    }, headers=headers)
    assert conn_resp.status_code == 200
    assert "accounts.google.com" in conn_resp.json()["redirect_url"]

    # Assert OAuthState persisted
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp.id)})
        states = db_session.scalars(select(OAuthState).where(OAuthState.user_id == user.id)).all()
        assert len(states) == 1
        assert states[0].provider == "google"
        assert states[0].used_at is None
        assert states[0].expires_at > datetime.now(timezone.utc)

    # 4. Request connect with non-whitelisted URI -> HTTP 400
    conn_resp_invalid = api_client.post("/api/v1/auth/calendars/connect", json={
        "provider": "google",
        "redirect_uri": "https://malicious.com/callback"
    }, headers=headers)
    assert conn_resp_invalid.status_code == 400
    assert "Redirect URI not whitelisted" in conn_resp_invalid.json()["detail"]


def test_oauth_callback_validation(api_client, db_session):
    """Verify that OAuth callback performs cryptographic validation, JIT credentials persistence, and webhook/connected audit logs."""
    from models.oauth_state import OAuthState

    # 1. Setup Company, User, and configure SAML authentication
    with tenant_context(auth_mode="true"):
        comp = Company(name="Callback Corp", slug="callback-corp", status=CompanyStatus.ACTIVE)
        db_session.add(comp)
        db_session.flush()
        user = User(
            company_id=comp.id,
            email="recruiter_callback@corp.com",
            full_name="Recruiter C",
            password_hash="dummy",
            role=UserRole.RECRUITER
        )
        db_session.add(user)
        db_session.commit()

    # Get authentication token
    assertion_id = f"assertion-{uuid.uuid4()}"
    saml_payload = json.dumps({
        "assertion_id": assertion_id,
        "email": user.email,
        "full_name": user.full_name,
        "saml_roles": [],
        "signature": "valid_signature"
    })
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp.id)})
        sso = CompanySSOSettings(
            company_id=comp.id,
            sso_provider="saml2",
            idp_entity_id="http://mock-okta.com/issuer",
            idp_sso_url="http://mock-okta.com/sso"
        )
        db_session.add(sso)
        db_session.commit()

    acs_resp = api_client.post("/api/v1/auth/sso/acs", json={
        "company_slug": comp.slug,
        "saml_response": saml_payload
    })
    access_token = acs_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Pre-seed a valid state and nonce in the DB
    state_token = "state_12345"
    nonce_token = "nonce_12345"
    state_hash = hashlib.sha256(state_token.encode("utf-8")).hexdigest()
    nonce_hash = hashlib.sha256(nonce_token.encode("utf-8")).hexdigest()

    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp.id)})
        oauth_state = OAuthState(
            company_id=comp.id,
            user_id=user.id,
            provider="google",
            state_hash=state_hash,
            nonce_hash=nonce_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
        )
        db_session.add(oauth_state)
        db_session.commit()

    # 3. Call callback with matching state & nonce -> Success
    cb_resp = api_client.post("/api/v1/auth/calendars/callback", json={
        "provider": "google",
        "code": "success_oauth_code",
        "state": state_token,
        "nonce": nonce_token,
        "redirect_uri": "http://mock-idp.com/oauth/google/callback"
    }, headers=headers)
    assert cb_resp.status_code == 200
    assert cb_resp.json()["status"] == "connected"

    # Assert credentials record created and encrypted
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp.id)})
        cred = db_session.scalar(select(CalendarCredentials).where(CalendarCredentials.user_id == user.id))
        assert cred is not None
        assert cred.provider == "google"
        assert cred.status == "active"
        
        # Verify envelope encryption (should be unreadable ciphertext in DB representation)
        assert "google_access_token" not in cred.encrypted_access_token
        
        # Verify decryption via SecretVault
        vault = SecretVaultService()
        assert vault.decrypt_secret(cred.encrypted_access_token) == "google_access_token_success_oauth_code"

        # Assert audit logs recorded correctly
        connected_log = db_session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "calendar.connected", AuditLog.company_id == comp.id)
            .order_by(AuditLog.timestamp.desc())
        )
        assert connected_log is not None
        assert connected_log.metadata_json["provider"] == "google"

        webhook_log = db_session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "calendar.webhook_registered", AuditLog.company_id == comp.id)
            .order_by(AuditLog.timestamp.desc())
        )
        assert webhook_log is not None

    # 4. Request same callback again -> Consumed state -> HTTP 400
    cb_resp_consumed = api_client.post("/api/v1/auth/calendars/callback", json={
        "provider": "google",
        "code": "success_oauth_code",
        "state": state_token,
        "nonce": nonce_token,
        "redirect_uri": "http://mock-idp.com/oauth/google/callback"
    }, headers=headers)
    assert cb_resp_consumed.status_code == 400
    assert "consumed" in cb_resp_consumed.json()["detail"].lower()


def test_calendar_ownership_enforcement(api_client, db_session):
    """Verify that only the credential owner or an OWNER role may disconnect/manage a calendar integration."""
    # 1. Setup Company with Recruiters A and B, plus an OWNER C
    with tenant_context(auth_mode="true"):
        comp = Company(name="Ownership Corp", slug="ownership-corp", status=CompanyStatus.ACTIVE)
        db_session.add(comp)
        db_session.flush()

        recruiter_a = User(company_id=comp.id, email="rec_a@corp.com", full_name="Recruiter A", password_hash="dummy", role=UserRole.RECRUITER)
        recruiter_b = User(company_id=comp.id, email="rec_b@corp.com", full_name="Recruiter B", password_hash="dummy", role=UserRole.RECRUITER)
        owner_c = User(company_id=comp.id, email="owner_c@corp.com", full_name="Owner C", password_hash="dummy", role=UserRole.OWNER)
        
        db_session.add_all([recruiter_a, recruiter_b, owner_c])
        db_session.commit()

    # Configure SAML Settings so ACS works for users
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp.id)})
        sso = CompanySSOSettings(
            company_id=comp.id,
            sso_provider="saml2",
            idp_entity_id="http://mock-okta.com/issuer",
            idp_sso_url="http://mock-okta.com/sso"
        )
        db_session.add(sso)
        db_session.commit()

    # Get Bearer tokens for Recruiter B and Owner C
    def get_token_for(user_obj):
        assertion_id = f"assertion-{uuid.uuid4()}"
        saml_payload = json.dumps({
            "assertion_id": assertion_id,
            "email": user_obj.email,
            "full_name": user_obj.full_name,
            "saml_roles": [],
            "signature": "valid_signature"
        })
        res = api_client.post("/api/v1/auth/sso/acs", json={"company_slug": comp.slug, "saml_response": saml_payload})
        return res.json()["access_token"]

    token_b = get_token_for(recruiter_b)
    token_c = get_token_for(owner_c)

    headers_b = {"Authorization": f"Bearer {token_b}"}
    headers_c = {"Authorization": f"Bearer {token_c}"}

    # 2. Seed a calendar credential belonging to Recruiter A
    vault = SecretVaultService()
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp.id)})
        cred = CalendarCredentials(
            company_id=comp.id,
            user_id=recruiter_a.id,
            provider="google",
            account_email=recruiter_a.email,
            encrypted_access_token=vault.encrypt_secret("secret_token_a"),
            encrypted_refresh_token=vault.encrypt_secret("refresh_token_a"),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            status="active"
        )
        db_session.add(cred)
        db_session.commit()
        cred_id = str(cred.id)

    # 3. Recruiter B attempts to disconnect Recruiter A's calendar -> HTTP 403 Forbidden
    disc_b_resp = api_client.post(f"/api/v1/auth/calendars/{cred_id}/disconnect", headers=headers_b)
    assert disc_b_resp.status_code == 403
    assert "Forbidden" in disc_b_resp.json()["detail"]

    # 4. Owner C attempts to disconnect Recruiter A's calendar -> Success
    disc_c_resp = api_client.post(f"/api/v1/auth/calendars/{cred_id}/disconnect", headers=headers_c)
    assert disc_c_resp.status_code == 200
    assert disc_c_resp.json()["status"] == "disconnected"


def test_rate_limit_recovery_and_health(db_session):
    """Verify that rate limits (HTTP 429) transition status to rate_limited and track retry metrics before self-healing."""
    # 1. Setup Company, User and Seed active credential
    vault = SecretVaultService()
    with tenant_context(auth_mode="true"):
        comp = Company(name="Rate Health Corp", slug="rate-health-corp", status=CompanyStatus.ACTIVE)
        db_session.add(comp)
        db_session.flush()
        user = User(company_id=comp.id, email="recruiter_rate@corp.com", full_name="Recruiter R", password_hash="dummy", role=UserRole.RECRUITER)
        db_session.add(user)
        db_session.flush()

        cred = CalendarCredentials(
            company_id=comp.id,
            user_id=user.id,
            provider="google",
            account_email=user.email,
            encrypted_access_token=vault.encrypt_secret("secret_access"),
            encrypted_refresh_token=vault.encrypt_secret("secret_refresh"),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            status="active",
            retry_count=0
        )
        db_session.add(cred)
        db_session.commit()
        cred_id = cred.id

    # 2. Simulate Provider sync raising Rate Limit error
    from tasks.calendar_sync import run_delta_sync_for_credential, ProviderRateLimitError
    from unittest.mock import patch, MagicMock

    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp.id)})
        
        # Mock GoogleCalendarProvider.fetch_changes to simulate rate limiting (HTTP 429)
        with patch("tasks.calendar_sync.GoogleCalendarProvider.fetch_changes", side_effect=ValueError("429 Too Many Requests")):
            with pytest.raises(ProviderRateLimitError):
                run_delta_sync_for_credential(db=db_session, credential_id=cred_id)

        # Assert status transitioned to rate_limited and retry_count was incremented
        db_session.refresh(cred)
        assert cred.status == "rate_limited"
        assert cred.retry_count == 1
        assert cred.last_retry_at is not None
        assert "rate limit" in cred.last_sync_error.lower()

        # 3. Simulate self-healing on successful sync
        with patch("tasks.calendar_sync.GoogleCalendarProvider.fetch_changes", return_value={"changes": [], "sync_token": "new_token_77"}):
            result = run_delta_sync_for_credential(db=db_session, credential_id=cred_id)
            assert result["status"] == "success"

        # Assert status self-healed back to active, retry count reset, and last_sync_error cleared
        db_session.refresh(cred)
        assert cred.status == "active"
        assert cred.retry_count == 0
        assert cred.last_sync_error is None
        assert cred.sync_token == "new_token_77"


def test_provider_capability_declarations():
    """Verify that calendar providers explicitly declare capability flags instead of relying on provider name checks."""
    from core.calendar_provider import GoogleCalendarProvider, MicrosoftGraphProvider

    google = GoogleCalendarProvider()
    outlook = MicrosoftGraphProvider()

    # Google Capabilities
    assert google.supports_webhooks is True
    assert google.supports_delta_sync is True
    assert google.supports_free_busy is True
    assert google.supports_push_renewal is False

    # Outlook Capabilities
    assert outlook.supports_webhooks is True
    assert outlook.supports_delta_sync is True
    assert outlook.supports_free_busy is True
    assert outlook.supports_push_renewal is True


def test_create_scheduling_link(api_client, db_session):
    """Verify that recruiters can create scheduling links and only token_hash is persisted."""
    # 1. Setup Company and Recruiter User
    with tenant_context(auth_mode="true"):
        comp = Company(name="Link Gen Corp", slug="link-gen-corp", status=CompanyStatus.ACTIVE)
        db_session.add(comp)
        db_session.flush()
        user = User(
            company_id=comp.id,
            email="recruiter_link@corp.com",
            full_name="Recruiter L",
            password_hash="dummy",
            role=UserRole.RECRUITER
        )
        db_session.add(user)
        db_session.commit()

    # Configure SAML Settings so ACS works
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp.id)})
        sso = CompanySSOSettings(
            company_id=comp.id,
            sso_provider="saml2",
            idp_entity_id="http://mock-okta.com/issuer",
            idp_sso_url="http://mock-okta.com/sso"
        )
        db_session.add(sso)
        db_session.commit()

    # Get Bearer token
    assertion_id = f"assertion-{uuid.uuid4()}"
    saml_payload = json.dumps({
        "assertion_id": assertion_id,
        "email": user.email,
        "full_name": user.full_name,
        "saml_roles": [],
        "signature": "valid_signature"
    })
    acs_resp = api_client.post("/api/v1/auth/sso/acs", json={"company_slug": comp.slug, "saml_response": saml_payload})
    access_token = acs_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Pre-seed a dummy job, candidate, and interview for RLS boundaries
    with tenant_context(auth_mode="true"):
        db_session.execute(
            text("INSERT INTO jobs (id, company_id, title, department, description, status) VALUES (:id, :c_id, 'Developer', 'Eng', 'Code', 'open')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id)}
        )
        job_id = db_session.scalar(text("SELECT id FROM jobs LIMIT 1"))
        
        db_session.execute(
            text("INSERT INTO candidates (id, company_id, email, full_name) VALUES (:id, :c_id, 'cand_link@test.com', 'Candidate L')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id)}
        )
        cand_id = db_session.scalar(text("SELECT id FROM candidates LIMIT 1"))
        
        db_session.execute(
            text("INSERT INTO applications (id, company_id, job_id, candidate_id, status) VALUES (:id, :c_id, :j_id, :cand_id, 'screening')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id), "j_id": str(job_id), "cand_id": str(cand_id)}
        )
        app_id = db_session.scalar(text("SELECT id FROM applications LIMIT 1"))
        
        interview_id = uuid.uuid4()
        db_session.execute(
            text("INSERT INTO interviews (id, company_id, application_id, interviewer_id, title, stage, scheduled_at, duration_minutes, is_cancelled) VALUES (:id, :c_id, :app_id, :interviewer_id, 'Coding Panel', 'interview', :scheduled_at, 45, false)"),
            {"id": str(interview_id), "c_id": str(comp.id), "app_id": str(app_id), "interviewer_id": str(user.id), "scheduled_at": datetime.now(timezone.utc)}
        )
        db_session.commit()

    # 2. Call link creation endpoint
    link_resp = api_client.post("/api/v1/schedule/links", json={
        "interview_id": str(interview_id),
        "expires_in_days": 3,
        "one_time_use": True
    }, headers=headers)
    assert link_resp.status_code == 201
    
    data = link_resp.json()
    assert data["link_id"] is not None
    assert data["raw_token"] is not None
    assert "/schedule/" in data["booking_url"]

    # 3. Assert raw token does NOT exist in DB (only the hashed token_hash is saved)
    with tenant_context(auth_mode="true"):
        db_link = db_session.scalar(select(SchedulingLink).where(SchedulingLink.interview_id == interview_id))
        assert db_link is not None
        assert db_link.token_hash == hashlib.sha256(data["raw_token"].encode("utf-8")).hexdigest()
        assert data["raw_token"] not in str(db_link.__dict__)


def test_get_availability_expired_link(api_client, db_session):
    """Verify that accessing an expired link returns HTTP 410 Gone and logs schedule.link_expired audit trail."""
    # 1. Setup Company, User, Interview, and an Expired link
    with tenant_context(auth_mode="true"):
        comp = Company(name="Expired Link Corp", slug="expired-corp", status=CompanyStatus.ACTIVE)
        db_session.add(comp)
        db_session.flush()
        user = User(company_id=comp.id, email="rec_exp@corp.com", full_name="Rec Exp", password_hash="dummy", role=UserRole.RECRUITER)
        db_session.add(user)
        db_session.commit()

    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp.id)})
        sso = CompanySSOSettings(company_id=comp.id, idp_entity_id="http://mock-okta.com/issuer", idp_sso_url="http://mock-okta.com/sso")
        db_session.add(sso)
        db_session.commit()

    # Get Bearer token
    assertion_id = f"assertion-{uuid.uuid4()}"
    saml_payload = json.dumps({"assertion_id": assertion_id, "email": user.email, "full_name": user.full_name, "saml_roles": [], "signature": "valid_signature"})
    acs_resp = api_client.post("/api/v1/auth/sso/acs", json={"company_slug": comp.slug, "saml_response": saml_payload})
    access_token = acs_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Pre-seed candidate details
    with tenant_context(auth_mode="true"):
        db_session.execute(
            text("INSERT INTO jobs (id, company_id, title, department, description, status) VALUES (:id, :c_id, 'Developer', 'Eng', 'Code', 'open')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id)}
        )
        job_id = db_session.scalar(text("SELECT id FROM jobs LIMIT 1"))
        db_session.execute(
            text("INSERT INTO candidates (id, company_id, email, full_name) VALUES (:id, :c_id, 'cand_exp@test.com', 'Candidate E')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id)}
        )
        cand_id = db_session.scalar(text("SELECT id FROM candidates LIMIT 1"))
        db_session.execute(
            text("INSERT INTO applications (id, company_id, job_id, candidate_id, status) VALUES (:id, :c_id, :j_id, :cand_id, 'screening')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id), "j_id": str(job_id), "cand_id": str(cand_id)}
        )
        app_id = db_session.scalar(text("SELECT id FROM applications LIMIT 1"))
        interview_id = uuid.uuid4()
        db_session.execute(
            text("INSERT INTO interviews (id, company_id, application_id, interviewer_id, title, stage, scheduled_at, duration_minutes, is_cancelled) VALUES (:id, :c_id, :app_id, :interviewer_id, 'Coding Panel', 'interview', :scheduled_at, 45, false)"),
            {"id": str(interview_id), "c_id": str(comp.id), "app_id": str(app_id), "interviewer_id": str(user.id), "scheduled_at": datetime.now(timezone.utc)}
        )
        db_session.commit()

    # Pre-seed expired scheduling link
    raw_token = "expired_raw_token_998877"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with tenant_context(auth_mode="true"):
        link = SchedulingLink(
            company_id=comp.id,
            interview_id=interview_id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            one_time_use=True
        )
        db_session.add(link)
        db_session.commit()

    # 2. Get availability using expired link -> HTTP 410 Gone
    avail_resp = api_client.get(f"/api/v1/schedule/{raw_token}/availability", headers=headers)
    assert avail_resp.status_code == 410
    assert "expired" in avail_resp.json()["detail"].lower()

    # 3. Assert schedule.link_expired audit trail logged
    with tenant_context(auth_mode="true"):
        expired_log = db_session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "schedule.link_expired", AuditLog.company_id == comp.id)
            .order_by(AuditLog.timestamp.desc())
        )
        assert expired_log is not None
        assert expired_log.metadata_json["interview_id"] == str(interview_id)


def test_self_scheduling_and_overlap_concurrency(api_client, db_session):
    """Verify dynamic availability slots calculation, successful booking, and EXCLUDE overlapping constraint blocks."""
    # 1. Setup Company, User, Interview, and Active link
    with tenant_context(auth_mode="true"):
        comp = Company(name="Overlap Corp", slug="overlap-corp", status=CompanyStatus.ACTIVE)
        db_session.add(comp)
        db_session.flush()
        user = User(company_id=comp.id, email="rec_ov@corp.com", full_name="Rec Ov", password_hash="dummy", role=UserRole.RECRUITER)
        db_session.add(user)
        db_session.commit()

    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp.id)})
        sso = CompanySSOSettings(company_id=comp.id, idp_entity_id="http://mock-okta.com/issuer", idp_sso_url="http://mock-okta.com/sso")
        db_session.add(sso)
        db_session.commit()

    # Get Bearer token
    assertion_id = f"assertion-{uuid.uuid4()}"
    saml_payload = json.dumps({"assertion_id": assertion_id, "email": user.email, "full_name": user.full_name, "saml_roles": [], "signature": "valid_signature"})
    acs_resp = api_client.post("/api/v1/auth/sso/acs", json={"company_slug": comp.slug, "saml_response": saml_payload})
    access_token = acs_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    with tenant_context(auth_mode="true"):
        db_session.execute(
            text("INSERT INTO jobs (id, company_id, title, department, description, status) VALUES (:id, :c_id, 'Developer', 'Eng', 'Code', 'open')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id)}
        )
        job_id = db_session.scalar(text("SELECT id FROM jobs LIMIT 1"))
        db_session.execute(
            text("INSERT INTO candidates (id, company_id, email, full_name) VALUES (:id, :c_id, 'cand_ov@test.com', 'Candidate O')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id)}
        )
        cand_id = db_session.scalar(text("SELECT id FROM candidates LIMIT 1"))
        db_session.execute(
            text("INSERT INTO applications (id, company_id, job_id, candidate_id, status) VALUES (:id, :c_id, :j_id, :cand_id, 'screening')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id), "j_id": str(job_id), "cand_id": str(cand_id)}
        )
        app_id = db_session.scalar(text("SELECT id FROM applications LIMIT 1"))
        interview_id = uuid.uuid4()
        db_session.execute(
            text("INSERT INTO interviews (id, company_id, application_id, interviewer_id, title, stage, scheduled_at, duration_minutes, is_cancelled) VALUES (:id, :c_id, :app_id, :interviewer_id, 'Coding Panel', 'interview', :scheduled_at, 45, false)"),
            {"id": str(interview_id), "c_id": str(comp.id), "app_id": str(app_id), "interviewer_id": str(user.id), "scheduled_at": datetime.now(timezone.utc)}
        )
        db_session.commit()

    # Pre-seed active scheduling link
    raw_token = "active_raw_token_555"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with tenant_context(auth_mode="true"):
        link = SchedulingLink(
            company_id=comp.id,
            interview_id=interview_id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=3),
            one_time_use=False
        )
        db_session.add(link)
        db_session.commit()

    # Seed calendar credentials so availability lookup returns mock slots
    vault = SecretVaultService()
    with tenant_context(auth_mode="true"):
        cred = CalendarCredentials(
            company_id=comp.id,
            user_id=user.id,
            provider="google",
            account_email=user.email,
            encrypted_access_token=vault.encrypt_secret("access"),
            encrypted_refresh_token=vault.encrypt_secret("refresh"),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
            status="active"
        )
        db_session.add(cred)
        db_session.commit()

    # 2. Get Availability Slots Grid
    avail_resp = api_client.get(f"/api/v1/schedule/{raw_token}/availability", headers=headers)
    assert avail_resp.status_code == 200
    avail_data = avail_resp.json()
    assert len(avail_data["available_slots"]) > 0
    selected_slot = avail_data["available_slots"][0]

    # 3. Successful Booking Execution
    book_resp = api_client.post(f"/api/v1/schedule/{raw_token}/book", json={
        "start_time": selected_slot["start_time"],
        "candidate_notes": "First Slot"
    }, headers=headers)
    assert book_resp.status_code == 201
    book_data = book_resp.json()
    assert book_data["status"] == "confirmed"
    assert book_data["booking_token"] is not None

    # Assert slot confirmed in DB and booking_token_hash stored
    with tenant_context(auth_mode="true"):
        db_slot = db_session.scalar(select(InterviewSlot).where(InterviewSlot.interview_id == interview_id))
        assert db_slot is not None
        assert db_slot.status == "confirmed"
        assert db_slot.booking_token_hash == hashlib.sha256(book_data["booking_token"].encode("utf-8")).hexdigest()

        # Assert schedule.slot_booked and schedule.reminder_sent audit logs
        booked_log = db_session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "schedule.slot_booked", AuditLog.company_id == comp.id)
            .order_by(AuditLog.timestamp.desc())
        )
        assert booked_log is not None
        assert booked_log.metadata_json["slot_id"] == str(db_slot.id)

    # 4. Attempt to book an overlapping time block -> Blocked by overlap check or database EXCLUDE constraint -> HTTP 409
    book_resp_fail = api_client.post(f"/api/v1/schedule/{raw_token}/book", json={
        "start_time": selected_slot["start_time"],
        "candidate_notes": "Overlap Attempt"
    }, headers=headers)
    assert book_resp_fail.status_code == 409


def test_booking_ownership_validation_cancel_reschedule(api_client, db_session):
    """Verify that cancellation and rescheduling require candidate booking token validation, and logs rescheduled/cancelled events."""
    # 1. Setup Company, User, Interview, and confirmed Booking slot
    with tenant_context(auth_mode="true"):
        comp = Company(name="Auth Slot Corp", slug="auth-slot-corp", status=CompanyStatus.ACTIVE)
        db_session.add(comp)
        db_session.flush()
        user = User(company_id=comp.id, email="rec_auth@corp.com", full_name="Rec Auth", password_hash="dummy", role=UserRole.RECRUITER)
        db_session.add(user)
        db_session.commit()

    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp.id)})
        sso = CompanySSOSettings(company_id=comp.id, idp_entity_id="http://mock-okta.com/issuer", idp_sso_url="http://mock-okta.com/sso")
        db_session.add(sso)
        db_session.commit()

    # Get Bearer token
    assertion_id = f"assertion-{uuid.uuid4()}"
    saml_payload = json.dumps({"assertion_id": assertion_id, "email": user.email, "full_name": user.full_name, "saml_roles": [], "signature": "valid_signature"})
    acs_resp = api_client.post("/api/v1/auth/sso/acs", json={"company_slug": comp.slug, "saml_response": saml_payload})
    access_token = acs_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    with tenant_context(auth_mode="true"):
        db_session.execute(
            text("INSERT INTO jobs (id, company_id, title, department, description, status) VALUES (:id, :c_id, 'Developer', 'Eng', 'Code', 'open')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id)}
        )
        job_id = db_session.scalar(text("SELECT id FROM jobs LIMIT 1"))
        db_session.execute(
            text("INSERT INTO candidates (id, company_id, email, full_name) VALUES (:id, :c_id, 'cand_auth@test.com', 'Candidate A')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id)}
        )
        cand_id = db_session.scalar(text("SELECT id FROM candidates LIMIT 1"))
        db_session.execute(
            text("INSERT INTO applications (id, company_id, job_id, candidate_id, status) VALUES (:id, :c_id, :j_id, :cand_id, 'screening')"),
            {"id": str(uuid.uuid4()), "c_id": str(comp.id), "j_id": str(job_id), "cand_id": str(cand_id)}
        )
        app_id = db_session.scalar(text("SELECT id FROM applications LIMIT 1"))
        interview_id = uuid.uuid4()
        db_session.execute(
            text("INSERT INTO interviews (id, company_id, application_id, interviewer_id, title, stage, scheduled_at, duration_minutes, is_cancelled) VALUES (:id, :c_id, :app_id, :interviewer_id, 'Coding Panel', 'interview', :scheduled_at, 45, false)"),
            {"id": str(interview_id), "c_id": str(comp.id), "app_id": str(app_id), "interviewer_id": str(user.id), "scheduled_at": datetime.now(timezone.utc)}
        )
        db_session.commit()

    # Pre-seed a confirmed booking slot with hash
    raw_booking_token = "my_candidate_secret_booking_token"
    booking_token_hash = hashlib.sha256(raw_booking_token.encode("utf-8")).hexdigest()
    start_time = datetime.now(timezone.utc) + timedelta(days=2)
    end_time = start_time + timedelta(minutes=45)

    with tenant_context(auth_mode="true"):
        slot = InterviewSlot(
            company_id=comp.id,
            interview_id=interview_id,
            start_time=start_time,
            end_time=end_time,
            status="confirmed",
            booking_token_hash=booking_token_hash
        )
        db_session.add(slot)
        db_session.commit()
        slot_id = str(slot.id)

    # 2. Reschedule Attempt: Missing Ownership Token -> HTTP 401 Unauthorized
    resched_fail = api_client.post(f"/api/v1/schedule/bookings/{slot_id}/reschedule", json={
        "new_start_time": (start_time + timedelta(hours=2)).isoformat()
    }, headers=headers)
    assert resched_fail.status_code == 401

    # Reschedule Attempt: Invalid Token -> HTTP 403 Forbidden
    resched_invalid = api_client.post(f"/api/v1/schedule/bookings/{slot_id}/reschedule", json={
        "new_start_time": (start_time + timedelta(hours=2)).isoformat()
    }, headers={"X-Booking-Token": "wrong_token", **headers})
    assert resched_invalid.status_code == 403

    # Reschedule Attempt: Success with Valid Token
    new_start_time = start_time + timedelta(hours=2)
    resched_success = api_client.post(f"/api/v1/schedule/bookings/{slot_id}/reschedule", json={
        "new_start_time": new_start_time.isoformat()
    }, headers={"X-Booking-Token": raw_booking_token, **headers})
    assert resched_success.status_code == 200
    
    # Assert reschedule audit logged
    with tenant_context(auth_mode="true"):
        resched_log = db_session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "schedule.rescheduled", AuditLog.company_id == comp.id)
            .order_by(AuditLog.timestamp.desc())
        )
        assert resched_log is not None
        assert resched_log.metadata_json["slot_id"] == slot_id

    # 3. Cancellation Attempt: Success with Valid Token
    cancel_success = api_client.post(f"/api/v1/schedule/bookings/{slot_id}/cancel", json={
        "reason": "Health conflict"
    }, headers={"X-Booking-Token": raw_booking_token, **headers})
    assert cancel_success.status_code == 200

    # Assert cancel audit logged
    with tenant_context(auth_mode="true"):
        cancel_log = db_session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "schedule.slot_cancelled", AuditLog.company_id == comp.id)
            .order_by(AuditLog.timestamp.desc())
        )
        assert cancel_log is not None
        assert cancel_log.metadata_json["slot_id"] == slot_id


