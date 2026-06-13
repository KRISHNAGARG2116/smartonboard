import pytest
import uuid
import json
import csv
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, text
from fastapi.testclient import TestClient
from server import app
from db.session import get_db, tenant_context
from models import User, Company, Job
from models.enums import UserRole, JobStatus
from models.audit import AuditLog
from core.audit import log_audit_event
from core.archive import LocalArchiveProvider, S3ArchiveProvider

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


def test_audit_logs_search_filtering_and_pagination(api_client, db_session):
    """Verify that audit logs search filters, sorting, and pagination work perfectly under Owner privileges."""
    # 1. Register Company A (Owner A)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Company A",
        "email": "owner_a@compa.com",
        "password": "super-secure-password-123",
        "full_name": "Owner A"
    })
    assert resp.status_code == 201
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    comp_a_id = uuid.UUID(reg_a["user"]["company_id"])
    owner_a_id = uuid.UUID(reg_a["user"]["id"])

    # Mark Owner A as verified
    with tenant_context(auth_mode="true"):
        user_a = db_session.get(User, owner_a_id)
        if user_a:
            user_a.email_verified = True
            db_session.add(user_a)
            db_session.commit()

    # 2. Register Company B (Owner B)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Company B",
        "email": "owner_b@compb.com",
        "password": "super-secure-password-123",
        "full_name": "Owner B"
    })
    assert resp.status_code == 201
    reg_b = resp.json()
    token_b = reg_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    comp_b_id = uuid.UUID(reg_b["user"]["company_id"])
    owner_b_id = uuid.UUID(reg_b["user"]["id"])

    # Mark Owner B as verified
    with tenant_context(auth_mode="true"):
        user_b = db_session.get(User, owner_b_id)
        if user_b:
            user_b.email_verified = True
            db_session.add(user_b)
            db_session.commit()

    # 3. Register a Recruiter for Company A (to test permissions!)
    with tenant_context(auth_mode="true"):
        recruiter_a = User(
            email="recruiter_a@compa.com",
            full_name="Recruiter A",
            password_hash="dummy",
            role=UserRole.RECRUITER,
            company_id=comp_a_id,
            email_verified=True,
        )
        db_session.add(recruiter_a)
        db_session.commit()
        db_session.refresh(recruiter_a)

    # Let's insert a UserSession for Recruiter A to avoid 401 Unauthorized session validation error
    from models.session import UserSession
    rec_session_id = uuid.uuid4()
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.bypass_audit_immutability', 'true', true)"))
        rec_us = UserSession(
            id=rec_session_id,
            user_id=recruiter_a.id,
            refresh_token_hash=str(uuid.uuid4()),
            ip_address="127.0.0.1",
            user_agent="pytest",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc)
        )
        db_session.add(rec_us)
        db_session.commit()
        db_session.execute(text("SELECT set_config('app.bypass_audit_immutability', 'false', true)"))

    # Let's get a token for Recruiter A
    from core.security import create_access_token
    rec_token = create_access_token(
        str(recruiter_a.id),
        {
            "company_id": str(comp_a_id),
            "role": UserRole.RECRUITER.value,
            "email": recruiter_a.email,
            "session_id": str(rec_session_id)
        }
    )
    headers_rec_a = {"Authorization": f"Bearer {rec_token}"}

    # 4. Insert dummy logs for Company A and Company B
    now = datetime.now(timezone.utc)
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.bypass_audit_immutability', 'true', true)"))
        
        # Log 1: Company A - Action 'auth.login'
        log1 = AuditLog(
            company_id=comp_a_id,
            actor_id=owner_a_id,
            actor_type="RECRUITER",
            action="auth.login",
            timestamp=now - timedelta(hours=2),
            ip_address="1.1.1.1"
        )
        # Log 2: Company A - Action 'job.created'
        log2 = AuditLog(
            company_id=comp_a_id,
            actor_id=owner_a_id,
            actor_type="RECRUITER",
            action="job.created",
            timestamp=now - timedelta(hours=1),
            ip_address="2.2.2.2"
        )
        # Log 3: Company A - Action 'auth.logout' (older log, 95 days old!)
        log3 = AuditLog(
            company_id=comp_a_id,
            actor_id=owner_a_id,
            actor_type="RECRUITER",
            action="auth.logout",
            timestamp=now - timedelta(days=95),
            ip_address="3.3.3.3"
        )
        # Log 4: Company B - Action 'auth.login'
        log4 = AuditLog(
            company_id=comp_b_id,
            actor_type="UNAUTHENTICATED",
            action="auth.login",
            timestamp=now,
            ip_address="4.4.4.4"
        )
        db_session.add_all([log1, log2, log3, log4])
        db_session.commit()
        db_session.execute(text("SELECT set_config('app.bypass_audit_immutability', 'false', true)"))

    # 5. Verify RLS Isolation and Search for Owner A
    # Query without filters: should retrieve Company A's 3 logs, NOT Company B's log!
    resp = api_client.get("/api/v1/audit/logs", headers=headers_a)
    assert resp.status_code == 200
    logs_data = resp.json()
    # It will contain 6 logs: the 3 above + auth.register + verification.domain_check + auth.email_verification_sent of the Owner A registration!
    assert len(logs_data) == 6
    actions = [l["action"] for l in logs_data]
    assert "auth.login" in actions
    assert "job.created" in actions
    assert "auth.logout" in actions
    assert "auth.register" in actions
    assert "verification.domain_check" in actions

    # 6. Verify Permissions: Recruiter A must be strictly forbidden (403 Forbidden)
    rec_resp = api_client.get("/api/v1/audit/logs", headers=headers_rec_a)
    assert rec_resp.status_code == 403
    assert "insufficient role privileges" in rec_resp.json()["detail"].lower()

    # 7. Verify Filters: Filter by action namespace 'auth.login'
    resp = api_client.get("/api/v1/audit/logs?action=auth.login", headers=headers_a)
    assert resp.status_code == 200
    filter_data = resp.json()
    assert len(filter_data) == 1
    assert filter_data[0]["action"] == "auth.login"
    assert filter_data[0]["ip_address"] == "1.1.1.1"

    # 8. Filter by Date range (excluding log3 which is 95 days old)
    start_str = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    resp = api_client.get(f"/api/v1/audit/logs?start_date={start_str}", headers=headers_a)
    assert resp.status_code == 200
    date_data = resp.json()
    assert len(date_data) == 5  # domain_check + register + email_verification_sent + log1 + log2
    assert "auth.logout" not in [l["action"] for l in date_data]

    # 9. Test Pagination and Sorting
    # Limit 1, Offset 0 sorted by timestamp asc
    resp = api_client.get("/api/v1/audit/logs?limit=1&offset=0&sort_by=timestamp&sort_order=asc", headers=headers_a)
    assert resp.status_code == 200
    page1 = resp.json()
    assert len(page1) == 1
    assert page1[0]["action"] == "auth.logout"  # The oldest log!


