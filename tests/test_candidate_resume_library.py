import io
import uuid
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from server import app
from db.session import get_db, tenant_context
from models import User, CandidateProfile, CandidateResume
from core.malware import EICAR_SIGNATURE

@pytest.fixture(autouse=True)
def mock_parser():
    with patch("agents.resume_parser.resume_parser_agent") as mock_agent:
        def side_effect(file_bytes):
            content_str = file_bytes.decode("utf-8", errors="ignore")
            skills = []
            if "Python" in content_str:
                skills.extend(["Python", "SQLAlchemy", "Docker"])
            elif "Java" in content_str:
                skills.extend(["Java", "Spring"])
            
            summary = "Mocked Summary"
            if "Summary:" in content_str:
                summary = content_str.split("Summary:")[1].strip()
            
            return {
                "name": "John Candidate",
                "email": "cand_resume_test@example.com",
                "phone": "+1234567890",
                "skills": skills,
                "experience_years": 5,
                "education": "BS CS",
                "previous_roles": ["Software Engineer"],
                "summary": summary
            }
        mock_agent.side_effect = side_effect
        yield mock_agent


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


def test_candidate_resume_library_lifecycle(api_client, db_session):
    # 1. Register candidate user
    reg_payload = {
        "email": "cand_resume_test@example.com",
        "password": "securepassword123",
        "full_name": "John Candidate",
    }
    resp = api_client.post("/api/v1/auth/register/candidate", json=reg_payload)
    assert resp.status_code == 201
    cand_data = resp.json()
    token = cand_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Mark candidate verified
    cand_user_id = uuid.UUID(cand_data["user"]["id"])
    with tenant_context(auth_mode="true"):
        profile = db_session.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == cand_user_id)
        )
        if profile:
            profile.email_verified = True
            profile.phone_verified = True
            db_session.add(profile)
            db_session.commit()

    # 2. Upload active resume (Text file - valid TXT signature)
    file_content = b"This is a professional resume for John Candidate.\nSkills: Python, SQLAlchemy, Docker.\nSummary: Experienced developer."
    files = {"file": ("resume.txt", io.BytesIO(file_content), "text/plain")}
    
    # Celery is eager, so this runs synchronously and promotes the file immediately
    resp = api_client.post("/api/v1/auth/candidate/resumes/upload", files=files, headers=headers)
    assert resp.status_code == 202
    res_data = resp.json()
    assert "task_id" in res_data
    assert "quarantine_file_id" in res_data

    # Verify resume in database
    db_session.expire_all()
    with tenant_context(auth_mode="true"):
        resumes = db_session.scalars(
            select(CandidateResume).where(CandidateResume.user_id == uuid.UUID(cand_data["user"]["id"]))
        ).all()
        assert len(resumes) == 1
        resume1 = resumes[0]
        assert resume1.filename == "resume.txt"
        assert resume1.is_active is True

        # Verify profile updated
        profile = db_session.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == uuid.UUID(cand_data["user"]["id"]))
        )
        assert profile is not None
        assert "Python" in profile.skills or len(profile.skills) > 0 or profile.summary != ""

    # 3. Upload a second resume
    files2 = {"file": ("resume2.txt", io.BytesIO(b"Second resume content.\nSkills: Java, Spring.\nSummary: Java developer."), "text/plain")}
    resp = api_client.post("/api/v1/auth/candidate/resumes/upload", files=files2, headers=headers)
    assert resp.status_code == 202

    # Verify second resume is active and first is now inactive
    db_session.expire_all()
    with tenant_context(auth_mode="true"):
        resumes = db_session.scalars(
            select(CandidateResume)
            .where(CandidateResume.user_id == uuid.UUID(cand_data["user"]["id"]))
            .order_by(CandidateResume.created_at.desc())
        ).all()
        assert len(resumes) == 2
        assert resumes[0].filename == "resume2.txt"
        assert resumes[0].is_active is True
        assert resumes[1].filename == "resume.txt"
        assert resumes[1].is_active is False

    # 4. Upload a third resume
    files3 = {"file": ("resume3.txt", io.BytesIO(b"Third resume content."), "text/plain")}
    resp = api_client.post("/api/v1/auth/candidate/resumes/upload", files=files3, headers=headers)
    assert resp.status_code == 202

    # 5. Attempt 4th upload - should be rejected by limits check
    files4 = {"file": ("resume4.txt", io.BytesIO(b"Fourth resume content."), "text/plain")}
    resp = api_client.post("/api/v1/auth/candidate/resumes/upload", files=files4, headers=headers)
    assert resp.status_code == 400
    assert "Maximum limit of 3 resumes reached" in resp.json()["detail"]

    # 6. Toggle active resume
    db_session.expire_all()
    with tenant_context(auth_mode="true"):
        target_resume_id = resumes[1].id # first uploaded resume (resume.txt)
    
    resp = api_client.post(f"/api/v1/auth/candidate/resumes/{target_resume_id}/toggle-active", headers=headers)
    assert resp.status_code == 200

    # Verify toggle in DB
    db_session.expire_all()
    with tenant_context(auth_mode="true"):
        resume1_db = db_session.get(CandidateResume, target_resume_id)
        assert resume1_db.is_active is True

    # 7. Delete active resume
    resp = api_client.delete(f"/api/v1/auth/candidate/resumes/{target_resume_id}", headers=headers)
    assert resp.status_code == 200

    # Verify deletion and automatic promotion of another resume to active
    db_session.expire_all()
    with tenant_context(auth_mode="true"):
        deleted = db_session.get(CandidateResume, target_resume_id)
        assert deleted is None
        
        remaining_resumes = db_session.scalars(
            select(CandidateResume).where(CandidateResume.user_id == uuid.UUID(cand_data["user"]["id"]))
        ).all()
        assert len(remaining_resumes) == 2
        # Verify one of them is marked active
        assert any(r.is_active for r in remaining_resumes)


