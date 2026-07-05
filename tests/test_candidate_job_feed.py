import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from server import app
from db.session import get_db, tenant_context
from models import User, Company, Job, Candidate, Application, CandidateProfile, CandidateResume, ApplicationSnapshot
from models.session import UserSession
from models.enums import JobStatus, ApplicationStatus
from core.candidate_matching import calculate_candidate_job_match


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


def test_applicability_engine_matching():
    # Test case 1: Partial match
    match1 = calculate_candidate_job_match(
        candidate_skills=["Python", "Docker", "Git"],
        job_title="Software Engineer",
        job_description="We are looking for a Python developer who knows Docker and Kubernetes.",
        job_settings=None
    )
    assert match1["applicability_score"] == 86 # 2 matching skills (python, docker) out of 3 total detected (python, docker, kubernetes)
    assert "Python" in match1["matching_skills"] or "python" in match1["matching_skills"]
    assert "Docker" in match1["matching_skills"] or "docker" in match1["matching_skills"]
    assert "Kubernetes" in match1["missing_skills"] or "kubernetes" in match1["missing_skills"]

    # Test case 2: No configured/detected skills on job should return 100% match gracefully
    match2 = calculate_candidate_job_match(
        candidate_skills=["Python"],
        job_title="General Role",
        job_description="Do some general tasks.",
        job_settings=None
    )
    assert match2["applicability_score"] == 100
    assert len(match2["matching_skills"]) == 0
    assert len(match2["missing_skills"]) == 0

    # Test case 3: Configured settings required_skills takes precedence
    match3 = calculate_candidate_job_match(
        candidate_skills=["React", "TypeScript"],
        job_title="Frontend Engineer",
        job_description="Write some code.",
        job_settings={"required_skills": ["React", "GraphQL"]}
    )
    assert match3["applicability_score"] == 80
    assert "React" in match3["matching_skills"]
    assert "GraphQL" in match3["missing_skills"]


def test_job_feed_and_apply_flow(api_client, db_session):
    # 1. Setup candidate account
    reg_payload = {
        "email": "candidate_feed_test@example.com",
        "password": "securepassword123",
        "full_name": "Test Candidate",
        "phone_number": "+15550199205",
    }
    resp = api_client.post("/api/v1/auth/register/candidate", json=reg_payload)
    assert resp.status_code == 201
    cand_data = resp.json()
    cand_user_id = uuid.UUID(cand_data["user"]["id"])

    # Update candidate profile skills and verify
    with tenant_context(auth_mode="true"):
        user = db_session.scalar(select(User).where(User.id == cand_user_id))
        user.email_verified = True
        db_session.add(user)
        profile = db_session.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == cand_user_id)
        )
        assert profile is not None
        profile.skills = ["Python", "Docker"]
        profile.email_verified = True
        profile.phone_verified = True
        db_session.add(profile)
        
        # Add a test resume
        resume = CandidateResume(
            user_id=cand_user_id,
            filename="my_resume.pdf",
            file_path="uploads/candidates/my_resume.pdf",
            is_active=True,
            parsed_skills=["Python", "Docker"],
            parsed_summary="Experienced developer profile."
        )
        db_session.add(resume)
        
        # Setup Company and Active Job
        company = Company(
            name="Feed Test Corp",
            slug="feed-test-corp"
        )
        db_session.add(company)
        db_session.flush()
        
        job = Job(
            company_id=company.id,
            title="Senior Python Architect",
            description="Looking for an engineer with skills in Python, Docker, and Kubernetes.",
            status=JobStatus.OPEN,
            settings={}
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(resume)
        db_session.refresh(job)

    # Login to get valid JWT token
    login_resp = api_client.post("/api/v1/auth/login/candidate", json={
        "email": reg_payload["email"],
        "password": reg_payload["password"]
    })
    assert login_resp.status_code == 200
    cand_token = login_resp.json()["access_token"]
    cand_headers = {"Authorization": f"Bearer {cand_token}"}

    # 2. Test GET /jobs/feed
    with tenant_context(auth_mode="true"):
        users_list = db_session.scalars(select(User)).all()
        sessions_list = db_session.scalars(select(UserSession)).all()
        print("ALL USERS:", [{"id": str(u.id), "email": u.email, "role": u.role} for u in users_list])
        print("ALL SESSIONS:", [{"id": str(s.id), "user_id": str(s.user_id), "is_revoked": s.is_revoked, "expires_at": s.expires_at} for s in sessions_list])

    resp = api_client.get("/api/v1/jobs/feed", headers=cand_headers)
    print("STATUS CODE:", resp.status_code)
    print("RESPONSE JSON:", resp.json())
    assert resp.status_code == 200
    feed_data = resp.json()
    assert feed_data["total"] >= 1
    
    # Check that our created job has match stats
    matched_job = next(j for j in feed_data["results"] if j["id"] == str(job.id))
    assert matched_job["title"] == "Senior Python Architect"
    assert matched_job["applicability_score"] > 0
    assert "python" in [s.lower() for s in matched_job["matching_skills"]]
    assert "docker" in [s.lower() for s in matched_job["matching_skills"]]
    assert "kubernetes" in [s.lower() for s in matched_job["missing_skills"]]

    # 3. Test duplicate check and resume ownership checks
    # Try using another candidate's resume (invalid uuid)
    apply_payload = {
        "job_id": str(job.id),
        "resume_id": str(uuid.uuid4())
    }
    resp = api_client.post("/api/v1/applications/apply", json=apply_payload, headers=cand_headers)
    assert resp.status_code == 400
    assert "Invalid resume selected" in resp.json()["detail"]

    # Apply successfully with candidate's own resume
    apply_payload = {
        "job_id": str(job.id),
        "resume_id": str(resume.id)
    }
    resp = api_client.post("/api/v1/applications/apply", json=apply_payload, headers=cand_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    app_id = uuid.UUID(resp.json()["application_id"])

    # Try applying again - should fail with 409 duplicate conflict
    resp = api_client.post("/api/v1/applications/apply", json=apply_payload, headers=cand_headers)
    assert resp.status_code == 409
    assert "already applied" in resp.json()["detail"]

    # 4. Verify snapshot immutability
    db_session.expire_all()
    with tenant_context(auth_mode="true"):
        snapshot = db_session.scalar(
            select(ApplicationSnapshot).where(ApplicationSnapshot.application_id == app_id)
        )
        assert snapshot is not None
        assert snapshot.resume_snapshot["filename"] == "my_resume.pdf"
        assert "Python" in snapshot.resume_snapshot["parsed_skills"]
        assert snapshot.candidate_snapshot["full_name"] == "Test Candidate"

        # Modify candidate's active profile and resume database records
        profile.skills = ["Java"]
        profile.full_name = "New Modified Name"
        db_session.add(profile)
        
        resume.filename = "new_resume.pdf"
        resume.parsed_skills = ["Java"]
        db_session.add(resume)
        db_session.commit()

    # Verify that the historically submitted snapshot was NOT mutated
    db_session.expire_all()
    with tenant_context(auth_mode="true"):
        fresh_snapshot = db_session.scalar(
            select(ApplicationSnapshot).where(ApplicationSnapshot.application_id == app_id)
        )
        assert fresh_snapshot.resume_snapshot["filename"] == "my_resume.pdf"
        assert "Python" in fresh_snapshot.resume_snapshot["parsed_skills"]
        assert fresh_snapshot.candidate_snapshot["full_name"] == "Test Candidate"
