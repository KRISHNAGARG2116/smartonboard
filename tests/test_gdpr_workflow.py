import pytest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, text
from fastapi.testclient import TestClient

from server import app
from db.session import get_db, tenant_context
from models import User, Company, Job, Application, Candidate, Offer, CandidateNote, Interview, Scorecard
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
def setup_gdpr_data(db_session, api_client):
    # 1. Register Company A (Owner A)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "GDPR Corp A",
        "email": "owner_a@gdprcorp.com",
        "password": "super-secure-password-123",
        "full_name": "GDPR Owner A"
    })
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    headers_own_a = {"Authorization": f"Bearer {token_a}"}
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
            email="recruiter_a@gdprcorp.com",
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
            title="Principal Cryptographer",
            department="Security Research",
            status=JobStatus.OPEN,
            settings={"scorecard_criteria": ["encryption", "security_protocols"]}
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        job_id = job.id

    # 4. Apply candidate (generating candidate.created audit log containing PII)
    app_payload = {
        "job_id": str(job_id),
        "candidate_name": "Godfrey GDPR",
        "candidate_email": "godfrey@gdpr.com",
        "candidate_phone": "+1-555-0987",
        "source": "referral"
    }
    app_resp = api_client.post("/api/v1/applications", json=app_payload, headers=headers_own_a)
    assert app_resp.status_code == 201
    app_data = app_resp.json()
    app_id = uuid.UUID(app_data["id"])
    cand_id = uuid.UUID(app_data["candidate_id"])

    # 5. Move status to INTERVIEW
    api_client.patch(f"/api/v1/applications/{app_id}", json={"status": "interview"}, headers=headers_own_a)

    # 6. Add Candidate Note (generating note.created audit log containing notes metadata)
    api_client.post(f"/api/v1/applications/{app_id}/notes", json={"content": "Godfrey has great knowledge in RLS and GDPR"}, headers=headers_rec_a)

    # 7. Schedule Interview
    now = datetime.now(timezone.utc)
    int_payload = {
        "title": "Initial Screen",
        "stage": "screening",
        "scheduled_at": (now + timedelta(days=2)).isoformat(),
        "duration_minutes": 45,
        "interviewer_id": str(owner_a_id)
    }
    int_resp = api_client.post(f"/api/v1/applications/{app_id}/interviews", json=int_payload, headers=headers_own_a)
    assert int_resp.status_code == 201
    interview_id = uuid.UUID(int_resp.json()["id"])

    # 8. Submit Scorecard
    score_payload = {
        "overall_recommendation": "strong_yes",
        "notes": "Excellent encryption skills.",
        "criteria_scores": {"encryption": 5, "security_protocols": 5}
    }
    api_client.post(f"/api/v1/applications/{app_id}/interviews/{interview_id}/scorecard/submit", json=score_payload, headers=headers_own_a)

    # 9. Create draft Offer
    offer_payload = {
        "salary": 185000.00,
        "start_date": "2026-08-01",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    api_client.post(f"/api/v1/applications/{app_id}/offers", json=offer_payload, headers=headers_rec_a)

    return {
        "headers_owner": headers_own_a,
        "headers_recruiter": headers_rec_a,
        "comp_id": comp_a_id,
        "app_id": app_id,
        "cand_id": cand_id,
        "job_id": job_id,
        "owner_id": owner_a_id,
        "recruiter_id": recruiter_a.id,
        "interview_id": interview_id
    }


def test_gdpr_deletion_confirmation_required(api_client, setup_gdpr_data):
    """Verify that candidate deletion is strictly blocked without explicit confirm: true."""
    cand_id = setup_gdpr_data["cand_id"]
    headers_own = setup_gdpr_data["headers_owner"]

    # 1. Attempt deletion with confirm: false
    resp1 = api_client.post(f"/api/v1/candidates/{cand_id}/delete", json={"confirm": False}, headers=headers_own)
    assert resp1.status_code == 400
    assert "confirmation" in resp1.json()["detail"].lower()

    # 2. Attempt deletion missing confirm field entirely
    resp2 = api_client.post(f"/api/v1/candidates/{cand_id}/delete", json={}, headers=headers_own)
    assert resp2.status_code == 422 # Pydantic validation error


def test_gdpr_recruiter_forbidden(api_client, setup_gdpr_data):
    """Assert that standard recruiters receive 403 Forbidden on GDPR erasures."""
    cand_id = setup_gdpr_data["cand_id"]
    headers_rec = setup_gdpr_data["headers_recruiter"]

    resp = api_client.post(f"/api/v1/candidates/{cand_id}/delete", json={"confirm": True}, headers=headers_rec)
    assert resp.status_code == 403


def test_gdpr_rls_isolation(api_client, db_session, setup_gdpr_data):
    """Verify multi-tenant RLS isolation blocks foreign company deletion attempts."""
    cand_id = setup_gdpr_data["cand_id"]

    # Register Company B
    resp_b = api_client.post("/api/v1/auth/register", json={
        "company_name": "GDPR Corp B",
        "email": "owner_b@gdprcorp.com",
        "password": "super-secure-password-123",
        "full_name": "GDPR Owner B"
    })
    token_b = resp_b.json()["access_token"]
    headers_own_b = {"Authorization": f"Bearer {token_b}"}
    owner_b_id = uuid.UUID(resp_b.json()["user"]["id"])

    with tenant_context(auth_mode="true"):
        user_own_b = db_session.get(User, owner_b_id)
        if user_own_b:
            user_own_b.email_verified = True
            db_session.add(user_own_b)
            db_session.commit()

    # Company B Owner attempts to delete Company A's Candidate -> Must return 404
    resp = api_client.post(f"/api/v1/candidates/{cand_id}/delete", json={"confirm": True}, headers=headers_own_b)
    assert resp.status_code == 404


def test_gdpr_candidate_deletion_atomic_flow(api_client, db_session, setup_gdpr_data):
    """Verify cascading deletion, atomic database rollbacks, and log pseudonymization."""
    cand_id = setup_gdpr_data["cand_id"]
    app_id = setup_gdpr_data["app_id"]
    headers_own = setup_gdpr_data["headers_owner"]

    # Let's count matching active rows inside candidate, application, note, interview, scorecard, offer prior to deletion
    with tenant_context(auth_mode="true"):
        assert db_session.scalar(select(Candidate).where(Candidate.id == cand_id)) is not None
        assert db_session.scalar(select(Application).where(Application.id == app_id)) is not None
        assert len(db_session.scalars(select(CandidateNote).where(CandidateNote.application_id == app_id)).all()) == 1
        assert len(db_session.scalars(select(Interview).where(Interview.application_id == app_id)).all()) == 1
        assert len(db_session.scalars(select(Scorecard).where(Scorecard.application_id == app_id)).all()) == 1
        assert len(db_session.scalars(select(Offer).where(Offer.application_id == app_id)).all()) == 1

        # Check that we have a candidate.created and note.created historical audit log with Godfrey PII prior to erasure
        c_logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "candidate.created")).all()
        assert len(c_logs) >= 1
        assert c_logs[0].metadata_json["email"] == "godfrey@gdpr.com"

    # Execute Candidate erasure workflow
    resp = api_client.post(f"/api/v1/candidates/{cand_id}/delete", json={"confirm": True}, headers=headers_own)
    assert resp.status_code == 204

    # Expire in-memory SQLAlchemy identity map cache to force refetching updated objects from database
    db_session.expire_all()

    # Let's verify all child rows are cascadingly and completely deleted
    with tenant_context(auth_mode="true"):
        assert db_session.scalar(select(Candidate).where(Candidate.id == cand_id)) is None
        assert db_session.scalar(select(Application).where(Application.id == app_id)) is None
        assert len(db_session.scalars(select(CandidateNote).where(CandidateNote.application_id == app_id)).all()) == 0
        assert len(db_session.scalars(select(Interview).where(Interview.application_id == app_id)).all()) == 0
        assert len(db_session.scalars(select(Scorecard).where(Scorecard.application_id == app_id)).all()) == 0
        assert len(db_session.scalars(select(Offer).where(Offer.application_id == app_id)).all()) == 0

        # Assert historical audit logs are successfully pseudonymized!
        scrubbed_logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "candidate.created")).all()
        assert len(scrubbed_logs) >= 1
        assert scrubbed_logs[0].metadata_json["email"] == "[PSEUDONYMIZED]"

        # Assert a clean candidate.deleted log was created containing no PII, with actor_type reflecting Owner
        del_logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "candidate.deleted")).all()
        assert len(del_logs) == 1
        assert del_logs[0].actor_type == "OWNER"
        assert "email" not in del_logs[0].metadata_json
        assert "full_name" not in del_logs[0].metadata_json
        assert del_logs[0].metadata_json["candidate_id"] == str(cand_id)


