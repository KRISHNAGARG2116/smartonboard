import pytest
import uuid
import io
import shutil
from unittest.mock import patch, MagicMock
from sqlalchemy import select, text
from fastapi.testclient import TestClient
from server import app
from db.session import get_db, tenant_context
from models import User, Company, Job, Candidate, Application
from models.enums import UserRole, JobStatus, ApplicationStatus
from models.audit import AuditLog
from core.audit import log_audit_event, pseudonymize_audit_logs, DEFAULT_SCRUB_LIST
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


def test_archive_storage_providers():
    """Verify storage-agnostic provider interfaces."""
    # 1. Test LocalArchiveProvider
    local_provider = LocalArchiveProvider(base_dir="storage/test_archive")
    filename = "test_log_archive.json"
    content = b'{"logs": []}'
    
    path = local_provider.upload_archive(filename, content)
    assert "test_log_archive.json" in path
    
    retrieved = local_provider.download_archive(filename)
    assert retrieved == content
    
    # Clean up test files
    shutil.rmtree("storage/test_archive", ignore_errors=True)
    
    # 2. Test S3ArchiveProvider stub
    s3_provider = S3ArchiveProvider(bucket_name="compliance-tests")
    uri = s3_provider.upload_archive("test.json", b"test")
    assert uri == "s3://compliance-tests/test.json"
    
    data = s3_provider.download_archive("test.json")
    assert data == b"{}"


def test_recursive_nested_pseudonymization(db_session):
    """Verify recursive nested JSONB scrubbing of all 31 default keys under GDPR Right-to-Be-Forgotten."""
    # 1. Create a dummy audit log with complex nested metadata containing ALL 31 default scrub fields
    candidate_id = uuid.uuid4()
    candidate_email = "gdpr_candidate@test.com"
    
    metadata = {
        "candidate": {
            "profile": {
                "name": "Jane GDPR",
                "full_name": "Jane GDPR User",
                "first_name": "Jane",
                "last_name": "GDPR",
                "email": candidate_email,
                "personal_email": "jane_pers@test.com",
                "work_email": "jane_work@test.com",
                "phone": "+1999888777",
                "mobile": "+1999888666",
                "telephone": "12345",
                "address": "123 Security St",
                "city": "San Francisco",
                "state": "CA",
                "country": "US",
                "postal_code": "94103",
                "linkedin": "linkedin.com/jane",
                "github": "github.com/jane",
                "portfolio_url": "jane.dev",
                "website": "jane.me",
                "resume_text": "Experienced Python Engineer",
                "resume_url": "s3://resumes/jane.pdf",
                "resume_file": "jane.pdf",
                "cover_letter": "I love security.",
                "candidate_notes": "Highly recommended",
                "assessment_answers": "Answers: Yes, No",
                "candidate_links": ["github.com", "linkedin.com"],
                "candidate_id_external": "ext-9999",
                "ip_address": "127.0.0.1",
                "ai_explanation": "Extremely high capability score.",
                "ai_reasoning": "Fits all criteria.",
                "ai_summary": "Passed all screens.",
                "ai_feedback": "Proceed to onboarding."
            }
        },
        "safe_key": "safe_value"
    }

    with tenant_context(auth_mode="true"):
        log_entry = AuditLog(
            actor_id=None,
            actor_type="CANDIDATE",
            action="candidate.created",
            ip_address="127.0.0.1",
            metadata_json=metadata
        )
        db_session.add(log_entry)
        db_session.commit()
        db_session.refresh(log_entry)

    # 2. Run the GDPR Right-to-Be-Forgotten pseudonymization pass
    scrubbed_count = pseudonymize_audit_logs(db_session, candidate_id, candidate_email)
    assert scrubbed_count == 1
    
    # Reload from DB and verify
    db_session.expire(log_entry)
    with tenant_context(auth_mode="true"):
        reloaded = db_session.scalar(select(AuditLog).where(AuditLog.id == log_entry.id))
        
        # Verify timestamps, actor references, and log integrity remain intact!
        assert reloaded.actor_id is None
        assert reloaded.actor_type == "CANDIDATE"
        assert reloaded.action == "candidate.created"
        assert reloaded.timestamp is not None
        
        # Verify the IP address column on AuditLog is scrubbed!
        assert reloaded.ip_address == "[PSEUDONYMIZED]"
        
        # Verify recursive JSONB scrubbing of all 31 fields!
        meta_res = reloaded.metadata_json
        profile = meta_res["candidate"]["profile"]
        
        for field in DEFAULT_SCRUB_LIST:
            assert profile[field] == "[PSEUDONYMIZED]"
            
        # Verify safe key integrity remains perfectly preserved!
        assert meta_res["safe_key"] == "safe_value"