def test_audit_logs_export(api_client, db_session):
    """Verify Owner-only bulk CSV and JSON exports, and verify export logging."""
    # 1. Register Owner A
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Export Corp",
        "email": "owner_export@test.com",
        "password": "super-secure-password-123",
        "full_name": "Export Owner"
    })
    reg_data = resp.json()
    token = reg_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    comp_id = uuid.UUID(reg_data["user"]["company_id"])
    owner_id = uuid.UUID(reg_data["user"]["id"])

    # Mark Owner as verified
    with tenant_context(auth_mode="true"):
        user = db_session.get(User, owner_id)
        if user:
            user.email_verified = True
            db_session.add(user)
            db_session.commit()

    # 2. Export as CSV
    csv_resp = api_client.get("/api/v1/audit/logs/export?format=csv", headers=headers)
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    csv_body = csv_resp.text
    assert "Action,Actor Type" in csv_body
    assert "auth.register" in csv_body

    # 3. Export as JSON
    json_resp = api_client.get("/api/v1/audit/logs/export?format=json", headers=headers)
    assert json_resp.status_code == 200
    assert "application/json" in json_resp.headers["content-type"]
    json_data = json_resp.json()
    assert len(json_data) >= 1
    
    # Check that export action itself generated a 'security.audit_exported' audit event!
    with tenant_context(auth_mode="true"):
        export_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "security.audit_exported")
        ).all()
        assert len(export_logs) == 2  # CSV and JSON exports!
        assert export_logs[0].company_id == comp_id


