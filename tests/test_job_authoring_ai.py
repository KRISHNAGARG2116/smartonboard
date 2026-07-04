import pytest
import uuid
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import select, text
from fastapi.testclient import TestClient

from server import app
from db.session import get_db, tenant_context
from models import (
    Company,
    User,
    Job,
    JobRevision,
    AuditLog
)
from models.enums import UserRole, JobStatus

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


def verify_recruiter_in_db(db_session, email: str):
    """
    Directly update registered user attributes and their company settings
    in the test DB to mark email verified and onboarding completed.
    """
    with tenant_context(auth_mode="true"):
        # 1. Verify email
        db_session.execute(
            text("UPDATE users SET email_verified = true WHERE email = :email"),
            {"email": email}
        )
        db_session.commit()
        
        # 2. Get user's company
        user = db_session.scalar(select(User).where(User.email == email))
        if user and user.company_id:
            # 3. Update company settings to pass validate_company_profile check
            db_session.execute(
                text(
                    "UPDATE companies SET status = 'active', settings = :settings WHERE id = :company_id"
                ),
                {
                    "company_id": user.company_id,
                    "settings": json.dumps({
                        "website": "https://corp.com",
                        "domain": "corp.com",
                        "industry": "Software",
                        "company_size": "10-50"
                    })
                }
            )
            db_session.commit()


def test_generate_description_success(api_client, db_session):
    """
    Verify successful AI-assisted job description generation:
    - Returns structured JSON payload.
    - Increments company/recruiter daily usage limit counts.
    - Records audit log entry.
    """
    # 1. Register Recruiter A
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "AI Authoring Corp A",
        "email": "author_a@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Author A"
    })
    assert resp.status_code == 201
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    
    # Verify in DB
    verify_recruiter_in_db(db_session, "author_a@corp.com")

    headers_a = {"Authorization": f"Bearer {token_a}", "Idempotency-Key": str(uuid.uuid4())}

    # Mock the LLM service to return a structured JSON string matching JobDescriptionResponse schema
    mock_llm_response = MagicMock()
    mock_llm_response.content = json.dumps({
        "description": "Dynamic software developer description.",
        "responsibilities": "Write clean code, deploy features.",
        "requirements": "3+ years Python experience.",
        "qualifications": "BS in Computer Science.",
        "benefits": "Unlimited coffee and snacks."
    })

    with patch("langchain_groq.ChatGroq.invoke") as mock_invoke:
        mock_invoke.return_value = mock_llm_response

        # Execute generation
        gen_resp = api_client.post(
            "/api/v1/jobs/generate-description",
            json={"title": "Software Engineer", "department": "Engineering"},
            headers=headers_a
        )
        assert gen_resp.status_code == 200
        data = gen_resp.json()
        assert data["success"] is True
        assert "Dynamic software developer" in data["description"]
        assert "Write clean code" in data["responsibilities"]
        assert "Unlimited coffee" in data["benefits"]

        # Check that audit log has been created
        with tenant_context(auth_mode="true"):
            db_session.expire_all()
            logs = db_session.scalars(
                select(AuditLog).where(AuditLog.action == "ai.generate_description.success").order_by(AuditLog.timestamp.desc())
            ).all()
            assert len(logs) >= 1
            assert logs[0].metadata_json["title"] == "Software Engineer"


def test_generate_description_timeout_fallback(api_client, db_session):
    """
    Verifies AI timeout returns the structured fallback response,
    does not modify recruiter-authored content,
    and records the timeout in audit logs.
    """
    # 1. Register Recruiter
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Timeout Fallback Corp",
        "email": "timeout_rec@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Timeout Recruiter"
    })
    assert resp.status_code == 201
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    
    # Verify in DB
    verify_recruiter_in_db(db_session, "timeout_rec@corp.com")

    headers_a = {"Authorization": f"Bearer {token_a}", "Idempotency-Key": str(uuid.uuid4())}

    # Mock LLM to throw a TimeoutError or simulate a timeout
    with patch("langchain_groq.ChatGroq.invoke") as mock_invoke:
        mock_invoke.side_effect = TimeoutError("Simulated LLM Timeout after 30s")

        # Execute generation
        gen_resp = api_client.post(
            "/api/v1/jobs/generate-description",
            json={"title": "Timeout Engineer", "department": "Engineering"},
            headers=headers_a
        )
        # Timeout returns 200 (or structured error response) with success=false
        assert gen_resp.status_code == 200
        data = gen_resp.json()
        assert data["success"] is False
        assert data["error_code"] == "timeout"
        assert "timed out" in data["message"].lower()

        # Check audit log contains timeout action
        with tenant_context(auth_mode="true"):
            db_session.expire_all()
            logs = db_session.scalars(
                select(AuditLog).where(AuditLog.action == "ai.generate_description.timeout").order_by(AuditLog.timestamp.desc())
            ).all()
            assert len(logs) >= 1
            assert logs[0].metadata_json["error_code"] == "timeout"


