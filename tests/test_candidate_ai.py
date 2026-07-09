import pytest
import uuid
from datetime import datetime, timezone, timedelta, date
from fastapi.testclient import TestClient
from server import app
from db.session import get_db, tenant_context
from models import User, Company, Job, Application, Candidate, Offer, CandidateChatSession, CandidateAIChatHistory, UserSession
from models.enums import UserRole, ApplicationStatus, JobStatus
from core.security import create_access_token
from unittest.mock import patch

@pytest.fixture
def test_setup(db_session):
    with tenant_context(auth_mode="true"):
        company = Company(name="Test Company", slug="test-company")
        db_session.add(company)
        db_session.commit()

        candidate = User(
            email="candidate_ai@example.com",
            password_hash="hashed_password",
            full_name="Candidate AI",
            role=UserRole.CANDIDATE,
            is_active=True
        )
        db_session.add(candidate)

        recruiter = User(
            email="recruiter_ai@example.com",
            password_hash="hashed_password",
            full_name="Recruiter AI",
            role=UserRole.RECRUITER,
            company_id=company.id,
            is_active=True
        )
        db_session.add(recruiter)
        db_session.commit()

        job = Job(
            company_id=company.id,
            title="AI Engineer",
            description="Build cool LLM pipelines.",
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

        # Create offer
        offer = Offer(
            company_id=company.id,
            application_id=app_record.id,
            salary=150000.0,
            equity_grant="0.2%",
            start_date=date.today() + timedelta(days=14),
            expires_at=date.today() + timedelta(days=7),
            status="sent"
        )
        db_session.add(offer)
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
        "offer": offer,
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

@patch("core.intelligence.GenerativeIntelligenceService.candidate_chat")
@patch("core.intelligence.GenerativeIntelligenceService.interview_preparation")
@patch("core.intelligence.GenerativeIntelligenceService.offer_explanation")
def test_candidate_ai_endpoints(
    mock_offer_explanation,
    mock_interview_preparation,
    mock_candidate_chat,
    api_client,
    db_session,
    test_setup
):
    headers = test_setup["headers"]
    app_id = str(test_setup["application"].id)
    offer_id = str(test_setup["offer"].id)

    # Mock return values
    mock_candidate_chat.return_value = "Sure, I can help you with that."
    mock_interview_preparation.return_value = "Prepare for coding and systems design."
    mock_offer_explanation.return_value = "This offer has base and equity components."

    # 1. AI Chat Session and Message Routing
    chat_payload = {
        "message": "What is the status of my application?",
        "session_id": None
    }
    resp = api_client.post("/api/v1/candidate/ai/chat", json=chat_payload, headers=headers)
    assert resp.status_code == 200
    chat_data = resp.json()
    assert "reply" in chat_data
    assert chat_data["reply"] == "Sure, I can help you with that."
    assert "session_id" in chat_data

    # 2. AI Interview Preparation Guide
    prep_payload = {
        "application_id": app_id
    }
    resp = api_client.post("/api/v1/candidate/ai/interview-prep", json=prep_payload, headers=headers)
    assert resp.status_code == 200
    prep_data = resp.json()
    assert "guide" in prep_data
    assert prep_data["guide"] == "Prepare for coding and systems design."

    # 3. AI Offer Explanation Guide
    offer_payload = {
        "offer_id": offer_id
    }
    resp = api_client.post("/api/v1/candidate/ai/offer-explanation", json=offer_payload, headers=headers)
    assert resp.status_code == 200
    offer_data = resp.json()
    assert "explanation" in offer_data
    assert offer_data["explanation"] == "This offer has base and equity components."