def test_job_lifecycle_audit_events(api_client, db_session):
    """Verify that job.created, job.edited, and job.archived events are logged."""
    # 1. Register a recruiter
    register_payload = {
        "company_name": "Job Corp",
        "email": "job_recruiter@test.com",
        "password": "super-secure-password-123",
        "full_name": "Job Recruiter"
    }
    resp = api_client.post("/api/v1/auth/register", json=register_payload)
    reg_data = resp.json()
    token = reg_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    company_id = uuid.UUID(reg_data["user"]["company_id"])

    # Mark recruiter as email verified
    with tenant_context(auth_mode="true"):
        user = db_session.get(User, uuid.UUID(reg_data["user"]["id"]))
        if user:
            user.email_verified = True
            db_session.add(user)
            db_session.commit()

    # 2. Create Job
    job_payload = {
        "title": "Software Engineer",
        "department": "Engineering",
        "description": "Write code",
        "status": "open",
        "start_date": "2026-06-01"
    }
    job_resp = api_client.post("/api/v1/jobs", json=job_payload, headers=headers)
    assert job_resp.status_code == 201
    job_data = job_resp.json()
    job_id = uuid.UUID(job_data["id"])

    # Verify job.created
    with tenant_context(auth_mode="true"):
        logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "job.created")
        ).all()
        assert len(logs) == 1
        assert logs[0].metadata_json["title"] == "Software Engineer"
        assert logs[0].company_id == company_id

    # 3. Edit Job
    edit_payload = {"title": "Senior Software Engineer"}
    edit_resp = api_client.patch(f"/api/v1/jobs/{job_id}", json=edit_payload, headers=headers)
    assert edit_resp.status_code == 200

    # Verify job.edited
    with tenant_context(auth_mode="true"):
        logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "job.edited").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(logs) >= 1
        assert logs[0].metadata_json["title"]["new"] == "Senior Software Engineer"

    # 4. Archive Job via delete endpoint
    del_resp = api_client.delete(f"/api/v1/jobs/{job_id}", headers=headers)
    assert del_resp.status_code == 204

    # Verify job.archived
    with tenant_context(auth_mode="true"):
        logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "job.archived").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(logs) >= 1
        assert logs[0].metadata_json["status"]["new"] == "closed"


