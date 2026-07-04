import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from server import app
from db.session import get_db, tenant_context
from models import Company, User
from models.enums import CompanyStatus, UserRole, VerificationState

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

def test_unonboarded_recruiter_workspace_blocked(api_client, db_session):
    """Verify that workspace endpoints (RequireRecruiter) reject un-onboarded recruiters with 403."""
    # 1. Register a recruiter
    res_reg = api_client.post("/api/v1/auth/register", json={
        "email": "recruiter.unonboarded@company.com",
        "password": "Password123!",
        "full_name": "Unonboarded Recruiter",
        "company_name": "Unonboarded Corp",
    })
    assert res_reg.status_code == 201
    token = res_reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate email verification directly in DB for test simplicity
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "recruiter.unonboarded@company.com"))
        user.email_verified = True
        db_session.add(user)
        db_session.commit()

    # 2. Attempt to list jobs (RequireRecruiter/TenantDb workspace API)
    response = api_client.get("/api/v1/jobs", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Onboarding incomplete"

def test_onboarded_recruiter_workspace_allowed(api_client, db_session):
    """Verify that completing onboarding allows accessing workspace endpoints."""
    # 1. Register a recruiter
    res_reg = api_client.post("/api/v1/auth/register", json={
        "email": "recruiter.onboarded@onboarded.com",
        "password": "Password123!",
        "full_name": "Onboarded Recruiter",
        "company_name": "Onboarded Corp",
    })
    assert res_reg.status_code == 201
    token = res_reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate email verification directly in DB
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "recruiter.onboarded@onboarded.com"))
        user.email_verified = True
        db_session.add(user)
        db_session.commit()

    # 2. Call setup-company to complete onboarding
    setup_payload = {
        "company_name": "Onboarded Corp",
        "company_website": "https://onboarded.com",
        "company_domain": "onboarded.com",
        "industry": "Technology",
        "company_size": "11-50"
    }
    res_setup = api_client.post("/api/v1/auth/setup-company", json=setup_payload, headers=headers)
    assert res_setup.status_code == 200
    assert res_setup.json()["user"]["company_onboarding_completed"] is True



    # 3. Call jobs list endpoint (Should succeed now!)
    res_jobs = api_client.get("/api/v1/jobs", headers=headers)
    assert res_jobs.status_code == 200
    assert isinstance(res_jobs.json(), list)

def test_candidate_unaffected_by_recruiter_onboarding(api_client, db_session):
    """Verify candidate accounts are not affected by recruiter onboarding rules."""
    # 1. Register a candidate
    email = "candidate.test@gmail.com"
    phone = "+15555555555"
    res_reg = api_client.post("/api/v1/auth/register/candidate", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Test Candidate",
        "phone_number": phone
    })
    assert res_reg.status_code == 201

    # Verify Email OTP
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == email))
        from core.auth_providers.email import DBVerificationTokenProvider
        email_otp = DBVerificationTokenProvider.create_token(
            db=db_session,
            user_id=user.id,
            token_type="email_otp",
            expires_in_minutes=10
        )

    api_client.post("/api/v1/auth/email/verify-otp", json={"email": email, "code": email_otp})
    
    # Verify Phone OTP to get active token
    from core.verification_service import _mock_phone_otps
    phone_otp = _mock_phone_otps[phone]["code"]
    res_phone = api_client.post("/api/v1/auth/phone/verify-otp", json={"email": email, "code": phone_otp})
    assert res_phone.status_code == 200
    token = res_phone.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Candidate cannot access recruiter profile endpoint (/auth/me) - returns 403
    res_me_recruiter = api_client.get("/api/v1/auth/me", headers=headers)
    assert res_me_recruiter.status_code == 403

    # Candidate CAN access candidate profile endpoint (/auth/candidate/me) - returns 200
    res_me = api_client.get("/api/v1/auth/candidate/me", headers=headers)
    assert res_me.status_code == 200

    # Verify that the derived property on the DB model evaluates to True for candidate
    with tenant_context(auth_mode="true"):
        db_user = db_session.scalar(select(User).where(User.email == email))
        assert db_user.company_onboarding_completed is True



def test_setup_company_validation_enforced(api_client, db_session):
    """Verify that backend rejects invalid/empty onboarding payloads."""
    # 1. Register a recruiter
    res_reg = api_client.post("/api/v1/auth/register", json={
        "email": "recruiter.validator@company.com",
        "password": "Password123!",
        "full_name": "Validator Recruiter",
        "company_name": "Validator Corp",
    })
    assert res_reg.status_code == 201
    token = res_reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Attempt to setup company with invalid website
    setup_payload = {
        "company_name": "Validator Corp",
        "company_website": "invalid_url", # Should fail shared validation
        "company_domain": "company.com",
        "industry": "Technology",
        "company_size": "11-50"
    }
    response = api_client.post("/api/v1/auth/setup-company", json=setup_payload, headers=headers)
    assert response.status_code == 422 # Pydantic Validation error

