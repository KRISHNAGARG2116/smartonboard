import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select

from server import app
from db.session import get_db, tenant_context
from models import User, Company, Job, Candidate, Application, CandidateProfile, CandidateResume, ApplicationSnapshot, Interview, InterviewSlot
from models.enums import JobStatus, ApplicationStatus


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


def test_candidate_applications_me_and_withdraw(api_client, db_session):
    # 1. Register candidate
    reg_payload = {
        "email": "phase_f_cand@example.com",
        "password": "securepassword123",
        "full_name": "Phase F Candidate",
    }
    resp = api_client.post("/api/v1/auth/register/candidate", json=reg_payload)
    assert resp.status_code == 201
    cand_data = resp.json()
    cand_token = cand_data["access_token"]
    cand_headers = {"Authorization": f"Bearer {cand_token}"}
    cand_user_id = uuid.UUID(cand_data["user"]["id"])

    # Update profile and create resume and job setup
    with tenant_context(auth_mode="true"):
        profile = db_session.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == cand_user_id)
        )
        assert profile is not None
        profile.skills = ["Python", "Docker"]
        db_session.add(profile)
        
        resume = CandidateResume(
            user_id=cand_user_id,
            filename="phase_f_resume.pdf",
            file_path="uploads/candidates/phase_f_resume.pdf",
            is_active=True,
            parsed_skills=["Python", "Docker"],
            parsed_summary="Phase F test resume."
        )
        db_session.add(resume)
        
        company = Company(name="Phase F Corp", slug="phase-f-corp")
        db_session.add(company)
        db_session.flush()
        
        job = Job(
            company_id=company.id,
            title="Phase F Engineer",
            description="Docker python coding.",
            status=JobStatus.OPEN,
            settings={}
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(resume)
        db_session.refresh(job)

    # 2. Apply to Job
    apply_payload = {
        "job_id": str(job.id),
        "resume_id": str(resume.id)
    }
    resp = api_client.post("/api/v1/applications/apply", json=apply_payload, headers=cand_headers)
    assert resp.status_code == 200
    app_id = uuid.UUID(resp.json()["application_id"])

    # 3. Fetch applications via GET /applications/me
    resp = api_client.get("/api/v1/applications/me", headers=cand_headers)
    assert resp.status_code == 200
    my_apps = resp.json()
    assert len(my_apps) == 1
    
    app_details = my_apps[0]
    assert app_details["id"] == str(app_id)
    assert app_details["job_title"] == "Phase F Engineer"
    assert app_details["status"] == "submitted"
    assert "snapshot" in app_details
    assert app_details["snapshot"]["resume_snapshot"]["filename"] == "phase_f_resume.pdf"
    
    # Exclude check: verify recruiter-only attributes are absent
    assert "risk_score" not in app_details
    assert "candidate_notes" not in app_details
    assert "committee_status" not in app_details

    # 4. Withdraw application via POST /applications/{application_id}/withdraw
    resp = api_client.post(f"/api/v1/applications/{app_id}/withdraw", headers=cand_headers)
    assert resp.status_code == 200
    withdraw_data = resp.json()
    assert withdraw_data["success"] is True
    assert "notification_draft" in withdraw_data
    assert "Application Withdrawn" in withdraw_data["notification_draft"]["subject"]

    # Verify status is withdrawn
    db_session.expire_all()
    with tenant_context(auth_mode="true"):
        fresh_app = db_session.scalar(select(Application).where(Application.id == app_id))
        assert fresh_app.status == ApplicationStatus.WITHDRAWN


def test_candidate_interviews_and_authenticated_booking_lifecycle(api_client, db_session):
    # 1. Register candidate
    reg_payload = {
        "email": "phase_f_iv_cand@example.com",
        "password": "securepassword123",
        "full_name": "Phase F Interview Candidate",
    }
    resp = api_client.post("/api/v1/auth/register/candidate", json=reg_payload)
    assert resp.status_code == 201
    cand_data = resp.json()
    cand_token = cand_data["access_token"]
    cand_headers = {"Authorization": f"Bearer {cand_token}"}
    cand_user_id = uuid.UUID(cand_data["user"]["id"])

    # Setup database records
    with tenant_context(auth_mode="true"):
        company = Company(name="Phase F IV Corp", slug="phase-f-iv-corp")
        db_session.add(company)
        db_session.flush()
        
        recruiter = User(
            company_id=company.id,
            email="recruiter_iv@example.com",
            password_hash="...",
            full_name="Interviewer Recruiter",
            role="recruiter"
        )
        db_session.add(recruiter)
        db_session.flush()
        
        job = Job(
            company_id=company.id,
            title="Interview Engineer",
            description="...",
            status=JobStatus.OPEN,
            settings={}
        )
        db_session.add(job)
        db_session.flush()

        candidate = Candidate(
            company_id=company.id,
            email="phase_f_iv_cand@example.com",
            full_name="Phase F Interview Candidate"
        )
        db_session.add(candidate)
        db_session.flush()

        application = Application(
            company_id=company.id,
            job_id=job.id,
            candidate_id=candidate.id,
            status=ApplicationStatus.INTERVIEW,
            source="candidate_portal"
        )
        db_session.add(application)
        db_session.flush()

        # Schedule Interview
        interview = Interview(
            company_id=company.id,
            application_id=application.id,
            interviewer_id=recruiter.id,
            title="Phase F Technical panel",
            stage="technical",
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
            duration_minutes=45
        )
        db_session.add(interview)
        db_session.flush()

        # Confirmed slot
        slot = InterviewSlot(
            company_id=company.id,
            interview_id=interview.id,
            start_time=interview.scheduled_at,
            end_time=interview.scheduled_at + timedelta(minutes=45),
            status="confirmed",
            booking_token_hash="mock_hash"
        )
        db_session.add(slot)
        db_session.commit()
        db_session.refresh(interview)
        db_session.refresh(slot)

    # 2. Get interviews via GET /candidate/interviews
    resp = api_client.get("/api/v1/candidate/interviews", headers=cand_headers)
    assert resp.status_code == 200
    my_ivs = resp.json()
    assert len(my_ivs) == 1
    iv_details = my_ivs[0]
    assert iv_details["id"] == str(interview.id)
    assert iv_details["title"] == "Phase F Technical panel"
    assert iv_details["slot"]["id"] == str(slot.id)
    assert iv_details["slot"]["status"] == "confirmed"
    
    # Exclude check: verify booking_token_hash is excluded
    assert "booking_token_hash" not in iv_details
    assert "booking_token" not in iv_details["slot"]

    # 3. Reschedule booking via POST /candidate/interviews/bookings/{slot_id}/reschedule
    resched_time = interview.scheduled_at + timedelta(days=1, hours=2)
    resched_payload = {
        "new_start_time": resched_time.isoformat()
    }
    resp = api_client.post(f"/api/v1/candidate/bookings/{slot.id}/reschedule", json=resched_payload, headers=cand_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    db_session.expire_all()
    with tenant_context(auth_mode="true"):
        fresh_slot = db_session.scalar(select(InterviewSlot).where(InterviewSlot.id == slot.id))
        assert fresh_slot.start_time.replace(tzinfo=timezone.utc) == resched_time.replace(tzinfo=timezone.utc)

    # 4. Cancel booking via POST /candidate/interviews/bookings/{slot_id}/cancel
    resp = api_client.post(f"/api/v1/candidate/bookings/{slot.id}/cancel", headers=cand_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    db_session.expire_all()
    with tenant_context(auth_mode="true"):
        fresh_slot = db_session.scalar(select(InterviewSlot).where(InterviewSlot.id == slot.id))
        assert fresh_slot.status == "cancelled"