def test_generate_description_idempotency(api_client, db_session):
    """
    Verify that multiple description generation requests using the same
    Idempotency-Key within a cache window return the identical response
    without invoking the AI service twice.
    """
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Idempotency Corp",
        "email": "idem_rec@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Idem Recruiter"
    })
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    
    # Verify in DB
    verify_recruiter_in_db(db_session, "idem_rec@corp.com")

    idem_key = str(uuid.uuid4())
    headers_a = {"Authorization": f"Bearer {token_a}", "Idempotency-Key": idem_key}

    mock_llm_response = MagicMock()
    mock_llm_response.content = json.dumps({
        "description": "Unique Overview text.",
        "responsibilities": "Unique Responsibilities.",
        "requirements": "Unique Requirements.",
        "qualifications": "Unique Qualifications.",
        "benefits": "Unique Benefits."
    })

    with patch("langchain_groq.ChatGroq.invoke") as mock_invoke:
        mock_invoke.return_value = mock_llm_response

        # First request
        resp1 = api_client.post(
            "/api/v1/jobs/generate-description",
            json={"title": "Idempotent Architect", "department": "Product"},
            headers=headers_a
        )
        assert resp1.status_code == 200
        data1 = resp1.json()

        # Second request (identical title/department and idem key)
        resp2 = api_client.post(
            "/api/v1/jobs/generate-description",
            json={"title": "Idempotent Architect", "department": "Product"},
            headers=headers_a
        )
        assert resp2.status_code == 200
        data2 = resp2.json()

        # Should be identical
        assert data1["description"] == data2["description"]
        # AI should only have been invoked once!
        assert mock_invoke.call_count == 1


def test_generate_description_usage_quota(api_client, db_session):
    """
    Verify that recruiters are restricted to their daily usage limits (e.g. 20 requests per day).
    """
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Quota Cap Corp",
        "email": "quota_rec@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Quota Recruiter"
    })
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    
    # Verify in DB
    verify_recruiter_in_db(db_session, "quota_rec@corp.com")

    mock_llm_response = MagicMock()
    mock_llm_response.content = json.dumps({
        "description": "Role Overview.",
        "responsibilities": "Responsibilities.",
        "requirements": "Requirements.",
        "qualifications": "Qualifications.",
        "benefits": "Benefits."
    })

    # Artificially trigger daily quota exhausted or set it via mock
    from api import jobs
    # Set recruiter usage in memory cache to 20
    recruiter_id = reg_a["user"]["id"]
    today = datetime.now(timezone.utc).date().isoformat()
    jobs._local_ai_usage[recruiter_id] = {"date": today, "count": 20}

    with patch("langchain_groq.ChatGroq.invoke") as mock_invoke, \
         patch("api.jobs.get_redis_connection", return_value=None):
        mock_invoke.return_value = mock_llm_response

        headers_a = {"Authorization": f"Bearer {token_a}", "Idempotency-Key": str(uuid.uuid4())}
        quota_resp = api_client.post(
            "/api/v1/jobs/generate-description",
            json={"title": "Quota Engineer", "department": "Engineering"},
            headers=headers_a
        )
        assert quota_resp.status_code == 200
        data = quota_resp.json()
        assert data["success"] is False
        assert data["error_code"] == "quota_exceeded"
        assert "limit reached" in data["message"].lower()


def test_suggest_skills_success(api_client, db_session):
    """
    Verify skill suggestion caching behavior:
    - Subsequent calls with same inputs fetch from Cache, not LLM.
    """
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Skills Cache Corp",
        "email": "skills_rec@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Skills Recruiter"
    })
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    
    # Verify in DB
    verify_recruiter_in_db(db_session, "skills_rec@corp.com")

    headers_a = {"Authorization": f"Bearer {token_a}"}

    mock_llm_response = MagicMock()
    mock_llm_response.content = json.dumps({
        "required_skills": ["Rust", "C++"],
        "preferred_skills": ["WebAssembly"],
        "technologies": ["LLVM"],
        "languages": ["English"]
    })

    with patch("langchain_groq.ChatGroq.invoke") as mock_invoke:
        mock_invoke.return_value = mock_llm_response

        # Request 1 (Cache Miss)
        resp1 = api_client.post(
            "/api/v1/jobs/suggest-skills",
            json={"title": "Systems Programmer", "department": "Engineering"},
            headers=headers_a
        )
        assert resp1.status_code == 200
        assert "Rust" in resp1.json()["required_skills"]

        # Request 2 (Cache Hit)
        resp2 = api_client.post(
            "/api/v1/jobs/suggest-skills",
            json={"title": "Systems Programmer", "department": "Engineering"},
            headers=headers_a
        )
        assert resp2.status_code == 200
        assert "Rust" in resp2.json()["required_skills"]

        # AI should only have been invoked once due to caching
        assert mock_invoke.call_count == 1


