import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from server import app
from db.session import get_db, tenant_context
from models import Company, User, CandidateProfile, CandidateResume, Application, Candidate, InterviewSlot, Interview, Job
from models.enums import CompanyStatus, UserRole, VerificationState, JobStatus
from core.auth_providers import DBVerificationTokenProvider


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


def test_disposable_email_blocked_recruiter(api_client):
    """Verify that recruiter signup with a disposable email domain is blocked."""
    payload = {
        "email": "badactor@mailinator.com",
        "password": "securepassword123",
        "full_name": "Bad Recruiter",
        "company_name": "Disposable Inc",
    }
    response = api_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "Disposable email" in response.json()["detail"]


def test_disposable_email_blocked_candidate(api_client):
    """Verify that candidate signup with a disposable email domain is blocked."""
    payload = {
        "email": "badcandidate@yopmail.com",
        "password": "securepassword123",
        "full_name": "Bad Candidate",
    }
    response = api_client.post("/api/v1/auth/register/candidate", json=payload)
    assert response.status_code == 400
    assert "Disposable email" in response.json()["detail"]


def test_recruiter_unverified_flow(api_client, db_session):
    """Verify recruiter verification requirements: block login, allow /me, allow verify, allow operations after verify."""
    # 1. Register recruiter (automatically set to unverified)
    payload = {
        "email": "recruiter@legitcorp.com",
        "password": "securepassword123",
        "full_name": "Legit Recruiter",
        "company_name": "Legit Corp",
    }
    # Mock DNS validation to pass for this domain
    from unittest.mock import patch
    with patch("api.auth.validate_domain_dns") as mock_dns:
        mock_dns.return_value = {"error": None, "mx_verified": True, "domain_exists": True, "domain": "legitcorp.com"}
        resp = api_client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201

    reg_data = resp.json()
    token = reg_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Assert unverified recruiter login is blocked
    login_payload = {
        "email": "recruiter@legitcorp.com",
        "password": "securepassword123",
    }
    resp = api_client.post("/api/v1/auth/login", json=login_payload)
    assert resp.status_code == 403
    assert "Email verification required" in resp.json()["detail"]

    # 3. Assert /me is ALLOWED for unverified recruiter
    resp = api_client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email_verified"] is False

    # 4. Assert protected recruiter route (e.g. /sessions or /jobs) is BLOCKED with 403
    resp = api_client.get("/api/v1/auth/sessions", headers=headers)
    assert resp.status_code == 403
    assert "Email verification required" in resp.json()["detail"]

    # 5. Extract verification code from DB
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "recruiter@legitcorp.com"))
        assert user is not None
        assert user.email_verified is False
        
        from models.verification_token import VerificationToken
        token_row = db_session.scalar(
            select(VerificationToken)
            .where(VerificationToken.user_id == user.id, VerificationToken.consumed_at.is_(None))
            .order_by(VerificationToken.created_at.desc())
        )
        assert token_row is not None
        # We can't read plaintext code since it's hashed, but we can verify it using provider helper
        # Or mock verify_token or use the provider to verify
        # Let's generate a new token and verify it via the API
        code = DBVerificationTokenProvider.create_token(
            db=db_session,
            user_id=user.id,
            token_type="email_otp"
        )

    # 6. Verify via verify-email endpoint
    verify_payload = {
        "email": "recruiter@legitcorp.com",
        "code": code
    }
    resp = api_client.post("/api/v1/auth/verify-email", json=verify_payload)
    assert resp.status_code == 200
    verify_data = resp.json()
    new_token = verify_data["access_token"]
    verified_headers = {"Authorization": f"Bearer {new_token}"}

    # 7. Assert login and protected operations now succeed
    resp = api_client.post("/api/v1/auth/login", json=login_payload)
    assert resp.status_code == 200

    resp = api_client.get("/api/v1/auth/sessions", headers=verified_headers)
    assert resp.status_code == 200


