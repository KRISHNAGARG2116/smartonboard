import pytest
import uuid
from datetime import datetime, timezone, timedelta, date
from fastapi.testclient import TestClient
from sqlalchemy import select
from server import app
from db.session import get_db, tenant_context
from models import User, Company, Job, Application, Candidate, Offer, UserSession
from models.enums import UserRole, ApplicationStatus, JobStatus
from core.security import create_access_token

@pytest.fixture
def test_setup(db_session):
    with tenant_context(auth_mode="true"):
        company = Company(name="Test Company", slug="test-company")
        db_session.add(company)
        db_session.commit()

        candidate = User(
            email="candidate_offer@example.com",
            password_hash="hashed_password",
            full_name="Candidate Offer",
            role=UserRole.CANDIDATE,
            is_active=True
        )
        db_session.add(candidate)

        recruiter = User(
            email="recruiter_offer@example.com",
            password_hash="hashed_password",
            full_name="Recruiter Offer",
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

        # Create offer
        offer = Offer(
            company_id=company.id,
            application_id=app_record.id,
            salary=120000.0,
            equity_grant="0.1%",
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

def test_list_and_download_offer(api_client, db_session, test_setup):
    headers = test_setup["headers"]
    offer_id = str(test_setup["offer"].id)

    # List offers
    resp = api_client.get("/api/v1/candidate/offers", headers=headers)
    assert resp.status_code == 200
    offers = resp.json()
    assert len(offers) == 1
    assert offers[0]["salary"] == 120000.0

    # Download offer PDF
    resp = api_client.get(f"/api/v1/candidate/offers/{offer_id}/download", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"

def test_accept_offer(api_client, db_session, test_setup):
    headers = test_setup["headers"]
    offer_id = str(test_setup["offer"].id)
    offer = test_setup["offer"]

    payload = {
        "client_updated_at": offer.updated_at.isoformat()
    }
    resp = api_client.post(f"/api/v1/candidate/offers/{offer_id}/accept", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Assert offer status is updated in db
    with tenant_context(auth_mode="true"):
        db_session.commit()
        db_session.expire_all()
        updated_offer = db_session.get(Offer, offer.id)
        assert updated_offer.status == "accepted"