def test_existing_onboarded_recruiter_unaffected(api_client, db_session):
    """Verify that existing recruiter accounts that completed setup before this change function normally."""
    # Create company and user with complete settings details in DB
    with tenant_context(auth_mode="true"):
        company = Company(
            name="Existing Completed Corp",
            slug="existing-completed-corp",
            status=CompanyStatus.ACTIVE,
            settings={
                "website": "https://completed.com",
                "domain": "completed.com",
                "industry": "Consulting",
                "company_size": "51-200"
            }
        )
        db_session.add(company)
        db_session.flush()

        user = User(
            company_id=company.id,
            email="recruiter.completed@completed.com",
            password_hash="hashed_dummy",
            full_name="Completed Recruiter",
            role=UserRole.RECRUITER,
            email_verified=True
        )
        db_session.add(user)
        db_session.commit()

    # Generate JWT for this user
    from core.security import create_access_token
    token = create_access_token(
        subject=str(user.id),
        claims={"role": user.role.value, "company_id": str(company.id), "jti": "some_jti"}
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Verify that listing jobs (workspace endpoint) is allowed immediately
    res_jobs = api_client.get("/api/v1/jobs", headers=headers)
    assert res_jobs.status_code == 200

def test_owner_role_enforcement(api_client, db_session):
    """Verify company owners follow the same onboarding checks."""
    # 1. Register owner (email/password signup defaults to Owner role)
    res_reg = api_client.post("/api/v1/auth/register", json={
        "email": "owner.test@company.com",
        "password": "Password123!",
        "full_name": "Test Owner",
        "company_name": "Test Owner Corp",
    })
    assert res_reg.status_code == 201
    token = res_reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "owner.test@company.com"))
        user.email_verified = True
        db_session.add(user)
        db_session.commit()

    # Owner should be blocked initially
    res_jobs = api_client.get("/api/v1/jobs", headers=headers)
    assert res_jobs.status_code == 403

def test_multi_tenant_isolation(api_client, db_session):
    """Verify that Recruiter A cannot setup/modify Company B's profile."""
    # Register Recruiter A
    res_a = api_client.post("/api/v1/auth/register", json={
        "email": "recruiter.a@comp-a.com",
        "password": "Password123!",
        "full_name": "Recruiter A",
        "company_name": "Company A",
    })
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register Recruiter B
    res_b = api_client.post("/api/v1/auth/register", json={
        "email": "recruiter.b@comp-b.com",
        "password": "Password123!",
        "full_name": "Recruiter B",
        "company_name": "Company B",
    })
    cid_b = res_b.json()["user"]["company_id"]

    # Verify email for A
    with tenant_context(auth_mode="true"):
        user_a = db_session.scalar(select(User).where(User.email == "recruiter.a@comp-a.com"))
        user_a.email_verified = True
        db_session.add(user_a)
        db_session.commit()

    setup_payload = {
        "company_name": "Company A",
        "company_website": "https://comp-a.com",
        "company_domain": "comp-b.com", # Attempting to claim B's domain/MX
        "industry": "HR Tech",
        "company_size": "11-50"
    }
    response = api_client.post("/api/v1/auth/setup-company", json=setup_payload, headers=headers_a)
    assert response.status_code == 400


def test_public_email_onboarding_wizard(api_client, db_session):
    """Verify that public email domains bypass website-mismatch checks but remain strictly PENDING."""
    res_reg = api_client.post("/api/v1/auth/register", json={
        "email": "recruiter.public@gmail.com",
        "password": "Password123!",
        "full_name": "Public Recruiter",
        "company_name": "Public Freelancer Corp",
    })
    assert res_reg.status_code == 201
    token = res_reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate email verification directly in DB
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "recruiter.public@gmail.com"))
        user.email_verified = True
        db_session.add(user)
        db_session.commit()

    # Call setup-company with any website domain (Gmail doesn't enforce mismatch check)
    setup_payload = {
        "company_name": "Public Freelancer Corp",
        "company_website": "https://randomweb.com",
        "company_domain": "gmail.com",
        "industry": "Consulting",
        "company_size": "1-10",
        "logo_url": "https://logo.com/img.png"
    }
    res_setup = api_client.post("/api/v1/auth/setup-company", json=setup_payload, headers=headers)
    assert res_setup.status_code == 200
    
    # Assert company verification flags are pending & unverified
    with tenant_context(auth_mode="true"):
        company = db_session.scalar(select(Company).where(Company.id == user.company_id))
        assert company.verification_state.value == "pending_verification"
        assert company.domain_verified is False
        assert company.website_verified is False
        assert company.settings.get("logo_url") == "https://logo.com/img.png"


