import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text
from fastapi.testclient import TestClient

from server import app
from db.session import get_db, tenant_context
from models import (
    Company,
    User,
    Job,
    Application,
    Candidate,
    CandidateStageTransition,
    FunnelAggregate,
    RecruiterProductivityAggregate,
    Interview,
    Offer,
)
from models.enums import UserRole, JobStatus, ApplicationStatus


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


def test_analytics_and_productivity_lifecycle(api_client, db_session):
    """
    Verify complete Phase 1 analytics flow:
    - Funnel metrics increments on transitions.
    - Recruiter productivity metrics increments on recruiter actions (review, advance, interview, offer).
    - Stage transition velocity and duration tracking.
    - Strict multi-tenant isolation.
    """
    # 1. Register Company A (Recruiter A)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Analytics Corp A",
        "email": "recruiter_a@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Recruiter A"
    })
    assert resp.status_code == 201
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    comp_a_id = uuid.UUID(reg_a["user"]["company_id"])
    recruiter_a_id = uuid.UUID(reg_a["user"]["id"])

    # Mark Recruiter A as email verified
    with tenant_context(auth_mode="true"):
        user_a = db_session.get(User, recruiter_a_id)
        if user_a:
            user_a.email_verified = True
            db_session.add(user_a)
            db_session.commit()

    # 2. Register Company B (Owner B - for tenant isolation checks)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Analytics Corp B",
        "email": "owner_b@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Owner B"
    })
    assert resp.status_code == 201
    reg_b = resp.json()
    token_b = reg_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    comp_b_id = uuid.UUID(reg_b["user"]["company_id"])
    owner_b_id = uuid.UUID(reg_b["user"]["id"])

    # Mark Owner B as email verified
    with tenant_context(auth_mode="true"):
        user_b = db_session.get(User, owner_b_id)
        if user_b:
            user_b.email_verified = True
            db_session.add(user_b)
            db_session.commit()

    # 3. Setup Job, Candidate, Application for Company A
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_a_id)})
        
        job_a = Job(
            company_id=comp_a_id,
            title="Software Architect",
            department="Engineering",
            description="Build scalable analytics platforms.",
            status=JobStatus.OPEN,
            settings={"scorecard_criteria": ["coding"]}
        )
        db_session.add(job_a)
        db_session.flush()
        job_a_id = job_a.id

        candidate_a = Candidate(
            company_id=comp_a_id,
            email="candidate_a@test.com",
            full_name="Candidate A"
        )
        db_session.add(candidate_a)
        db_session.flush()

        app_a = Application(
            company_id=comp_a_id,
            job_id=job_a_id,
            candidate_id=candidate_a.id,
            status=ApplicationStatus.SUBMITTED,
            source="Referral"
        )
        db_session.add(app_a)
        db_session.commit()
        app_a_id = app_a.id

    # 4. Advance application to SCREENING (Verify Stage Transition, Funnel, and Review/Advance Productivity)
    resp = api_client.patch(
        f"/api/v1/applications/{app_a_id}",
        json={"status": "screening"},
        headers=headers_a
    )
    assert resp.status_code == 200

    # Verify stage transition record is written
    with tenant_context(tenant_id=str(comp_a_id)):
        db_session.expire_all()
        transitions = db_session.scalars(
            select(CandidateStageTransition).where(CandidateStageTransition.application_id == app_a_id)
        ).all()
        assert len(transitions) == 1
        assert transitions[0].from_status == "submitted"
        assert transitions[0].to_status == "screening"
        assert transitions[0].actor_id == recruiter_a_id

        # Verify funnel aggregate counts
        funnel_submitted = db_session.scalar(
            select(FunnelAggregate).where(
                FunnelAggregate.job_id == job_a_id,
                FunnelAggregate.stage == "submitted"
            )
        )
        assert funnel_submitted is not None
        assert funnel_submitted.conversion_count == 1

        funnel_screening = db_session.scalar(
            select(FunnelAggregate).where(
                FunnelAggregate.job_id == job_a_id,
                FunnelAggregate.stage == "screening"
            )
        )
        assert funnel_screening is not None
        assert funnel_screening.candidate_count == 1

        # Verify recruiter productivity accomplishments
        prod = db_session.scalar(
            select(RecruiterProductivityAggregate).where(
                RecruiterProductivityAggregate.recruiter_id == recruiter_a_id
            )
        )
        assert prod is not None
        assert prod.applications_reviewed == 1
        assert prod.candidates_advanced == 1

    # 5. Check Analytics GET Funnel API Endpoint
    resp = api_client.get(
        f"/api/v1/analytics/funnel?job_id={job_a_id}",
        headers=headers_a
    )
    assert resp.status_code == 200
    funnel_data = resp.json()
    assert funnel_data["job_id"] == str(job_a_id)
    stages = {s["stage"]: s for s in funnel_data["stages"]}
    
    assert stages["submitted"]["conversion_count"] == 1
    assert stages["submitted"]["conversion_rate"] == 0.0 # because candidate_count is 0 for submitted in funnel
    assert stages["screening"]["candidate_count"] == 1
    assert stages["screening"]["conversion_rate"] == 0.0
    assert stages["screening"]["drop_off_count"] == 1

    # 6. Check Recruiter Productivity API Endpoint
    resp = api_client.get(
        "/api/v1/analytics/recruiter-productivity",
        headers=headers_a
    )
    assert resp.status_code == 200
    prod_data = resp.json()
    assert len(prod_data["metrics"]) == 1
    metric = prod_data["metrics"][0]
    assert metric["recruiter_id"] == str(recruiter_a_id)
    assert metric["applications_reviewed"] == 1
    assert metric["candidates_advanced"] == 1

    # 7. Schedule an Interview (Verify Interview Productivity and automatic SCREENING -> INTERVIEW transition)
    resp = api_client.post(
        f"/api/v1/applications/{app_a_id}/interviews",
        json={
            "interviewer_id": str(recruiter_a_id),
            "title": "Technical Deep Dive",
            "stage": "interview",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            "duration_minutes": 60
        },
        headers=headers_a
    )
    assert resp.status_code == 201

    # Verify transition screening -> interview occurred
    with tenant_context(tenant_id=str(comp_a_id)):
        db_session.expire_all()
        transitions = db_session.scalars(
            select(CandidateStageTransition)
            .where(CandidateStageTransition.application_id == app_a_id)
            .order_by(CandidateStageTransition.transitioned_at.asc())
        ).all()
        # Should have 2 transitions: submitted->screening, screening->interview
        assert len(transitions) == 2
        assert transitions[0].to_status == "screening"
        assert transitions[0].duration_seconds is not None  # Exited screening stage

        assert transitions[1].from_status == "screening"
        assert transitions[1].to_status == "interview"

        # Verify productivity increased for interview
        prod = db_session.scalar(
            select(RecruiterProductivityAggregate).where(
                RecruiterProductivityAggregate.recruiter_id == recruiter_a_id
            )
        )
        assert prod.interviews_scheduled == 1

    # 8. Check Stage transition velocity stats
    resp = api_client.get(
        f"/api/v1/analytics/velocity?job_id={job_a_id}",
        headers=headers_a
    )
    assert resp.status_code == 200
    velocity_data = resp.json()
    vel_stages = {s["stage"]: s for s in velocity_data["stages"]}
    assert vel_stages["screening"]["transition_count"] == 1
    assert vel_stages["screening"]["average_duration_seconds"] >= 0.0

    # 9. Create Offer (Verify Offer Productivity and automatic INTERVIEW -> OFFER transition)
    resp = api_client.post(
        f"/api/v1/applications/{app_a_id}/offers",
        json={
            "salary": 150000.00,
            "equity_grant": "5%",
            "start_date": (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        },
        headers=headers_a
    )
    assert resp.status_code == 201
    offer_id = resp.json()["id"]

    with tenant_context(tenant_id=str(comp_a_id)):
        db_session.expire_all()
        prod = db_session.scalar(
            select(RecruiterProductivityAggregate).where(
                RecruiterProductivityAggregate.recruiter_id == recruiter_a_id
            )
        )
        assert prod.offers_created == 1

    # 10. Accept Offer (Verify Accept Productivity and OFFER -> HIRED transition)
    # Transition to sent first, since we can only decide on sent offers
    with tenant_context(auth_mode="true"):
        offer = db_session.scalar(select(Offer).where(Offer.id == uuid.UUID(offer_id)))
        offer.status = "sent"
        db_session.commit()

    resp = api_client.post(
        f"/api/v1/applications/{app_a_id}/offers/decide",
        json={"decision": "signed"},
        headers=headers_a
    )
    assert resp.status_code == 200

    with tenant_context(tenant_id=str(comp_a_id)):
        db_session.expire_all()
        prod = db_session.scalar(
            select(RecruiterProductivityAggregate).where(
                RecruiterProductivityAggregate.recruiter_id == recruiter_a_id
            )
        )
        assert prod.offers_accepted == 1

        # Check final transition to hired exists
        transitions = db_session.scalars(
            select(CandidateStageTransition)
            .where(CandidateStageTransition.application_id == app_a_id)
            .order_by(CandidateStageTransition.transitioned_at.asc())
        ).all()
        # Transitions: submitted->screening, screening->interview, interview->offer, offer->hired
        assert len(transitions) == 4
        assert transitions[-1].from_status == "offer"
        assert transitions[-1].to_status == "hired"

    # 11. Multi-Tenant RLS Isolation checks
    # Try to access Company A analytics using Company B's headers
    resp = api_client.get(
        f"/api/v1/analytics/funnel?job_id={job_a_id}",
        headers=headers_b
    )
    # Since Job A belongs to Company A, RLS on job fetch inside funnel API should restrict B from viewing
    # Or, the job_id filter does a query on FunnelAggregate which is RLS isolated.
    # Therefore, Company B gets 0 candidate counts or empty funnel for Job A
    assert resp.status_code == 200
    funnel_b = resp.json()
    for s in funnel_b["stages"]:
        assert s["candidate_count"] == 0
        assert s["conversion_count"] == 0

    # Recruiter B gets empty recruiter productivity metrics
    resp = api_client.get(
        "/api/v1/analytics/recruiter-productivity",
        headers=headers_b
    )
    assert resp.status_code == 200
    assert len(resp.json()["metrics"]) == 0