def test_candidate_and_override_lifecycle_events(api_client, db_session):
    """Verify that creating a candidate, changing stage, hired, rejected, and overrides are logged."""
    # 1. Register a recruiter and get auth token
    register_payload = {
        "company_name": "Candidate Corp",
        "email": "candidate_recruiter@test.com",
        "password": "super-secure-password-123",
        "full_name": "Candidate Recruiter"
    }
    resp = api_client.post("/api/v1/auth/register", json=register_payload)
    assert resp.status_code == 201
    reg_data = resp.json()
    token = reg_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    company_id = uuid.UUID(reg_data["user"]["company_id"])

    # Mark recruiter as email verified
    with tenant_context(auth_mode="true"):
        user = db_session.get(User, uuid.UUID(reg_data["user"]["id"]))
        if user:
            user.email_verified = True
            db_session.add(user)
            db_session.commit()

    # Create a job first so we can apply to it
    with tenant_context(auth_mode="true"):
        job = Job(
            company_id=company_id,
            title="SRE Engineer",
            department="Engineering",
            description="Fix things",
            status=JobStatus.OPEN
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

    # 2. Create Application / Candidate
    app_payload = {
        "job_id": str(job.id),
        "candidate_name": "John Candidate",
        "candidate_email": "john_candidate@test.com",
        "candidate_phone": "+1999999999",
        "source": "LinkedIn"
    }
    
    app_resp = api_client.post("/api/v1/applications", json=app_payload, headers=headers)
    assert app_resp.status_code == 201
    app_data = app_resp.json()
    application_id = uuid.UUID(app_data["id"])
    candidate_id = uuid.UUID(app_data["candidate_id"])

    # Verify candidate.created was recorded!
    with tenant_context(auth_mode="true"):
        logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "candidate.created")
        ).all()
        assert len(logs) == 1
        assert logs[0].actor_id == uuid.UUID(reg_data["user"]["id"])
        assert logs[0].company_id == company_id
        assert logs[0].metadata_json["email"] == "john_candidate@test.com"

    # 3. Patch Application (stage change and recruiter override)
    patch_payload = {"status": "screening"}
    patch_resp = api_client.patch(f"/api/v1/applications/{application_id}", json=patch_payload, headers=headers)
    assert patch_resp.status_code == 200
    
    # Verify stage_changed and recruiter_override
    with tenant_context(auth_mode="true"):
        override_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "ai.recruiter_override")
        ).all()
        assert len(override_logs) == 1
        assert override_logs[0].metadata_json["new_status"] == "screening"
        assert override_logs[0].metadata_json["old_status"] == "submitted"
        
        stage_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "candidate.stage_changed")
        ).all()
        assert len(stage_logs) == 1
        assert stage_logs[0].metadata_json["new_status"] == "screening"

    # 4. Hired transition
    patch_payload = {"status": "hired"}
    patch_resp = api_client.patch(f"/api/v1/applications/{application_id}", json=patch_payload, headers=headers)
    assert patch_resp.status_code == 200
    
    with tenant_context(auth_mode="true"):
        hired_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "candidate.hired")
        ).all()
        assert len(hired_logs) == 1

    # 5. Rejected transition
    patch_payload = {"status": "rejected"}
    patch_resp = api_client.patch(f"/api/v1/applications/{application_id}", json=patch_payload, headers=headers)
    assert patch_resp.status_code == 200
    
    with tenant_context(auth_mode="true"):
        rejected_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "candidate.rejected")
        ).all()
        assert len(rejected_logs) == 1


def test_ai_lifecycle_events(api_client, db_session):
    """Verify that ai.evaluation_started, match_score_generated, and evaluation_completed events are logged."""
    # 1. Mock process_candidate to return a standard result
    mock_result = {
        "candidate_data": {"name": "Test Candidate", "email": "candidate@test.com"},
        "screening_result": {},
        "scoring_result": {"total_score": 92, "overall_fit": "Excellent fit"},
        "decision_result": {"decision": "HIRE"},
        "communication_result": {},
    }
    
    valid_pdf_data = b"%PDF-1.4\n%%EOF"
    files = {"file": ("candidate_resume.pdf", valid_pdf_data, "application/pdf")}
    data = {
        "job_role": "Rust Engineer",
        "department": "Engineering",
        "job_description": "Write fast Rust programs"
    }

    with patch("server.process_candidate") as mock_process:
        mock_process.return_value = mock_result
        
        response = api_client.post("/api/recruit", files=files, data=data)
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify AI evaluation audit events were logged!
        with tenant_context(auth_mode="true"):
            started_logs = db_session.scalars(
                select(AuditLog).where(AuditLog.action == "ai.evaluation_started")
            ).all()
            assert len(started_logs) == 1
            assert started_logs[0].metadata_json["job_role"] == "Rust Engineer"
            evaluation_id = started_logs[0].metadata_json["evaluation_id"]
            
            score_logs = db_session.scalars(
                select(AuditLog).where(AuditLog.action == "ai.match_score_generated")
            ).all()
            assert len(score_logs) == 1
            assert score_logs[0].metadata_json["evaluation_id"] == evaluation_id
            assert score_logs[0].metadata_json["score"] == 92
            
            completed_logs = db_session.scalars(
                select(AuditLog).where(AuditLog.action == "ai.evaluation_completed")
            ).all()
            assert len(completed_logs) == 1
            
            # Verify strict compact storage constraints!
            meta = completed_logs[0].metadata_json
            assert meta["evaluation_id"] == evaluation_id
            assert meta["score"] == 92
            assert meta["recommendation"] == "HIRE"
            assert meta["model_version"] == "gemini-1.5-pro"
            assert "Excellent fit" in meta["summary"]
            # Ensure full rationales or LLM outputs are NOT stored!
            assert "ai_explanation" not in meta
            assert "ai_reasoning" not in meta
