import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import select, delete
from pathlib import Path

# Force Celery to execute tasks synchronously and in-process for tests
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

from db.session import tenant_context
from fastapi.testclient import TestClient
from server import app
from db.session import get_db
from models import Company, User, Job, Candidate, Application, CandidateEmbedding, AuditLog
from models.enums import UserRole, JobStatus, ApplicationStatus, CompanyStatus
from celery_worker import process_resume_async, GroqRateLimitError
from core.celery_app import celery_app


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


def test_celery_config_result_retention():
    """Verify that Celery is configured with 24-hour task result retention."""
    assert celery_app.conf.result_expires == 86400
    assert celery_app.conf.task_always_eager is True


def test_async_task_dispatch_and_polling(api_client, db_session):
    """Verify that POST /applications/async promotes files, schedules Celery tasks, and GET status works under RLS."""
    # 1. Register Company A
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Async Corp",
        "email": "owner_async@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Async Owner"
    })
    assert resp.status_code == 201
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    comp_a_id = uuid.UUID(reg_a["user"]["company_id"])

    # 2. Register Company B for isolation checks
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Async Isolation",
        "email": "owner_async_iso@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Async Iso Owner"
    })
    assert resp.status_code == 201
    token_b = resp.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Create a Job in Company A
    with tenant_context(auth_mode="true"):
        job = Job(
            company_id=comp_a_id,
            title="Senior Async Engineer",
            department="Engineering",
            description="Build scalable Celery queues.",
            status=JobStatus.OPEN,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        job_id = job.id

    # Mock the underlying LangGraph process_candidate execution
    mock_result = {
        "candidate_data": {
            "name": "Jane Async",
            "email": "jane.async@example.com",
            "phone": "9876543210"
        },
        "screening_result": {},
        "scoring_result": {"total_score": 88, "overall_fit": "Strong fit"},
        "decision_result": {"decision": "HIRE"},
        "communication_result": {}
    }

    valid_pdf_data = b"%PDF-1.4\n%%EOF"
    files = {"file": ("resume.pdf", valid_pdf_data, "application/pdf")}
    data = {"job_id": str(job_id)}

    with patch("celery_worker.process_candidate") as mock_process, \
         patch("core.signature.extract_text_from_file_bytes") as mock_extract:
        mock_process.return_value = mock_result
        mock_extract.return_value = "Jane's resume content text."

        # 4. Dispatch the upload via POST /api/v1/applications/async
        dispatch_resp = api_client.post("/api/v1/applications/async", files=files, data=data, headers=headers_a)
        assert dispatch_resp.status_code == 202
        dispatch_data = dispatch_resp.json()
        assert "task_id" in dispatch_data
        task_id = dispatch_data["task_id"]

        # 5. Poll the status via GET /api/v1/applications/async/status/{task_id}
        status_resp = api_client.get(f"/api/v1/applications/async/status/{task_id}", headers=headers_a)
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["status"] == "COMPLETED"
        assert status_data["result"]["success"] is True
        assert status_data["result"]["score"] == 88

        # 6. Tenant Isolation Check: Company B must receive 404/403 or fail to read Company A's task status
        with tenant_context(tenant_id=str(comp_a_id)):
            candidate_a = db_session.scalar(select(Candidate).where(Candidate.email == "jane.async@example.com"))
            assert candidate_a is not None

        # Under Company B's database context, Candidate A is invisible
        with tenant_context(tenant_id=str(resp.json()["user"]["company_id"])):
            candidate_hidden = db_session.scalar(select(Candidate).where(Candidate.email == "jane.async@example.com"))
            assert candidate_hidden is None


def test_celery_task_idempotency(db_session):
    """Verify that multiple task invocations (retries/duplicate runs) are completely idempotent."""
    with tenant_context(auth_mode="true"):
        company = Company(name="Idempotence Co", slug="idem-co", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        job = Job(
            company_id=company.id,
            title="SRE",
            department="Operations",
            description="Enforce idempotency.",
            status=JobStatus.OPEN,
        )
        db_session.add(job)
        db_session.commit()

    mock_result = {
        "candidate_data": {
            "name": "Repeat Candidate",
            "email": "repeat@example.com",
            "phone": "555-5555"
        },
        "screening_result": {},
        "scoring_result": {"total_score": 90},
        "decision_result": {"decision": "HIRE"},
        "communication_result": {}
    }

    # Save a mock resume file to verify reading works inside the task
    storage_dir = Path(__file__).resolve().parent.parent / "storage" / "uploads" / str(company.id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    mock_file = storage_dir / "resume_mock.pdf"
    mock_file.write_bytes(b"%PDF-1.4\n%%EOF")

    relative_file_path = f"uploads/{company.id}/resume_mock.pdf"
    evaluation_id = str(uuid.uuid4())

    with patch("celery_worker.process_candidate") as mock_process, \
         patch("core.signature.extract_text_from_file_bytes") as mock_extract:
        mock_process.return_value = mock_result
        mock_extract.return_value = "Resume text content for idempotency checks.\n\nChunk two text."

        # First task execution
        result_1 = process_resume_async(relative_file_path, str(company.id), str(job.id), evaluation_id)
        assert result_1["success"] is True

        # Second task execution (simulating duplicate trigger or retry)
        result_2 = process_resume_async(relative_file_path, str(company.id), str(job.id), evaluation_id)
        assert result_2["success"] is True

        # Verify that ONLY a single Candidate record exists for this email
        with tenant_context(tenant_id=str(company.id)):
            candidates = db_session.scalars(select(Candidate).where(Candidate.email == "repeat@example.com")).all()
            assert len(candidates) == 1
            cand_id = candidates[0].id

            # Verify that ONLY a single Application record exists
            applications = db_session.scalars(select(Application).where(Application.candidate_id == cand_id)).all()
            assert len(applications) == 1

            # Verify CandidateEmbedding count remains correct (2 chunks splitted by \n\n)
            embeddings = db_session.scalars(
                select(CandidateEmbedding).where(CandidateEmbedding.candidate_id == cand_id)
            ).all()
            assert len(embeddings) == 2


def test_celery_task_failures_and_failed_audit_event(db_session):
    """Verify that permanent task failures log the ai.evaluation_failed audit event containing correct metadata."""
    with tenant_context(auth_mode="true"):
        company = Company(name="Failure Co", slug="fail-co", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        job = Job(
            company_id=company.id,
            title="Engineer",
            department="Engineering",
            description="Testing failures.",
            status=JobStatus.OPEN,
        )
        db_session.add(job)
        db_session.commit()

    # Save a mock resume file to verify reading works inside the task
    storage_dir = Path(__file__).resolve().parent.parent / "storage" / "uploads" / str(company.id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    mock_file = storage_dir / "resume_fail.pdf"
    mock_file.write_bytes(b"%PDF-1.4\n%%EOF")

    relative_file_path = f"uploads/{company.id}/resume_fail.pdf"
    evaluation_id = str(uuid.uuid4())

    with patch("celery_worker.process_candidate") as mock_process:
        # Inject terminal failure
        mock_process.side_effect = ValueError("Terminal API Disconnection Error")

        # Run task, expecting exception to bubble up
        with pytest.raises(ValueError, match="Terminal API Disconnection Error"):
            process_resume_async(relative_file_path, str(company.id), str(job.id), evaluation_id)

        # Verify compliance event: ai.evaluation_failed was emitted
        with tenant_context(auth_mode="true"):
            failed_logs = db_session.scalars(
                select(AuditLog).where(AuditLog.action == "ai.evaluation_failed").order_by(AuditLog.timestamp.desc())
            ).all()
            assert len(failed_logs) >= 1
            metadata = failed_logs[0].metadata_json
            assert metadata["evaluation_id"] == evaluation_id
            assert metadata["error_type"] == "ValueError"



def test_celery_retry_backoff_trigger(db_session):
    """Verify that transient Groq rate limit errors trigger Celery task self.retry dispatches."""
    with tenant_context(auth_mode="true"):
        company = Company(name="Retry Co", slug="retry-co", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        job = Job(
            company_id=company.id,
            title="Engineer",
            department="Engineering",
            description="Testing retries.",
            status=JobStatus.OPEN,
        )
        db_session.add(job)
        db_session.commit()

    # Save a mock resume file to verify reading works inside the task
    storage_dir = Path(__file__).resolve().parent.parent / "storage" / "uploads" / str(company.id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    mock_file = storage_dir / "resume_retry.pdf"
    mock_file.write_bytes(b"%PDF-1.4\n%%EOF")

    relative_file_path = f"uploads/{company.id}/resume_retry.pdf"
    evaluation_id = str(uuid.uuid4())

    with patch("celery_worker.process_candidate") as mock_process, \
         patch("celery_worker.process_resume_async.retry") as mock_retry:
        
        # Inject transient rate limit error
        mock_process.side_effect = GroqRateLimitError("Rate limit exceeded 429")
        mock_retry.side_effect = Exception("Retry triggered")

        # Trigger task execution
        with pytest.raises(Exception, match="Retry triggered"):
            process_resume_async(relative_file_path, str(company.id), str(job.id), evaluation_id)

        # Assert task triggered retry
        mock_retry.assert_called_once()
        args, kwargs = mock_retry.call_args
        assert "exc" in kwargs
        assert isinstance(kwargs["exc"], GroqRateLimitError)
        assert "countdown" in kwargs
        assert kwargs["countdown"] > 0
