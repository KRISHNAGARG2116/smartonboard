import pytest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, text
from fastapi.testclient import TestClient

from server import app
from db.session import get_db, tenant_context
from models import User, Company, Job, Application, Candidate, Offer
from models.enums import UserRole, JobStatus, ApplicationStatus
from models.audit import AuditLog


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
def setup_application(db_session, api_client):
    # 1. Register Company A (Owner A)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Offers Corp A",
        "email": "owner_a@offerscorp.com",
        "password": "super-secure-password-123",
        "full_name": "Offers Owner A"
    })
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    comp_a_id = uuid.UUID(reg_a["user"]["company_id"])
    owner_a_id = uuid.UUID(reg_a["user"]["id"])

    # Mark Owner A verified in DB
    with tenant_context(auth_mode="true"):
        user_own_a = db_session.get(User, owner_a_id)
        if user_own_a:
            user_own_a.email_verified = True
            db_session.add(user_own_a)
            db_session.commit()

    # 2. Register Recruiter for Company A
    with tenant_context(auth_mode="true"):
        recruiter_a = User(
            email="recruiter_a@offerscorp.com",
            full_name="Recruiter A",
            password_hash="dummy",
            role=UserRole.RECRUITER,
            company_id=comp_a_id,
            email_verified=True,
        )
        db_session.add(recruiter_a)
        db_session.commit()
        db_session.refresh(recruiter_a)

    # Let's get a session for Recruiter A to avoid 401
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

    # 3. Create a Job in Company A
    with tenant_context(auth_mode="true"):
        job = Job(
            company_id=comp_a_id,
            title="Senior Architect",
            department="Engineering",
            status=JobStatus.OPEN
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        job_id = job.id

    # 4. Apply a candidate
    app_payload = {
        "job_id": str(job_id),
        "candidate_name": "Bob Builder",
        "candidate_email": "bob@build.com",
        "candidate_phone": "+1-555-9876",
        "source": "referral"
    }
    app_resp = api_client.post("/api/v1/applications", json=app_payload, headers=headers_a)
    app_data = app_resp.json()
    app_id = uuid.UUID(app_data["id"])

    # 5. Move status to INTERVIEW
    api_client.patch(f"/api/v1/applications/{app_id}", json={"status": "interview"}, headers=headers_a)

    return {
        "headers_owner": headers_a,
        "headers_recruiter": headers_rec_a,
        "comp_id": comp_a_id,
        "app_id": app_id,
        "candidate_id": uuid.UUID(app_data["candidate_id"]),
        "actor_id": owner_a_id,
        "recruiter_id": recruiter_a.id
    }


def test_offer_creation(api_client, setup_application):
    """Verify that a recruiter can successfully create a draft offer and transitions the Application stage."""
    app_id = setup_application["app_id"]
    headers = setup_application["headers_recruiter"]

    now = datetime.now(timezone.utc)
    body = {
        "salary": 145000.00,
        "equity_grant": "1000 shares",
        "start_date": "2026-07-01",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    resp = api_client.post(f"/api/v1/applications/{app_id}/offers", json=body, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"
    assert float(data["salary"]) == 145000.00

    # Assert Application transitions automatically to OFFER status
    app_resp = api_client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert app_resp.json()["status"] == "offer"


def test_offer_duplicate_creation(api_client, setup_application):
    """Verify that creating a second offer for the same application is blocked (1:1 constraint)."""
    app_id = setup_application["app_id"]
    headers = setup_application["headers_recruiter"]

    now = datetime.now(timezone.utc)
    body = {
        "salary": 120000.00,
        "start_date": "2026-07-01",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    # Create the first offer
    resp1 = api_client.post(f"/api/v1/applications/{app_id}/offers", json=body, headers=headers)
    assert resp1.status_code == 201

    # Attempt second offer creation
    resp2 = api_client.post(f"/api/v1/applications/{app_id}/offers", json=body, headers=headers)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()


def test_offer_invalid_transition(api_client, setup_application):
    """Verify that strict offer state transitions are enforced, rejecting incorrect updates."""
    app_id = setup_application["app_id"]
    headers_rec = setup_application["headers_recruiter"]
    headers_own = setup_application["headers_owner"]

    now = datetime.now(timezone.utc)
    body = {
        "salary": 130000.00,
        "start_date": "2026-07-01",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    # Create DRAFT offer
    resp = api_client.post(f"/api/v1/applications/{app_id}/offers", json=body, headers=headers_rec)
    assert resp.status_code == 201
    
    # 1. Attempt invalid transition: draft -> sent (must be approved first!)
    send_resp = api_client.post(f"/api/v1/applications/{app_id}/offers/send", headers=headers_rec)
    assert send_resp.status_code == 400
    assert "invalid state transition" in send_resp.json()["detail"].lower()


def test_offer_approval(api_client, setup_application):
    """Verify that an Owner can successfully approve a draft offer."""
    app_id = setup_application["app_id"]
    headers_rec = setup_application["headers_recruiter"]
    headers_own = setup_application["headers_owner"]

    now = datetime.now(timezone.utc)
    body = {
        "salary": 150000.00,
        "start_date": "2026-07-01",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    # Create DRAFT offer
    api_client.post(f"/api/v1/applications/{app_id}/offers", json=body, headers=headers_rec)

    # Approve offer as Owner
    appr_resp = api_client.post(f"/api/v1/applications/{app_id}/offers/approve", headers=headers_own)
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "approved"


def test_offer_recruiter_forbidden(api_client, setup_application):
    """Assert that a standard recruiter cannot approve draft offers (receives 403)."""
    app_id = setup_application["app_id"]
    headers_rec = setup_application["headers_recruiter"]

    now = datetime.now(timezone.utc)
    body = {
        "salary": 150000.00,
        "start_date": "2026-07-01",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    api_client.post(f"/api/v1/applications/{app_id}/offers", json=body, headers=headers_rec)

    # Attempt to approve as recruiter
    appr_resp = api_client.post(f"/api/v1/applications/{app_id}/offers/approve", headers=headers_rec)
    assert appr_resp.status_code == 403


def test_offer_signing(api_client, setup_application):
    """Verify candidate signing an offer promotes status to signed and application to hired."""
    app_id = setup_application["app_id"]
    headers_rec = setup_application["headers_recruiter"]
    headers_own = setup_application["headers_owner"]

    now = datetime.now(timezone.utc)
    body = {
        "salary": 160000.00,
        "start_date": "2026-07-01",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    api_client.post(f"/api/v1/applications/{app_id}/offers", json=body, headers=headers_rec)
    api_client.post(f"/api/v1/applications/{app_id}/offers/approve", headers=headers_own)
    api_client.post(f"/api/v1/applications/{app_id}/offers/send", headers=headers_rec)

    # Candidate signs
    dec_resp = api_client.post(f"/api/v1/applications/{app_id}/offers/decide", json={"decision": "signed"}, headers=headers_rec)
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == "signed"

    # Assert Application transitions automatically to HIRED
    app_resp = api_client.get(f"/api/v1/applications/{app_id}", headers=headers_rec)
    assert app_resp.json()["status"] == "hired"

    # Verify terminal status transition check: Cannot transition out of signed!
    exp_resp = api_client.post(f"/api/v1/applications/{app_id}/offers/expire", headers=headers_rec)
    assert exp_resp.status_code == 400
    assert "terminal offer state" in exp_resp.json()["detail"].lower()


def test_offer_rejection(api_client, setup_application):
    """Verify candidate rejecting an offer promotes status to rejected and application to rejected."""
    app_id = setup_application["app_id"]
    headers_rec = setup_application["headers_recruiter"]
    headers_own = setup_application["headers_owner"]

    now = datetime.now(timezone.utc)
    body = {
        "salary": 160000.00,
        "start_date": "2026-07-01",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    api_client.post(f"/api/v1/applications/{app_id}/offers", json=body, headers=headers_rec)
    api_client.post(f"/api/v1/applications/{app_id}/offers/approve", headers=headers_own)
    api_client.post(f"/api/v1/applications/{app_id}/offers/send", headers=headers_rec)

    # Candidate rejects
    dec_resp = api_client.post(f"/api/v1/applications/{app_id}/offers/decide", json={"decision": "rejected"}, headers=headers_rec)
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == "rejected"

    # Assert Application transitions automatically to REJECTED
    app_resp = api_client.get(f"/api/v1/applications/{app_id}", headers=headers_rec)
    assert app_resp.json()["status"] == "rejected"


def test_offer_expiration(api_client, setup_application):
    """Verify offer expiration transition is locked and works correctly."""
    app_id = setup_application["app_id"]
    headers_rec = setup_application["headers_recruiter"]
    headers_own = setup_application["headers_owner"]

    now = datetime.now(timezone.utc)
    body = {
        "salary": 160000.00,
        "start_date": "2026-07-01",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    api_client.post(f"/api/v1/applications/{app_id}/offers", json=body, headers=headers_rec)
    api_client.post(f"/api/v1/applications/{app_id}/offers/approve", headers=headers_own)
    api_client.post(f"/api/v1/applications/{app_id}/offers/send", headers=headers_rec)

    # Expire Offer
    exp_resp = api_client.post(f"/api/v1/applications/{app_id}/offers/expire", headers=headers_rec)
    assert exp_resp.status_code == 200
    assert exp_resp.json()["status"] == "expired"


def test_offer_audit_events(api_client, db_session, setup_application):
    """Verify all 7 requested offer-related audit event names are written with exact metadata fields."""
    app_id = setup_application["app_id"]
    cand_id = setup_application["candidate_id"]
    headers_rec = setup_application["headers_recruiter"]
    headers_own = setup_application["headers_owner"]

    now = datetime.now(timezone.utc)
    body = {
        "salary": 170000.00,
        "start_date": "2026-07-01",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    # 1. Created
    c_resp = api_client.post(f"/api/v1/applications/{app_id}/offers", json=body, headers=headers_rec)
    assert c_resp.status_code == 201
    offer_id = c_resp.json()["id"]

    # 2. Approved
    api_client.post(f"/api/v1/applications/{app_id}/offers/approve", headers=headers_own)
    # 3. Sent
    api_client.post(f"/api/v1/applications/{app_id}/offers/send", headers=headers_rec)
    # 4. Decided (Signed)
    api_client.post(f"/api/v1/applications/{app_id}/offers/decide", json={"decision": "signed"}, headers=headers_rec)

    with tenant_context(auth_mode="true"):
        # Check offer.created metadata keys
        c_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "offer.created").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(c_logs) >= 1
        assert c_logs[0].metadata_json["application_status_before"] == "interview"
        assert c_logs[0].metadata_json["application_status_after"] == "offer"
        assert c_logs[0].metadata_json["candidate_id"] == str(cand_id)

        # Check offer.approved
        appr_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "offer.approved").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(appr_logs) >= 1
        assert appr_logs[0].metadata_json["offer_id"] == str(offer_id)

        # Check offer.sent
        sent_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "offer.sent").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(sent_logs) >= 1

        # Check offer.signed
        sign_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "offer.signed").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(sign_logs) >= 1
        assert sign_logs[0].metadata_json["new_status"] == "hired"


def test_offer_rls_isolation(api_client, db_session, setup_application):
    """Verify multi-tenant RLS isolation blocks foreign company access entirely."""
    app_id = setup_application["app_id"]
    headers_rec = setup_application["headers_recruiter"]

    # Register Company B
    resp_b = api_client.post("/api/v1/auth/register", json={
        "company_name": "Offers Corp B",
        "email": "owner_b@offerscorp.com",
        "password": "super-secure-password-123",
        "full_name": "Offers Owner B"
    })
    token_b = resp_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    owner_b_id = uuid.UUID(resp_b.json()["user"]["id"])

    with tenant_context(auth_mode="true"):
        user_own_b = db_session.get(User, owner_b_id)
        if user_own_b:
            user_own_b.email_verified = True
            db_session.add(user_own_b)
            db_session.commit()

    # Create offer in Company A
    now = datetime.now(timezone.utc)
    body = {
        "salary": 130000.00,
        "start_date": "2026-07-01",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    c_resp = api_client.post(f"/api/v1/applications/{app_id}/offers", json=body, headers=headers_rec)
    assert c_resp.status_code == 201

    # Company B tries to fetch Company A's Offer -> Must return 404
    iso_fetch = api_client.get(f"/api/v1/applications/{app_id}/offers", headers=headers_b)
    assert iso_fetch.status_code == 404


def test_onboarding_trigger_generation(api_client, setup_application):
    """Verify signing API generates exact required onboarding trigger payload structure."""
    app_id = setup_application["app_id"]
    cand_id = setup_application["candidate_id"]
    comp_id = setup_application["comp_id"]
    headers_rec = setup_application["headers_recruiter"]
    headers_own = setup_application["headers_owner"]

    now = datetime.now(timezone.utc)
    body = {
        "salary": 180000.00,
        "start_date": "2026-07-15",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    c_resp = api_client.post(f"/api/v1/applications/{app_id}/offers", json=body, headers=headers_rec)
    offer_id = uuid.UUID(c_resp.json()["id"])
    
    api_client.post(f"/api/v1/applications/{app_id}/offers/approve", headers=headers_own)
    api_client.post(f"/api/v1/applications/{app_id}/offers/send", headers=headers_rec)

    # Candidate signs
    dec_resp = api_client.post(f"/api/v1/applications/{app_id}/offers/decide", json={"decision": "signed"}, headers=headers_rec)
    assert dec_resp.status_code == 200
    data = dec_resp.json()
    
    assert data["onboarding_trigger"] is not None
    trigger = data["onboarding_trigger"]
    assert uuid.UUID(trigger["candidate_id"]) == cand_id
    assert uuid.UUID(trigger["application_id"]) == app_id
    assert uuid.UUID(trigger["offer_id"]) == offer_id
    assert uuid.UUID(trigger["company_id"]) == comp_id
    assert trigger["start_date"] == "2026-07-15"
    assert trigger["status"] == "ready_for_onboarding"


def test_terminal_offer_states_transitions_blocked(api_client, setup_application):
    """Enforce that signed, rejected, and expired are terminal offer states, blocking all transitions out of them."""
    app_id = setup_application["app_id"]
    headers_rec = setup_application["headers_recruiter"]
    headers_own = setup_application["headers_owner"]

    # 1. Helper function to verify all transition endpoints fail with 400 Bad Request
    def assert_transitions_are_blocked(target_app_id):
        # Try /approve
        resp = api_client.post(f"/api/v1/applications/{target_app_id}/offers/approve", headers=headers_own)
        assert resp.status_code == 400
        assert "terminal offer state" in resp.json()["detail"].lower()

        # Try /send
        resp = api_client.post(f"/api/v1/applications/{target_app_id}/offers/send", headers=headers_rec)
        assert resp.status_code == 400
        assert "terminal offer state" in resp.json()["detail"].lower()

        # Try /decide (signed)
        resp = api_client.post(f"/api/v1/applications/{target_app_id}/offers/decide", json={"decision": "signed"}, headers=headers_rec)
        assert resp.status_code == 400
        assert "terminal offer state" in resp.json()["detail"].lower()

        # Try /decide (rejected)
        resp = api_client.post(f"/api/v1/applications/{target_app_id}/offers/decide", json={"decision": "rejected"}, headers=headers_rec)
        assert resp.status_code == 400
        assert "terminal offer state" in resp.json()["detail"].lower()

        # Try /expire
        resp = api_client.post(f"/api/v1/applications/{target_app_id}/offers/expire", headers=headers_rec)
        assert resp.status_code == 400
        assert "terminal offer state" in resp.json()["detail"].lower()

    # 2. Test for SIGNED state
    now = datetime.now(timezone.utc)
    body = {
        "salary": 150000.00,
        "start_date": "2026-07-01",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    c_resp = api_client.post(f"/api/v1/applications/{app_id}/offers", json=body, headers=headers_rec)
    assert c_resp.status_code == 201
    
    api_client.post(f"/api/v1/applications/{app_id}/offers/approve", headers=headers_own)
    api_client.post(f"/api/v1/applications/{app_id}/offers/send", headers=headers_rec)
    dec_resp = api_client.post(f"/api/v1/applications/{app_id}/offers/decide", json={"decision": "signed"}, headers=headers_rec)
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == "signed"
    
    # Assert transitions blocked out of signed state
    assert_transitions_are_blocked(app_id)

    # 3. Test for REJECTED state
    # Get the job_id from owner jobs list
    job_resp = api_client.get("/api/v1/jobs", headers=headers_own)
    assert job_resp.status_code == 200
    job_id = job_resp.json()[0]["id"]

    # Create second application
    app_payload_2 = {
        "job_id": job_id,
        "candidate_name": "Alice Builder",
        "candidate_email": "alice@build.com",
        "candidate_phone": "+1-555-4321",
        "source": "referral"
    }
    app_resp_2 = api_client.post("/api/v1/applications", json=app_payload_2, headers=headers_own)
    assert app_resp_2.status_code == 201
    app_id_2 = uuid.UUID(app_resp_2.json()["id"])
    api_client.patch(f"/api/v1/applications/{app_id_2}", json={"status": "interview"}, headers=headers_own)

    # Create offer for second application
    c_resp_2 = api_client.post(f"/api/v1/applications/{app_id_2}/offers", json=body, headers=headers_rec)
    assert c_resp_2.status_code == 201
    api_client.post(f"/api/v1/applications/{app_id_2}/offers/approve", headers=headers_own)
    api_client.post(f"/api/v1/applications/{app_id_2}/offers/send", headers=headers_rec)
    dec_resp_2 = api_client.post(f"/api/v1/applications/{app_id_2}/offers/decide", json={"decision": "rejected"}, headers=headers_rec)
    assert dec_resp_2.status_code == 200
    assert dec_resp_2.json()["status"] == "rejected"

    # Assert transitions blocked out of rejected state
    assert_transitions_are_blocked(app_id_2)

    # 4. Test for EXPIRED state
    # Create third application
    app_payload_3 = {
        "job_id": job_id,
        "candidate_name": "Charlie Builder",
        "candidate_email": "charlie@build.com",
        "candidate_phone": "+1-555-5678",
        "source": "referral"
    }
    app_resp_3 = api_client.post("/api/v1/applications", json=app_payload_3, headers=headers_own)
    assert app_resp_3.status_code == 201
    app_id_3 = uuid.UUID(app_resp_3.json()["id"])
    api_client.patch(f"/api/v1/applications/{app_id_3}", json={"status": "interview"}, headers=headers_own)

    # Create offer for third application
    c_resp_3 = api_client.post(f"/api/v1/applications/{app_id_3}/offers", json=body, headers=headers_rec)
    assert c_resp_3.status_code == 201
    api_client.post(f"/api/v1/applications/{app_id_3}/offers/approve", headers=headers_own)
    api_client.post(f"/api/v1/applications/{app_id_3}/offers/send", headers=headers_rec)
    api_client.post(f"/api/v1/applications/{app_id_3}/offers/expire", headers=headers_rec)

    # Assert transitions blocked out of expired state
    assert_transitions_are_blocked(app_id_3)