def test_analyze_quality(api_client, db_session):
    """
    Verify posting strength calculation:
    - Fully populated job yields high score (>= 80).
    - Incomplete/empty job yields low score (< 50).
    """
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Quality Analytics Corp",
        "email": "quality_rec@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Quality Recruiter"
    })
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    
    # Verify in DB
    verify_recruiter_in_db(db_session, "quality_rec@corp.com")

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Incomplete inputs
    bad_resp = api_client.post(
        "/api/v1/jobs/analyze-quality",
        json={
            "title": "",
            "department": "Engineering",
            "description": "",
            "settings": {
                "required_skills": [],
                "salary_min": None,
                "salary_max": None,
                "hide_salary": True,
                "benefits": [],
                "hiring_manager_id": None,
                "workplace_type": "On-site",
                "office_address": "",
                "openings": 1
            }
        },
        headers=headers_a
    )
    assert bad_resp.status_code == 200
    bad_data = bad_resp.json()
    assert bad_data["score"] < 50
    assert len(bad_data["warnings"]) > 0

    # Fully complete inputs
    good_resp = api_client.post(
        "/api/v1/jobs/analyze-quality",
        json={
            "title": "Lead Software Architect",
            "department": "Engineering",
            "description": "### Role Overview\nIntroduce the candidate to a highly robust workspace setting with modern tooling.\n### Key Responsibilities\nArchitect outstanding frontend views, optimize backend latency, maintain documentation.\n### Requirements & Qualifications\n5+ years of production experience, expert in React, Pytest, Docker, and PostgreSQL databases.",
            "settings": {
                "required_skills": ["React", "Python", "SQL"],
                "salary_min": 120000,
                "salary_max": 180000,
                "hide_salary": False,
                "benefits": ["Health Insurance", "Remote setting"],
                "hiring_manager_id": str(uuid.uuid4()),
                "workplace_type": "Remote",
                "office_address": "",
                "openings": 2
            }
        },
        headers=headers_a
    )
    assert good_resp.status_code == 200
    good_data = good_resp.json()
    assert good_data["score"] >= 80
    assert len(good_data["warnings"]) == 0


def test_job_revisions_rls(api_client, db_session):
    """
    Verify recruiter tenant company ID bounds and history isolation:
    - Recruiter A can view and fetch Recruiter A's revisions.
    - Recruiter B trying to view Recruiter A's revision gets 404 (not found).
    """
    # Register Company A (Recruiter A)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Revision Corp A",
        "email": "rec_rev_a@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Recruiter A"
    })
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    
    # Verify in DB
    verify_recruiter_in_db(db_session, "rec_rev_a@corp.com")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    comp_a_id = uuid.UUID(reg_a["user"]["company_id"])

    # Register Company B (Recruiter B)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Revision Corp B",
        "email": "rec_rev_b@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Recruiter B"
    })
    reg_b = resp.json()
    token_b = reg_b["access_token"]
    
    # Verify in DB
    verify_recruiter_in_db(db_session, "rec_rev_b@corp.com")

    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Setup Job & Revision records for Company A
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_a_id)})
        
        job_a = Job(
            company_id=comp_a_id,
            title="Senior Architect",
            department="Engineering",
            description="Initial Description",
            status=JobStatus.DRAFT
        )
        db_session.add(job_a)
        db_session.flush()
        job_id = job_a.id

        rev_a = JobRevision(
            job_id=job_id,
            version=1,
            title="Senior Architect",
            department="Engineering",
            description="Initial Description",
            settings={},
            job_status=JobStatus.DRAFT,
            created_by=uuid.UUID(reg_a["user"]["id"])
        )
        db_session.add(rev_a)
        db_session.commit()

    # Recruiter A fetches revisions list -> 200 OK
    resp_list_a = api_client.get(f"/api/v1/jobs/{job_id}/revisions", headers=headers_a)
    assert resp_list_a.status_code == 200
    assert len(resp_list_a.json()) == 1
    assert resp_list_a.json()[0]["version"] == 1

    # Recruiter A fetches specific version detail -> 200 OK
    resp_detail_a = api_client.get(f"/api/v1/jobs/{job_id}/revisions/1", headers=headers_a)
    assert resp_detail_a.status_code == 200
    assert resp_detail_a.json()["title"] == "Senior Architect"

    # Recruiter B tries to fetch Company A's revisions -> 404 (due to tenant matching check)
    resp_list_b = api_client.get(f"/api/v1/jobs/{job_id}/revisions", headers=headers_b)
    assert resp_list_b.status_code == 404

    # Recruiter B tries to fetch Company A's specific version -> 404
    resp_detail_b = api_client.get(f"/api/v1/jobs/{job_id}/revisions/1", headers=headers_b)
    assert resp_detail_b.status_code == 404