def test_corporate_email_website_mismatch(api_client, db_session):
    """Verify that corporate domains enforce matching website domains."""
    res_reg = api_client.post("/api/v1/auth/register", json={
        "email": "recruiter@tesla.com",
        "password": "Password123!",
        "full_name": "Tesla Recruiter",
        "company_name": "Tesla Motors",
    })
    assert res_reg.status_code == 201
    token = res_reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate email verification directly in DB
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "recruiter@tesla.com"))
        user.email_verified = True
        db_session.add(user)
        db_session.commit()

    # Call setup-company with mismatching website (google.com) -> should fail with 400
    setup_payload = {
        "company_name": "Tesla Motors",
        "company_website": "https://google.com",
        "company_domain": "tesla.com",
        "industry": "Automotive",
        "company_size": "501+"
    }
    res_setup = api_client.post("/api/v1/auth/setup-company", json=setup_payload, headers=headers)
    assert res_setup.status_code == 400
    assert "website domain" in res_setup.json()["detail"].lower()


def test_optimistic_concurrency_conflict(api_client, db_session):
    """Verify update_job rejects stale client updates with 409 Conflict."""
    # 1. Setup recruiter and complete onboarding
    res_reg = api_client.post("/api/v1/auth/register", json={
        "email": "recruiter.concurrency@tesla.com",
        "password": "Password123!",
        "full_name": "Concurrency Recruiter",
        "company_name": "Tesla Concurrency",
    })
    token = res_reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "recruiter.concurrency@tesla.com"))
        user.email_verified = True
        db_session.add(user)
        db_session.commit()

    setup_payload = {
        "company_name": "Tesla Concurrency",
        "company_website": "https://tesla.com",
        "company_domain": "tesla.com",
        "industry": "Automotive",
        "company_size": "501+"
    }
    api_client.post("/api/v1/auth/setup-company", json=setup_payload, headers=headers)

    # 2. Create a job
    res_job = api_client.post("/api/v1/jobs", json={
        "title": "Software Engineer",
        "department": "Engineering",
        "description": "Write code.",
        "status": "draft"
    }, headers=headers)
    assert res_job.status_code == 201
    job_id = res_job.json()["id"]

    # 3. Simulate database updating the record (newer timestamp)
    import datetime
    with tenant_context(auth_mode="true"):
        from models import Job
        job = db_session.scalar(select(Job).where(Job.id == job_id))
        job.updated_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=10)
        db_session.add(job)
        db_session.commit()

    # 4. Attempt to update job with a stale client_updated_at -> should return 409
    stale_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)).isoformat()
    res_update = api_client.patch(f"/api/v1/jobs/{job_id}", json={
        "title": "Updated Software Engineer",
        "client_updated_at": stale_time
    }, headers=headers)
    assert res_update.status_code == 409


def test_job_revisions_captured(api_client, db_session):
    """Verify that JobRevision is created when modifying published jobs."""
    # 1. Setup recruiter and complete onboarding
    res_reg = api_client.post("/api/v1/auth/register", json={
        "email": "recruiter.revisions@tesla.com",
        "password": "Password123!",
        "full_name": "Revisions Recruiter",
        "company_name": "Tesla Revisions",
    })
    token = res_reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.email == "recruiter.revisions@tesla.com"))
        user.email_verified = True
        db_session.add(user)
        db_session.commit()

    setup_payload = {
        "company_name": "Tesla Revisions",
        "company_website": "https://tesla.com",
        "company_domain": "tesla.com",
        "industry": "Automotive",
        "company_size": "501+"
    }
    api_client.post("/api/v1/auth/setup-company", json=setup_payload, headers=headers)

    # 2. Create and publish a job (status = open)
    res_job = api_client.post("/api/v1/jobs", json={
        "title": "Hardware Engineer",
        "department": "Engineering",
        "description": "Design circuits.",
        "status": "open"
    }, headers=headers)
    assert res_job.status_code == 201
    job_id = res_job.json()["id"]

    # 3. Modify the job title
    res_update = api_client.patch(f"/api/v1/jobs/{job_id}", json={
        "title": "Senior Hardware Engineer",
        "change_reason": "Seniority level correction"
      }, headers=headers)
    assert res_update.status_code == 200

    # 4. Assert JobRevision exists with previous state details in DB
    with tenant_context(auth_mode="true"):
        from models import JobRevision
        revs = db_session.scalars(select(JobRevision).where(JobRevision.job_id == job_id)).all()
        assert len(revs) == 1
        assert revs[0].version == 1
        assert revs[0].title == "Hardware Engineer"  # Captured previous state
        assert revs[0].change_reason == "Seniority level correction"
        assert revs[0].created_by == user.id

