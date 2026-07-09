import pytest
import uuid
import io
from datetime import datetime, timezone, date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from server import app
from db.session import get_db, tenant_context
from models import (
    User, Company, Job, Application, Offer, CandidateTask, Notification,
    UserSession, Candidate, Interview, InterviewSlot, CandidateProfile,
    CandidateProfileRevision
)
from models.enums import UserRole, ApplicationStatus, JobStatus
from core.security import create_access_token

@pytest.fixture
def test_setup(db_session):
    with tenant_context(auth_mode="true"):
        # Create company
        company = Company(name="Test Company", slug="test-company")
        db_session.add(company)
        db_session.commit()

        # Create candidate User
        candidate = User(
            email="candidate_refine@example.com",
            password_hash="hashed_password",
            full_name="Candidate Refine",
            role=UserRole.CANDIDATE,
            is_active=True
        )
        db_session.add(candidate)

        # Create recruiter User
        recruiter = User(
            email="recruiter_refine@example.com",
            password_hash="hashed_password",
            full_name="Recruiter Refine",
            role=UserRole.RECRUITER,
            company_id=company.id,
            is_active=True
        )
        db_session.add(recruiter)
        db_session.commit()

        # Create job
        job = Job(
            company_id=company.id,
            title="Test Job",
            description="Job description",
            status=JobStatus.OPEN
        )
        db_session.add(job)
        db_session.commit()

        # Create recruiter Candidate record
        cand_rec = Candidate(
            company_id=company.id,
            email=candidate.email,
            full_name=candidate.full_name
        )
        db_session.add(cand_rec)
        db_session.commit()

        # Create application
        app_record = Application(
            company_id=company.id,
            job_id=job.id,
            candidate_id=cand_rec.id,
            status=ApplicationStatus.SUBMITTED
        )
        db_session.add(app_record)
        db_session.commit()

        # Create candidate session
        session_id = uuid.uuid4()
        session = UserSession(
            id=session_id,
            user_id=candidate.id,
            refresh_token_hash=str(uuid.uuid4()),
            is_revoked=False,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc)
        )
        db_session.add(session)
        db_session.commit()

        # Create candidate profile
        profile = CandidateProfile(
            user_id=candidate.id,
            full_name=candidate.full_name,
            phone_verified=False,
            email_verified=True,
            preferences={},
            experience=[],
            education=[],
            links={},
            languages=[]
        )
        db_session.add(profile)
        db_session.commit()

    token = create_access_token(
        str(candidate.id),
        {
            "company_id": None,
            "role": UserRole.CANDIDATE.value,
            "email": candidate.email,
            "session_id": str(session_id)
        }
    )

    return {
        "company": company,
        "candidate": candidate,
        "recruiter": recruiter,
        "job": job,
        "application": app_record,
        "profile": profile,
        "headers": {"Authorization": f"Bearer {token}"}
    }

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

def test_dashboard_notification_extensions(api_client, db_session, test_setup):
    headers = test_setup["headers"]
    candidate = test_setup["candidate"]
    company = test_setup["company"]

    with tenant_context(auth_mode="true"):
        # Add notifications
        n1 = Notification(
            company_id=company.id,
            user_id=candidate.id,
            title="Interview scheduled",
            message="Your interview is confirmed.",
            type="interview",
            status="unread"
        )
        n2 = Notification(
            company_id=company.id,
            user_id=candidate.id,
            title="Document request",
            message="Please upload your passport.",
            type="document",
            status="unread"
        )
        db_session.add_all([n1, n2])
        db_session.commit()

    resp = api_client.get("/api/v1/candidate/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["unread_count"] == 2
    assert "recent_notifications" in data
    assert "grouped_notifications" in data
    assert len(data["recent_notifications"]) == 2
    assert any("interview" in g for g in data["grouped_notifications"])
    assert any("document" in g for g in data["grouped_notifications"])

def test_interview_availability_endpoint(api_client, db_session, test_setup):
    headers = test_setup["headers"]
    company = test_setup["company"]
    app_record = test_setup["application"]
    recruiter = test_setup["recruiter"]

    with tenant_context(auth_mode="true"):
        # Create Interview
        iv = Interview(
            company_id=company.id,
            application_id=app_record.id,
            interviewer_id=recruiter.id,
            title="Technical Interview",
            stage="Technical",
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
            duration_minutes=45
        )
        db_session.add(iv)
        db_session.commit()

        # Create slots
        slot_avail = InterviewSlot(
            company_id=company.id,
            interview_id=iv.id,
            start_time=datetime.now(timezone.utc) + timedelta(days=2),
            end_time=datetime.now(timezone.utc) + timedelta(days=2, minutes=45),
            status="available"
        )
        slot_conf = InterviewSlot(
            company_id=company.id,
            interview_id=iv.id,
            start_time=datetime.now(timezone.utc) + timedelta(days=3),
            end_time=datetime.now(timezone.utc) + timedelta(days=3, minutes=45),
            status="confirmed"
        )
        db_session.add_all([slot_avail, slot_conf])
        db_session.commit()

    # Query availability endpoint
    resp = api_client.get(f"/api/v1/candidate/interviews/{iv.id}/availability", headers=headers)
    assert resp.status_code == 200
    slots = resp.json()
    # Should only return the recruiter-approved "available" slot, not the "confirmed" slot
    assert len(slots) == 1
    assert slots[0]["status"] == "available"
    assert slots[0]["id"] == str(slot_avail.id)

def test_profile_preferences_revision_history(api_client, db_session, test_setup):
    headers = test_setup["headers"]
    profile = test_setup["profile"]

    # 1. Update preferences
    payload = {
        "preferences": {"dark_mode": True, "sms_notifications": False},
        "client_updated_at": profile.updated_at.isoformat()
    }
    resp = api_client.put("/api/v1/candidate/profile/preferences", json=payload, headers=headers)
    assert resp.status_code == 200
    res_json = resp.json()
    assert res_json["status"] == "success"
    assert "version" in res_json

    # Verify revision was created
    with tenant_context(auth_mode="true"):
        revisions = db_session.scalars(
            select(CandidateProfileRevision).where(CandidateProfileRevision.profile_id == profile.id)
        ).all()
        assert len(revisions) == 1
        assert revisions[0].version == 1
        assert revisions[0].snapshot_json["full_name"] == profile.full_name
