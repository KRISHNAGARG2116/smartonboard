import pytest
import uuid
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, text
from fastapi.testclient import TestClient

from server import app
from db.session import get_db, tenant_context
from models import User, Company, Job, Application, Candidate
from models.enums import UserRole, JobStatus, ApplicationStatus
from models.note import CandidateNote
from models.interview import Interview
from models.scorecard import Scorecard
from models.session import UserSession
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


def test_recruitment_workflow_complete_phase1(api_client, db_session):
    """Verify Notes, Interviews, notifications, and Scorecards with Structured Hiring under RLS constraints."""
    
    # 1. Register Company A (Owner A)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Sourcing Corp",
        "email": "owner_sourcing@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Sourcing Owner"
    })
    assert resp.status_code == 201
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    comp_a_id = uuid.UUID(reg_a["user"]["company_id"])
    owner_a_id = uuid.UUID(reg_a["user"]["id"])

    # 2. Register Company B (Owner B - for tenant isolation checks)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Isolation Corp",
        "email": "owner_iso@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Isolation Owner"
    })
    assert resp.status_code == 201
    reg_b = resp.json()
    token_b = reg_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    comp_b_id = uuid.UUID(reg_b["user"]["company_id"])
    owner_b_id = uuid.UUID(reg_b["user"]["id"])

    # Mark users as verified in the DB for the test client
    with tenant_context(auth_mode="true"):
        user_a = db_session.get(User, owner_a_id)
        if user_a:
            user_a.email_verified = True
            db_session.add(user_a)
        user_b = db_session.get(User, owner_b_id)
        if user_b:
            user_b.email_verified = True
            db_session.add(user_b)
        db_session.commit()

    # 3. Create a Job in Company A with Structured Hiring Criteria Templates inside Job.settings
    with tenant_context(auth_mode="true"):
        db_session.execute(sa_text := text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_a_id)})
        job = Job(
            company_id=comp_a_id,
            title="Senior Backend Engineer",
            department="Engineering",
            description="Write clean SQLAlchemy and FastAPI code.",
            status=JobStatus.OPEN,
            settings={
                "scorecard_criteria": ["python_coding", "system_design", "communication"]
            }
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        job_id = job.id

    # 4. Apply a candidate to this job under Company A (Creates Candidate & Application)
    app_payload = {
        "job_id": str(job_id),
        "candidate_name": "Jane Developer",
        "candidate_email": "jane@coder.com",
        "candidate_phone": "+1-555-0199",
        "source": "referral"
    }
    app_resp = api_client.post("/api/v1/applications", json=app_payload, headers=headers_a)
    assert app_resp.status_code == 201
    app_data = app_resp.json()
    app_id = uuid.UUID(app_data["id"])
    cand_id = uuid.UUID(app_data["candidate_id"])

    # Set application status to SCREENING to test automatic transition
    api_client.patch(f"/api/v1/applications/{app_id}", json={"status": "screening"}, headers=headers_a)

    # ----------------------------------------------------
    # SECTION A: CANDIDATE NOTES & COLLABORATION
    # ----------------------------------------------------
    # A.1 Create Note
    note_resp = api_client.post(
        f"/api/v1/applications/{app_id}/notes",
        json={"content": "Strong initial application. Resume is extremely polished."},
        headers=headers_a
    )
    assert note_resp.status_code == 201
    note_data = note_resp.json()
    note_id = uuid.UUID(note_data["id"])
    assert note_data["content"] == "Strong initial application. Resume is extremely polished."

    # A.2 List Notes
    list_notes_resp = api_client.get(f"/api/v1/applications/{app_id}/notes", headers=headers_a)
    assert list_notes_resp.status_code == 200
    notes_list = list_notes_resp.json()
    assert len(notes_list) == 1
    assert notes_list[0]["content"] == "Strong initial application. Resume is extremely polished."

    # A.3 Edit Note
    edit_note_resp = api_client.patch(
        f"/api/v1/applications/{app_id}/notes/{note_id}",
        json={"content": "Strong initial application. Verified GitHub portfolio, looks stellar."},
        headers=headers_a
    )
    assert edit_note_resp.status_code == 200
    assert edit_note_resp.json()["content"] == "Strong initial application. Verified GitHub portfolio, looks stellar."

    # Verify Note edit audit logs in DB
    with tenant_context(auth_mode="true"):
        notes_created_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "note.created").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(notes_created_logs) >= 1
        assert notes_created_logs[0].metadata_json["candidate_id"] == str(cand_id)
        assert notes_created_logs[0].metadata_json["application_id"] == str(app_id)

        notes_updated_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "note.updated").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(notes_updated_logs) == 1
        assert notes_updated_logs[0].metadata_json["note_id"] == str(note_id)

    # ----------------------------------------------------
    # SECTION B: INTERVIEWS SCHEDULING & TRANSITIONS
    # ----------------------------------------------------
    # B.1 Schedule Interview Loop
    now = datetime.now(timezone.utc)
    interview_payload = {
        "interviewer_id": str(owner_a_id),
        "title": "System Architecture Deep Dive",
        "stage": "technical_interview",
        "scheduled_at": (now + timedelta(days=2)).isoformat(),
        "duration_minutes": 60,
        "video_link": "https://meet.google.com/abc-defg-hij"
    }
    
    int_resp = api_client.post(
        f"/api/v1/applications/{app_id}/interviews",
        json=interview_payload,
        headers=headers_a
    )
    assert int_resp.status_code == 201
    int_data = int_resp.json()
    interview_id = uuid.UUID(int_data["id"])
    assert int_data["title"] == "System Architecture Deep Dive"

    # Assert notification draft payload is correctly generated in-place
    assert int_data["notification_draft"] is not None
    draft = int_data["notification_draft"]
    assert draft["recipient_email"] == "owner_sourcing@corp.com"
    assert "Jane Developer" in draft["body"]
    assert "System Architecture Deep Dive" in draft["subject"]
    assert draft["draft_payload"]["candidate_name"] == "Jane Developer"
    assert draft["draft_payload"]["interview_stage"] == "technical_interview"
    assert draft["draft_payload"]["video_link"] == "https://meet.google.com/abc-defg-hij"

    # B.2 Verify automatic status transition: SCREENING -> INTERVIEW
    app_check = api_client.get(f"/api/v1/applications/{app_id}", headers=headers_a)
    assert app_check.status_code == 200
    assert app_check.json()["status"] == "interview"

    # Verify both interview.scheduled and application.status_changed audit events are present
    with tenant_context(auth_mode="true"):
        int_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "interview.scheduled").order_by(AuditLog.timestamp.desc())
        ).all()
        print("DEBUG INT LOGS:", [(log.id, log.company_id, log.timestamp, log.metadata_json) for log in int_logs])
        assert len(int_logs) == 1
        assert int_logs[0].metadata_json["interview_id"] == str(interview_id)
        assert int_logs[0].metadata_json["previous_status"] == "screening"
        assert int_logs[0].metadata_json["new_status"] == "interview"

        status_change_logs = db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "application.status_changed",
                AuditLog.resource_id == str(app_id)
            ).order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(status_change_logs) >= 1
        assert status_change_logs[0].metadata_json["previous_status"] == "screening"
        assert status_change_logs[0].metadata_json["new_status"] == "interview"

    # B.3 List Interviews
    list_int_resp = api_client.get(f"/api/v1/applications/{app_id}/interviews", headers=headers_a)
    assert list_int_resp.status_code == 200
    assert len(list_int_resp.json()) == 1

    # B.4 Cancel/Update Interview
    cancel_resp = api_client.patch(
        f"/api/v1/applications/{app_id}/interviews/{interview_id}",
        json={"is_cancelled": True},
        headers=headers_a
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["is_cancelled"] is True

    # Verify interview.cancelled audit event in DB
    with tenant_context(auth_mode="true"):
        cancel_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "interview.cancelled").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(cancel_logs) == 1
        assert cancel_logs[0].metadata_json["interview_id"] == str(interview_id)

    # Re-enable interview to test scorecard submissions
    api_client.patch(
        f"/api/v1/applications/{app_id}/interviews/{interview_id}",
        json={"is_cancelled": False},
        headers=headers_a
    )

    # ----------------------------------------------------
    # SECTION C: SCORECARDS & STRUCTURED HIRING
    # ----------------------------------------------------
    # C.1 Try to submit scorecard with incorrect criteria keys (Must fail!)
    bad_scorecard_payload = {
        "criteria_scores": {
            "coding": 5,           # expected: python_coding
            "communication": 4
        },
        "overall_recommendation": "yes",
        "notes": "Excellent coder."
    }
    bad_resp = api_client.post(
        f"/api/v1/applications/{app_id}/interviews/{interview_id}/scorecard/submit",
        json=bad_scorecard_payload,
        headers=headers_a
    )
    assert bad_resp.status_code == 400
    assert "criteria mismatch" in bad_resp.json()["detail"].lower()

    # C.2 Submit scorecard with correct criteria matching Job.settings
    good_scorecard_payload = {
        "criteria_scores": {
            "python_coding": 5,
            "system_design": 4,
            "communication": 5
        },
        "overall_recommendation": "strong_yes",
        "notes": "Jane is an exceptional candidate. Deep python skills, robust design choices."
    }
    good_resp = api_client.post(
        f"/api/v1/applications/{app_id}/interviews/{interview_id}/scorecard/submit",
        json=good_scorecard_payload,
        headers=headers_a
    )
    assert good_resp.status_code == 201
    scorecard_data = good_resp.json()
    scorecard_id = uuid.UUID(scorecard_data["id"])
    assert scorecard_data["overall_recommendation"] == "strong_yes"

    # C.3 Retrieve submitted scorecard feedback
    get_sc_resp = api_client.get(
        f"/api/v1/applications/{app_id}/interviews/{interview_id}/scorecard",
        headers=headers_a
    )
    assert get_sc_resp.status_code == 200
    assert get_sc_resp.json()["overall_recommendation"] == "strong_yes"

    # Verify both scorecard.created and scorecard.submitted audit log events in DB
    with tenant_context(auth_mode="true"):
        sc_created_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "scorecard.created").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(sc_created_logs) == 1
        assert sc_created_logs[0].metadata_json["scorecard_id"] == str(scorecard_id)

        sc_submitted_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "scorecard.submitted").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(sc_submitted_logs) == 1
        assert sc_submitted_logs[0].metadata_json["overall_recommendation"] == "strong_yes"

    # ----------------------------------------------------
    # SECTION D: SECURITY & RLS TENANT ISOLATION
    # ----------------------------------------------------
    # D.1 Company B attempts to access Company A's Notes -> Must return 404
    iso_note_resp = api_client.get(f"/api/v1/applications/{app_id}/notes", headers=headers_b)
    assert iso_note_resp.status_code == 404

    # D.2 Company B attempts to schedule Interview on Company A's Application -> Must return 404
    iso_int_resp = api_client.post(
        f"/api/v1/applications/{app_id}/interviews",
        json=interview_payload,
        headers=headers_b
    )
    assert iso_int_resp.status_code == 404

    # D.3 Company B attempts to access Scorecard of Company A -> Must return 404
    iso_sc_resp = api_client.get(
        f"/api/v1/applications/{app_id}/interviews/{interview_id}/scorecard",
        headers=headers_b
    )
    assert iso_sc_resp.status_code == 404

    # ----------------------------------------------------
    # SECTION E: RECRUITER COLLABORATION NOTES DELETE
    # ----------------------------------------------------
    # Delete Note
    del_note_resp = api_client.delete(f"/api/v1/applications/{app_id}/notes/{note_id}", headers=headers_a)
    assert del_note_resp.status_code == 244 or del_note_resp.status_code == 204

    # Verify note.deleted audit event in DB
    with tenant_context(auth_mode="true"):
        del_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "note.deleted").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(del_logs) == 1
        assert del_logs[0].metadata_json["note_id"] == str(note_id)
