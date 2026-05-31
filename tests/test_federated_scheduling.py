import pytest
import uuid
import json
import hashlib
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text
from fastapi.testclient import TestClient

from server import app
from db.session import get_db, tenant_context
from models import Company, User, AuditLog
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