def test_audit_logs_archival_and_retrieval(api_client, db_session):
    """Verify background archival worker purges hot database logs older than 90 days and retrieves them securely."""
    # 1. Register Company A (Owner A)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Archive A Corp",
        "email": "archive_owner_a@test.com",
        "password": "super-secure-password-123",
        "full_name": "Archive Owner A"
    })
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    comp_a_id = uuid.UUID(reg_a["user"]["company_id"])
    owner_a_id = uuid.UUID(reg_a["user"]["id"])

    # Mark Owner A as verified
    with tenant_context(auth_mode="true"):
        user_a = db_session.get(User, owner_a_id)
        if user_a:
            user_a.email_verified = True
            db_session.add(user_a)
            db_session.commit()

    # 2. Register Company B (Owner B)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Archive B Corp",
        "email": "archive_owner_b@test.com",
        "password": "super-secure-password-123",
        "full_name": "Archive Owner B"
    })
    reg_b = resp.json()
    token_b = reg_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    comp_b_id = uuid.UUID(reg_b["user"]["company_id"])
    owner_b_id = uuid.UUID(reg_b["user"]["id"])

    # Mark Owner B as verified
    with tenant_context(auth_mode="true"):
        user_b = db_session.get(User, owner_b_id)
        if user_b:
            user_b.email_verified = True
            db_session.add(user_b)
            db_session.commit()

    # 3. Insert a log older than 90 days for Company A
    now = datetime.now(timezone.utc)
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.bypass_audit_immutability', 'true', true)"))
        old_log = AuditLog(
            company_id=comp_a_id,
            actor_type="SYSTEM",
            action="archivable.action",
            timestamp=now - timedelta(days=120)
        )
        db_session.add(old_log)
        db_session.commit()
        db_session.execute(text("SELECT set_config('app.bypass_audit_immutability', 'false', true)"))

    # 4. Trigger cold archival run for Company A!
    archive_resp = api_client.post("/api/v1/audit/archive/run?days=90", headers=headers_a)
    assert archive_resp.status_code == 200
    arch_data = archive_resp.json()
    assert arch_data["success"] is True
    assert arch_data["uri"] is not None
    
    filename = arch_data["uri"].split("/")[-1]

    # Verify that the archivable log has been successfully purged from the database!
    with tenant_context(auth_mode="true"):
        purged = db_session.scalar(
            select(AuditLog).where(AuditLog.action == "archivable.action")
        )
        assert purged is None

    # 5. Retrieve the archived batch as Owner A
    retr_resp = api_client.get(f"/api/v1/audit/archive/retrieve?filename={filename}", headers=headers_a)
    assert retr_resp.status_code == 200
    batch_data = retr_resp.json()
    assert len(batch_data) == 1
    assert batch_data[0]["action"] == "archivable.action"

    # 6. Verify Tenant Isolation: Owner B must be forbidden (403 Forbidden)
    malicious_resp = api_client.get(f"/api/v1/audit/archive/retrieve?filename={filename}", headers=headers_b)
    assert malicious_resp.status_code == 403
    assert "you do not have permissions" in malicious_resp.json()["detail"].lower()
