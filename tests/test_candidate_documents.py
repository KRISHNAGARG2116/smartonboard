import pytest
import uuid
import io
import os
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from server import app
from db.session import get_db, tenant_context
from models import User, Company, Job, Application, Candidate, CandidateDocument, UserSession
from models.enums import UserRole, ApplicationStatus, JobStatus
from core.security import create_access_token

@pytest.fixture
def test_setup(db_session):
    with tenant_context(auth_mode="true"):
        company = Company(name="Test Company", slug="test-company")
        db_session.add(company)
        db_session.commit()

        candidate = User(
            email="candidate_doc@example.com",
            password_hash="hashed_password",
            full_name="Candidate Doc",
            role=UserRole.CANDIDATE,
            is_active=True
        )
        db_session.add(candidate)

        recruiter = User(
            email="recruiter_doc@example.com",
            password_hash="hashed_password",
            full_name="Recruiter Doc",
            role=UserRole.RECRUITER,
            company_id=company.id,
            is_active=True
        )
        db_session.add(recruiter)
        db_session.commit()

        job = Job(
            company_id=company.id,
            title="Test Job",
            description="Job description",
            status=JobStatus.OPEN
        )
        db_session.add(job)
        db_session.commit()

        cand_rec = Candidate(
            company_id=company.id,
            email=candidate.email,
            full_name=candidate.full_name
        )
        db_session.add(cand_rec)
        db_session.commit()

        app_record = Application(
            company_id=company.id,
            job_id=job.id,
            candidate_id=cand_rec.id,
            status=ApplicationStatus.SUBMITTED
        )
        db_session.add(app_record)
        db_session.commit()

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

def test_upload_and_list_documents(api_client, db_session, test_setup):
    headers = test_setup["headers"]
    app_id = str(test_setup["application"].id)

    # 1. Upload Document
    file_content = b"This is a mock pdf document content for verification."
    file_obj = io.BytesIO(file_content)

    data = {
        "application_id": app_id,
        "document_type": "passport"
    }
    files = {
        "file": ("passport.pdf", file_obj, "application/pdf")
    }

    resp = api_client.post("/api/v1/candidate/documents/upload", data=data, files=files, headers=headers)
    assert resp.status_code == 200
    res_json = resp.json()
    assert res_json["status"] == "pending"
    assert "id" in res_json
    assert "checksum" in res_json
    assert "verification_reason_code" in res_json
    assert res_json["mime_type"] == "application/pdf"

    # Check file exists in mock local storage
    with tenant_context(auth_mode="true"):
        doc_id = uuid.UUID(res_json["id"])
        doc = db_session.get(CandidateDocument, doc_id)
        assert doc is not None
        assert os.path.exists(doc.storage_path)

        # Cleanup file
        if os.path.exists(doc.storage_path):
            os.remove(doc.storage_path)

    # 2. List Documents
    resp = api_client.get("/api/v1/candidate/documents", headers=headers)
    assert resp.status_code == 200
    docs = resp.json()
    assert len(docs) == 1
    assert docs[0]["document_type"] == "passport"
    assert "checksum" in docs[0]
    assert "verification_reason_code" in docs[0]
    assert docs[0]["mime_type"] == "application/pdf"