def test_candidate_unverified_block(api_client, db_session):
    """Verify that unverified candidates are blocked from resume actions, applications, and scheduling."""
    # 1. Register candidate
    payload = {
        "email": "candidate@legithub.com",
        "password": "securepassword123",
        "full_name": "Legit Candidate",
    }
    resp = api_client.post("/api/v1/auth/register/candidate", json=payload)
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Set up a mock resume, application, and booking slot in DB
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "candidate@legithub.com"))
        
        # Create a resume
        resume = CandidateResume(
            user_id=user.id,
            filename="my_cv.pdf",
            file_path="/storage/my_cv.pdf",
            is_active=False
        )
        db_session.add(resume)
        
        # Create a company and candidate object for application
        company = Company(name="Test Target Corp", slug="test-target-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        recruiter = User(
            email="recruiter-test@test-target-corp.com",
            full_name="Test Recruiter",
            password_hash="fakehash123",
            role=UserRole.RECRUITER,
            company_id=company.id,
            is_active=True,
            email_verified=True
        )
        db_session.add(recruiter)
        db_session.flush()

        job = Job(
            company_id=company.id,
            title="Software Engineer",
            status=JobStatus.OPEN
        )
        db_session.add(job)
        db_session.flush()

        candidate = Candidate(
            company_id=company.id,
            email=user.email,
            full_name=user.full_name
        )
        db_session.add(candidate)
        db_session.flush()

        # Create an application
        application = Application(
            company_id=company.id,
            job_id=job.id,
            candidate_id=candidate.id
        )
        db_session.add(application)
        db_session.flush()

        # Create an interview and slot
        interview = Interview(
            company_id=company.id,
            application_id=application.id,
            interviewer_id=recruiter.id,
            title="Screening Call",
            stage="screening",
            scheduled_at="2026-06-20T10:00:00Z"
        )
        db_session.add(interview)
        db_session.flush()

        slot = InterviewSlot(
            company_id=company.id,
            interview_id=interview.id,
            start_time="2026-06-20T10:00:00Z",
            end_time="2026-06-20T10:45:00Z",
            status="confirmed"
        )
        db_session.add(slot)
        db_session.commit()
        
        resume_id = resume.id
        application_id = application.id
        slot_id = slot.id

    # 2. Attempt toggle active resume (Expect 403 because email & phone are unverified)
    resp = api_client.post(f"/api/v1/auth/candidate/resumes/{resume_id}/toggle-active", headers=headers)
    assert resp.status_code == 403
    assert "verified before performing this action" in resp.json()["detail"]

    # 3. Attempt delete resume (Expect 403)
    resp = api_client.delete(f"/api/v1/auth/candidate/resumes/{resume_id}", headers=headers)
    assert resp.status_code == 403

    # 4. Attempt withdraw application (Expect 403)
    resp = api_client.post(f"/api/v1/applications/{application_id}/withdraw", headers=headers)
    assert resp.status_code == 403

    # 5. Attempt cancel booking slot (Expect 403)
    resp = api_client.post(f"/api/v1/candidate/bookings/{slot_id}/cancel", headers=headers)
    assert resp.status_code == 403

    # 6. Now, verify candidate email and phone in database
    with tenant_context(auth_mode="true"):
        profile = db_session.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        profile.email_verified = True
        profile.phone_verified = True
        user.email_verified = True
        db_session.add(profile)
        db_session.add(user)
        db_session.commit()

    # 7. Assert actions now succeed or pass the verification guard
    resp = api_client.post(f"/api/v1/auth/candidate/resumes/{resume_id}/toggle-active", headers=headers)
    assert resp.status_code == 200

    resp = api_client.post(f"/api/v1/applications/{application_id}/withdraw", headers=headers)
    assert resp.status_code == 200

    resp = api_client.post(f"/api/v1/candidate/bookings/{slot_id}/cancel", headers=headers)
    assert resp.status_code == 200