def test_application_deletion_workflow(api_client, db_session, setup_gdpr_data):
    """Verify that recruiters can delete single applications, cascading only to that application's child rows."""
    headers_rec = setup_gdpr_data["headers_recruiter"]
    headers_own = setup_gdpr_data["headers_owner"]
    job_id = setup_gdpr_data["job_id"]
    cand_id = setup_gdpr_data["cand_id"]
    app_id = setup_gdpr_data["app_id"]

    # 1. Create a second application for the same candidate under Company A
    app_payload_2 = {
        "job_id": str(job_id),
        "candidate_name": "Godfrey GDPR",
        "candidate_email": "godfrey@gdpr.com",
        "candidate_phone": "+1-555-0987",
        "source": "referral"
    }
    # Wait, the candidate_email exists, so create_application fetches the existing candidate but creates a second application
    # unless they are already applied to this job (uq_applications_job_candidate constraint).
    # Since Godfrey already applied to job_id, we need to create a second job!
    with tenant_context(auth_mode="true"):
        job2 = Job(
            company_id=setup_gdpr_data["comp_id"],
            title="Junior Cryptographer",
            department="Security Research",
            status=JobStatus.OPEN
        )
        db_session.add(job2)
        db_session.commit()
        db_session.refresh(job2)
        job2_id = job2.id

    app_payload_2["job_id"] = str(job2_id)
    app_resp_2 = api_client.post("/api/v1/applications", json=app_payload_2, headers=headers_rec)
    assert app_resp_2.status_code == 201
    app_id_2 = uuid.UUID(app_resp_2.json()["id"])

    # Verify second application exists and candidate has 2 applications
    with tenant_context(auth_mode="true"):
        assert db_session.scalar(select(Application).where(Application.id == app_id)) is not None
        assert db_session.scalar(select(Application).where(Application.id == app_id_2)) is not None
        assert db_session.scalar(select(Candidate).where(Candidate.id == cand_id)) is not None

    # Recruiter deletes application 2 via DELETE /api/v1/applications/{application_id}
    del_resp = api_client.delete(f"/api/v1/applications/{app_id_2}", headers=headers_rec)
    assert del_resp.status_code == 204

    # Assert that application 2 is deleted, while candidate and application 1 remain completely untouched!
    with tenant_context(auth_mode="true"):
        assert db_session.scalar(select(Application).where(Application.id == app_id_2)) is None
        assert db_session.scalar(select(Application).where(Application.id == app_id)) is not None
        assert db_session.scalar(select(Candidate).where(Candidate.id == cand_id)) is not None

        # Check application.deleted audit log was created correctly
        del_logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "application.deleted")).all()
        assert len(del_logs) == 1
        assert del_logs[0].actor_type == "RECRUITER"
        assert del_logs[0].metadata_json["application_id"] == str(app_id_2)
