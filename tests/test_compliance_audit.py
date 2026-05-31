import pytest
import uuid
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError, InternalError
from fastapi.testclient import TestClient
from server import app
from db.session import get_db, tenant_context
from models import User, Company
from models.enums import UserRole
from models.audit import AuditLog
from core.audit import log_audit_event, sanitize_metadata

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


def test_audit_log_immutability(db_session):
    """Verify database-level triggers block UPDATE and DELETE on audit_logs table."""
    # 1. Create a dummy company and user to associate with
    with tenant_context(auth_mode="true"):
        company = Company(name="Immutability Corp", slug="immutability-corp")
        db_session.add(company)
        db_session.commit()
        db_session.refresh(company)

        user = User(
            email="audit_immutability@test.com",
            full_name="Immutability Audit",
            password_hash="dummy",
            role=UserRole.RECRUITER,
            company_id=company.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    # 2. Write an audit log entry
    log = log_audit_event(
        db=db_session,
        action="test.immutability",
        actor_type="RECRUITER",
        actor_id=user.id,
        company_id=company.id,
        metadata={"info": "this should not change"}
    )
    
    # 3. Attempt to UPDATE the record under normal context (without bypass)
    # The DB trigger check_audit_log_immutability should block this!
    with pytest.raises((ProgrammingError, InternalError)) as exc_info:
        with tenant_context(auth_mode="true"):
            log.action = "tampered.action"
            db_session.add(log)
            db_session.commit()
    assert "immutable append-only records" in str(exc_info.value).lower()
    
    db_session.rollback()

    # 4. Attempt to DELETE the record under normal context
    # The DB trigger should block this!
    with pytest.raises((ProgrammingError, InternalError)) as exc_info:
        with tenant_context(auth_mode="true"):
            db_session.delete(log)
            db_session.commit()
    assert "immutable append-only records" in str(exc_info.value).lower()
    
    db_session.rollback()


def test_audit_log_rls_isolation(db_session):
    """Verify that tenant RLS isolation works as expected on audit logs."""
    # 1. Create Company A and Company B
    with tenant_context(auth_mode="true"):
        company_a = Company(name="Company A", slug="company-a")
        company_b = Company(name="Company B", slug="company-b")
        db_session.add_all([company_a, company_b])
        db_session.commit()
        db_session.refresh(company_a)
        db_session.refresh(company_b)

        user_a = User(
            email="user_a@test.com",
            full_name="User A",
            password_hash="dummy",
            role=UserRole.RECRUITER,
            company_id=company_a.id,
        )
        user_b = User(
            email="user_b@test.com",
            full_name="User B",
            password_hash="dummy",
            role=UserRole.RECRUITER,
            company_id=company_b.id,
        )
        db_session.add_all([user_a, user_b])
        db_session.commit()
        db_session.refresh(user_a)
        db_session.refresh(user_b)

    # 2. Write audit logs for Company A and Company B
    log_a = log_audit_event(
        db=db_session,
        action="test.rls_a",
        actor_type="RECRUITER",
        actor_id=user_a.id,
        company_id=company_a.id,
    )
    log_b = log_audit_event(
        db=db_session,
        action="test.rls_b",
        actor_type="RECRUITER",
        actor_id=user_b.id,
        company_id=company_b.id,
    )

    # 3. Query under Company A context
    with tenant_context(tenant_id=str(company_a.id)):
        logs = db_session.scalars(select(AuditLog)).all()
        # Should ONLY see log_a
        assert len(logs) == 1
        assert logs[0].id == log_a.id

    # 4. Query under Company B context
    with tenant_context(tenant_id=str(company_b.id)):
        logs = db_session.scalars(select(AuditLog)).all()
        # Should ONLY see log_b
        assert len(logs) == 1
        assert logs[0].id == log_b.id


def test_audit_log_metadata_sanitization(db_session):
    """Verify that password, keys, tokens, and authorization parameters are recursively sanitized."""
    metadata = {
        "user_email": "clean@test.com",
        "nested": {
            "password": "super-secret-password-123",
            "api_key": "xoxb-1234567890",
            "normal_field": "hello",
        },
        "data_list": [
            {"token": "jwt-token-val"},
            {"safe_val": 42}
        ],
        "authorization": "Bearer token-data",
        "secret": "hidden-info",
        "auth": "secret-auth"
    }
    
    # Sanitize using the function directly first
    sanitized = sanitize_metadata(metadata)
    assert sanitized["user_email"] == "clean@test.com"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["nested"]["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["normal_field"] == "hello"
    assert sanitized["data_list"][0]["token"] == "[REDACTED]"
    assert sanitized["data_list"][1]["safe_val"] == 42
    assert sanitized["authorization"] == "[REDACTED]"
    assert sanitized["secret"] == "[REDACTED]"
    assert sanitized["auth"] == "[REDACTED]"

    # Write audit log and check database contents
    with tenant_context(auth_mode="true"):
        company = Company(name="Sanitization Corp", slug="sanitization-corp")
        db_session.add(company)
        db_session.commit()
        db_session.refresh(company)

    log = log_audit_event(
        db=db_session,
        action="test.sanitization",
        actor_type="RECRUITER",
        company_id=company.id,
        metadata=metadata
    )
    
    # Reload from DB and verify
    db_session.expire(log)
    with tenant_context(auth_mode="true"):
        reloaded = db_session.scalar(select(AuditLog).where(AuditLog.id == log.id))
        meta_db = reloaded.metadata_json
        assert meta_db["user_email"] == "clean@test.com"
        assert meta_db["nested"]["password"] == "[REDACTED]"
        assert meta_db["nested"]["api_key"] == "[REDACTED]"
        assert meta_db["nested"]["normal_field"] == "hello"
        assert meta_db["authorization"] == "[REDACTED]"


def test_audit_event_creation_from_endpoints(api_client, db_session):
    """Verify that calling register, login, and session revocation creates correct audit events."""
    # 1. Register a new user
    register_payload = {
        "company_name": "Audit Events Inc",
        "email": "audit_events@test.com",
        "password": "super-secure-password-123",
        "full_name": "Audit Events Tester"
    }
    
    response = api_client.post("/api/v1/auth/register", json=register_payload)
    assert response.status_code == 201
    reg_data = response.json()
    user_id = reg_data["user"]["id"]
    company_id = reg_data["user"]["company_id"]
    
    # Check that register audit event was created
    with tenant_context(auth_mode="true"):
        logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "auth.register")
        ).all()
        assert len(logs) == 1
        assert logs[0].actor_id == uuid.UUID(user_id)
        assert logs[0].company_id == uuid.UUID(company_id)
        assert logs[0].metadata_json["email"] == "audit_events@test.com"
        
    # 2. Login successfully
    login_payload = {
        "email": "audit_events@test.com",
        "password": "super-secure-password-123"
    }
    response = api_client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    login_data = response.json()
    access_token = login_data["access_token"]
    
    # Check that login audit event was created
    with tenant_context(auth_mode="true"):
        logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "auth.login")
        ).all()
        assert len(logs) == 1
        assert logs[0].actor_id == uuid.UUID(user_id)
        assert logs[0].company_id == uuid.UUID(company_id)
        assert logs[0].metadata_json["email"] == "audit_events@test.com"
        
    # 3. Login failed
    failed_payload = {
        "email": "audit_events@test.com",
        "password": "wrong-password"
    }
    response = api_client.post("/api/v1/auth/login", json=failed_payload)
    assert response.status_code == 401
    
    # Check that login_failed audit event was created
    with tenant_context(auth_mode="true"):
        logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "auth.login_failed")
        ).all()
        assert len(logs) == 1
        assert logs[0].metadata_json["email"] == "audit_events@test.com"
        assert logs[0].metadata_json["password"] == "[REDACTED]"
        
    # 4. Revoke a session
    # First get the list of active sessions
    headers = {"Authorization": f"Bearer {access_token}"}
    sessions_resp = api_client.get("/api/v1/auth/sessions", headers=headers)
    assert sessions_resp.status_code == 200
    sessions_list = sessions_resp.json()
    assert len(sessions_list) > 0
    session_id_to_revoke = sessions_list[0]["id"]
    
    # Revoke session
    revoke_payload = {"session_id": session_id_to_revoke}
    revoke_resp = api_client.post("/api/v1/auth/sessions/revoke", json=revoke_payload, headers=headers)
    assert revoke_resp.status_code == 200
    
    # Check that session revocation audit event was created
    with tenant_context(auth_mode="true"):
        logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "auth.session_revoked")
        ).all()
        assert len(logs) == 1
        assert logs[0].actor_id == uuid.UUID(user_id)
        assert logs[0].company_id == uuid.UUID(company_id)
        assert logs[0].metadata_json["session_id"] == session_id_to_revoke