def test_candidate_resume_upload_validations(api_client, db_session):
    # Register candidate user
    reg_payload = {
        "email": "cand_val_test@example.com",
        "password": "securepassword123",
        "full_name": "Validation Candidate",
    }
    resp = api_client.post("/api/v1/auth/register/candidate", json=reg_payload)
    assert resp.status_code == 201
    cand_data = resp.json()
    token = cand_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Mark candidate verified
    cand_user_id = uuid.UUID(cand_data["user"]["id"])
    with tenant_context(auth_mode="true"):
        profile = db_session.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == cand_user_id)
        )
        if profile:
            profile.email_verified = True
            profile.phone_verified = True
            db_session.add(profile)
            db_session.commit()

    # 1. Invalid signature (Empty text or binary with png extension/signature)
    invalid_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR..."
    files = {"file": ("resume.png", io.BytesIO(invalid_bytes), "image/png")}
    resp = api_client.post("/api/v1/auth/candidate/resumes/upload", files=files, headers=headers)
    assert resp.status_code == 400
    assert "Invalid file signature" in resp.json()["detail"]

    # 2. Malware upload (EICAR)
    files_mal = {"file": ("malware.txt", io.BytesIO(EICAR_SIGNATURE), "text/plain")}
    resp = api_client.post("/api/v1/auth/candidate/resumes/upload", files=files_mal, headers=headers)
    assert resp.status_code == 400
    assert "Malware detected" in resp.json()["detail"]

    # 3. File too large (> 5 MB)
    large_bytes = b"x" * (5 * 1024 * 1024 + 100)
    files_lg = {"file": ("large.txt", io.BytesIO(large_bytes), "text/plain")}
    resp = api_client.post("/api/v1/auth/candidate/resumes/upload", files=files_lg, headers=headers)
    assert resp.status_code == 413
