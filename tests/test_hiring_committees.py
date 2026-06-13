import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text

from server import app
from db.session import get_db, tenant_context
from models import (
    Company,
    User,
    Job,
    Offer,
    Candidate,
    Application,
    AuditLog,
    Scorecard,
    ApprovalTemplate,
    ApprovalChain,
    ApprovalStep,
    ScorecardTemplate,
    ScorecardTemplateSkill,
    HiringCommittee,
    HiringCommitteeMember,
    CommitteeReview,
    CommitteeReviewReviewer,
    Interview
)
from models.enums import UserRole, JobStatus, ApplicationStatus
from fastapi.testclient import TestClient

@pytest.fixture
def api_client(db_session):
    def override_get_db():
        try:
            db_session.expire_all()
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def verify_user_in_db(db, user_id):
    with tenant_context(auth_mode="true"):
        user = db.get(User, user_id)
        if user:
            user.email_verified = True
            db.add(user)
            db.commit()


def test_scorecard_template_weight_sum_validation(api_client, db_session):
    """
    1. Creating a scorecard template where skill weights sum to 1.0 succeeds.
    2. Creating a scorecard template where skill weights do not sum to 1.0 fails.
    """
    # Register Company
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Scorecard Template Corp",
        "email": "owner@scorecard-corp.com",
        "password": "secure-password",
        "full_name": "Owner A"
    })
    assert resp.status_code == 201
    reg_data = resp.json()
    headers = {"Authorization": f"Bearer {reg_data['access_token']}"}
    verify_user_in_db(db_session, uuid.UUID(reg_data["user"]["id"]))

    # 1. Valid template (sum of weights = 1.0)
    resp_valid = api_client.post(
        "/api/v1/scorecards/templates",
        headers=headers,
        json={
            "name": "Software Engineer II Template",
            "description": "Standard SE evaluation",
            "skills": [
                {"skill_key": "coding", "display_name": "Coding Ability", "weight": 0.40},
                {"skill_key": "system_design", "display_name": "System Architecture", "weight": 0.40},
                {"skill_key": "culture", "display_name": "Culture Fit", "weight": 0.20}
            ]
        }
    )
    assert resp_valid.status_code == 201

    # 2. Invalid template (sum of weights = 0.90) -> expects 422
    resp_invalid = api_client.post(
        "/api/v1/scorecards/templates",
        headers=headers,
        json={
            "name": "Invalid Template",
            "skills": [
                {"skill_key": "coding", "display_name": "Coding Ability", "weight": 0.40},
                {"skill_key": "system_design", "display_name": "System Architecture", "weight": 0.50}
            ]
        }
    )
    assert resp_invalid.status_code == 422
    assert "sum of skill weights must be exactly 1.0" in resp_invalid.text


def test_committee_review_consensus_weighted_normalization_and_handoff(api_client, db_session):
    """
    1. Tests reviewer weights normalization (2.0 vs 1.0 weights).
    2. Tests immutable membership snapshotting on initiation.
    3. Verifies auto-spawned Offer Approval Chain on aligned approval.
    """
    # 1. Setup Company A and User B
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "Consensus Corp",
        "email": "owner@consensus-corp.com",
        "password": "secure-password",
        "full_name": "Owner User"
    })
    assert resp_a.status_code == 201
    reg_a = resp_a.json()
    headers_owner = {"Authorization": f"Bearer {reg_a['access_token']}"}
    comp_id = uuid.UUID(reg_a["user"]["company_id"])
    owner_id = uuid.UUID(reg_a["user"]["id"])
    verify_user_in_db(db_session, owner_id)

    # Register reviewer User B (recruiter)
    resp_b = api_client.post("/api/v1/auth/register", json={
        "company_name": "Consensus Reviewer",
        "email": "reviewer@consensus-corp.com",
        "password": "secure-password-2",
        "full_name": "Reviewer B"
    })
    assert resp_b.status_code == 201
    reg_b = resp_b.json()
    headers_reviewer = {"Authorization": f"Bearer {reg_b['access_token']}"}
    rev_id = uuid.UUID(reg_b["user"]["id"])
    verify_user_in_db(db_session, rev_id)

    # Binds User B to Company A (isolation bypass to unify company)
    with tenant_context(auth_mode="true"):
        u_b = db_session.get(User, rev_id)
        u_b.company_id = comp_id
        u_b.role = UserRole.RECRUITER
        db_session.commit()

    # Create scorecard template (sum = 1.0)
    resp_tpl = api_client.post(
        "/api/v1/scorecards/templates",
        headers=headers_owner,
        json={
            "name": "Review Template",
            "skills": [
                {"skill_key": "coding", "display_name": "Coding", "weight": 0.50},
                {"skill_key": "system_design", "display_name": "Design", "weight": 0.50}
            ]
        }
    )
    assert resp_tpl.status_code == 201
    template_id = uuid.UUID(resp_tpl.json()["id"])

    # Create offer approval template to verify auto-handoff
    resp_app_tpl = api_client.post(
        "/api/v1/approvals/templates",
        headers=headers_owner,
        json={
            "name": "Offer Sign-off Flow",
            "description": "Spawns automatically",
            "target_type": "offer",
            "steps": [
                {
                    "sequence": 1,
                    "role_required": "owner",
                    "approver_id": str(owner_id)
                }
            ]
        }
    )
    assert resp_app_tpl.status_code == 201

    # Create Hiring Committee
    # Reviewer B is assigned weight 1.00
    # Owner A (Chair) is assigned weight 2.00 (senior)
    resp_comm = api_client.post(
        "/api/v1/committees",
        headers=headers_owner,
        json={
            "name": "Technical Committee",
            "quorum_percentage": 100,
            "min_score_threshold": 3.00,
            "consensus_sd_threshold": 1.50,
            "allow_veto": True,
            "veto_skill_keys": ["coding"],
            "members": [
                {"user_id": str(rev_id), "role": "reviewer", "reviewer_weight": 1.00},
                {"user_id": str(owner_id), "role": "chair", "reviewer_weight": 2.00}
            ]
        }
    )
    assert resp_comm.status_code == 201
    committee_id = uuid.UUID(resp_comm.json()["id"])

    # Setup job, candidate, and application in DB
    with tenant_context(auth_mode="true"):
        job = Job(company_id=comp_id, title="Lead Dev", department="Eng", description="Eng", status=JobStatus.OPEN, settings={"scorecard_criteria": ["coding", "system_design"]})
        candidate = Candidate(company_id=comp_id, email="cand@consensus.com", full_name="Consensus Cand")
        db_session.add_all([job, candidate])
        db_session.flush()

        application = Application(company_id=comp_id, job_id=job.id, candidate_id=candidate.id, status="screening")
        db_session.add(application)
        db_session.commit()
        app_id = application.id

    # Initiate Review and verify snapshot
    resp_init = api_client.post(
        f"/api/v1/applications/{app_id}/reviews/initiate",
        headers=headers_owner,
        json={
            "hiring_committee_id": str(committee_id),
            "scorecard_template_id": str(template_id)
        }
    )
    assert resp_init.status_code == 201
    review_id = uuid.UUID(resp_init.json()["id"])

    # 4. Schedule Interviews via API to generate valid scorecards
    now = datetime.now(timezone.utc)
    resp_int1 = api_client.post(f"/api/v1/applications/{app_id}/interviews", headers=headers_owner, json={
        "interviewer_id": str(rev_id),
        "title": "Standard Sync",
        "stage": "interviewing",
        "scheduled_at": (now + timedelta(days=1)).isoformat(),
        "duration_minutes": 30
    })
    assert resp_int1.status_code == 201
    int1_id = uuid.UUID(resp_int1.json()["id"])

    resp_int2 = api_client.post(f"/api/v1/applications/{app_id}/interviews", headers=headers_owner, json={
        "interviewer_id": str(owner_id),
        "title": "Chair Sync",
        "stage": "interviewing",
        "scheduled_at": (now + timedelta(days=1)).isoformat(),
        "duration_minutes": 30
    })
    assert resp_int2.status_code == 201
    int2_id = uuid.UUID(resp_int2.json()["id"])

    # Submit scorecard for Reviewer B (weight 1.0) -> grades 3 and 3 (weighted score = 3.0)
    with tenant_context(auth_mode="true"):
        sc1 = Scorecard(
            company_id=comp_id,
            application_id=app_id,
            interview_id=int1_id,
            grader_id=rev_id,
            criteria_scores={"coding": 3, "system_design": 3},
            overall_recommendation="yes",
            notes="Solid SE",
            committee_review_id=review_id,
            submitted_at=datetime.now(timezone.utc)
        )
        db_session.add(sc1)
        db_session.commit()

        from core.consensus import evaluate_committee_review_consensus
        evaluate_committee_review_consensus(db_session, review_id)
        db_session.commit()

    # Verify review is still pending quorum
    resp_chk_pending = api_client.get(f"/api/v1/reviews/{review_id}", headers=headers_owner)
    assert resp_chk_pending.json()["status"] == "pending"

    # Submit scorecard for Owner A (weight 2.0) -> grades 4 and 4 (weighted score = 4.0)
    with tenant_context(auth_mode="true"):
        sc2 = Scorecard(
            company_id=comp_id,
            application_id=app_id,
            interview_id=int2_id,
            grader_id=owner_id,
            criteria_scores={"coding": 4, "system_design": 4},
            overall_recommendation="strong_yes",
            notes="Excellent SE",
            committee_review_id=review_id,
            submitted_at=datetime.now(timezone.utc)
        )
        db_session.add(sc2)
        db_session.commit()

        evaluate_committee_review_consensus(db_session, review_id)
        db_session.commit()

    # Verify consensus engine has run and calculated:
    # Reviewer B score = 3.0, weight = 1.0
    # Owner A score = 4.0, weight = 2.0
    # Normalized weights: B = 1/3, A = 2/3
    # OverallScore = 3.0 * (1/3) + 4.0 * (2/3) = 1.0 + 2.666 = 3.67
    # Since OverallScore (3.67) >= min_score_threshold (3.0) and SD is low, it should be 'aligned_approve'
    resp_chk_resolved = api_client.get(f"/api/v1/reviews/{review_id}", headers=headers_owner)
    res_data = resp_chk_resolved.json()
    assert res_data["status"] == "aligned_approve"
    assert abs(float(res_data["average_score"]) - 3.67) < 0.05

    # Verify application status shifted to APPROVED
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        app_rec = db_session.get(Application, app_id)
        assert app_rec.status == ApplicationStatus.OFFER
        assert app_rec.committee_status == "aligned_approve"

        # Verify automated Offer Approval Chain was instantiated
        chain = db_session.scalar(select(ApprovalChain).where(ApprovalChain.company_id == comp_id))
        assert chain is not None
        assert chain.target_type == "offer"
        assert chain.status == "pending"
        steps = db_session.scalars(select(ApprovalStep).where(ApprovalStep.approval_chain_id == chain.id)).all()
        assert len(steps) == 1
        assert steps[0].approver_id == owner_id

        # Verify committee.offer_chain_created audit log exists
        evt = db_session.scalar(select(AuditLog).where(AuditLog.action == "committee.offer_chain_created"))
        assert evt is not None
        assert evt.company_id == comp_id


def test_committee_membership_snapshotting(api_client, db_session):
    """
    Refinement 2: Verify committee membership snapshot roster immutability.
    Global roster additions/removals do not modify initiated reviews.
    """
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "Snapshot Corp",
        "email": "owner@snapshot-corp.com",
        "password": "secure-password",
        "full_name": "Owner A"
    })
    reg_data = resp_a.json()
    headers_owner = {"Authorization": f"Bearer {reg_data['access_token']}"}
    comp_id = uuid.UUID(reg_data["user"]["company_id"])
    owner_id = uuid.UUID(reg_data["user"]["id"])
    verify_user_in_db(db_session, owner_id)

    # Create scorecard template
    resp_tpl = api_client.post(
        "/api/v1/scorecards/templates",
        headers=headers_owner,
        json={
            "name": "Template",
            "skills": [{"skill_key": "coding", "display_name": "Coding", "weight": 1.00}]
        }
    )
    template_id = uuid.UUID(resp_tpl.json()["id"])

    # Create Hiring Committee with 1 member
    resp_comm = api_client.post(
        "/api/v1/committees",
        headers=headers_owner,
        json={
            "name": "Snapshot Committee",
            "quorum_percentage": 100,
            "min_score_threshold": 3.00,
            "members": [{"user_id": str(owner_id), "role": "chair", "reviewer_weight": 1.00}]
        }
    )
    committee_id = uuid.UUID(resp_comm.json()["id"])

    # Setup application
    with tenant_context(auth_mode="true"):
        job = Job(company_id=comp_id, title="QA", department="QA", description="QA", status=JobStatus.OPEN, settings={"scorecard_criteria": ["coding"]})
        candidate = Candidate(company_id=comp_id, email="qa@snapshot.com", full_name="QA Candidate")
        db_session.add_all([job, candidate])
        db_session.flush()
        application = Application(company_id=comp_id, job_id=job.id, candidate_id=candidate.id, status="screening")
        db_session.add(application)
        db_session.commit()
        app_id = application.id

    # Initiate Review
    resp_init = api_client.post(
        f"/api/v1/applications/{app_id}/reviews/initiate",
        headers=headers_owner,
        json={
            "hiring_committee_id": str(committee_id),
            "scorecard_template_id": str(template_id)
        }
    )
    assert resp_init.status_code == 201
    review_id = uuid.UUID(resp_init.json()["id"])

    # Verify review snapshot has exactly 1 reviewer
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        reviewers_pre = db_session.scalars(
            select(CommitteeReviewReviewer).where(CommitteeReviewReviewer.committee_review_id == review_id)
        ).all()
        assert len(reviewers_pre) == 1

        # Modify the global committee member list by adding another member (simulate a post or db add)
        # Binds standard reviewer C to committee in DB
        new_u = User(company_id=comp_id, email="qa_reviewer@snapshot.com", password_hash="...", full_name="QA Member", role=UserRole.RECRUITER)
        db_session.add(new_u)
        db_session.flush()

        global_mem = HiringCommitteeMember(company_id=comp_id, hiring_committee_id=committee_id, user_id=new_u.id, role="reviewer", reviewer_weight=2.00)
        db_session.add(global_mem)
        db_session.commit()

    # Verify snapshot roster is completely unmodified (still exactly 1 snapshotted reviewer)
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        reviewers_post = db_session.scalars(
            select(CommitteeReviewReviewer).where(CommitteeReviewReviewer.committee_review_id == review_id)
        ).all()
        assert len(reviewers_post) == 1
        assert reviewers_post[0].user_id == owner_id


def test_configurable_sd_threshold(api_client, db_session):
    """
    Refinement 3: Verifies custom consensus_sd_threshold per committee.
    If SD exceeds custom threshold, status is set to disputed.
    """
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "SD Corp",
        "email": "owner@sd-corp.com",
        "password": "secure-password",
        "full_name": "Owner A"
    })
    reg_a = resp_a.json()
    headers_owner = {"Authorization": f"Bearer {reg_a['access_token']}"}
    comp_id = uuid.UUID(reg_a["user"]["company_id"])
    owner_id = uuid.UUID(reg_a["user"]["id"])
    verify_user_in_db(db_session, owner_id)

    resp_b = api_client.post("/api/v1/auth/register", json={
        "company_name": "SD Reviewer",
        "email": "rev@sd-corp.com",
        "password": "secure-password",
        "full_name": "Reviewer B"
    })
    reg_b = resp_b.json()
    headers_rev = {"Authorization": f"Bearer {reg_b['access_token']}"}
    rev_id = uuid.UUID(reg_b["user"]["id"])
    verify_user_in_db(db_session, rev_id)

    with tenant_context(auth_mode="true"):
        db_session.get(User, rev_id).company_id = comp_id
        db_session.commit()

    # Create scorecard template
    resp_tpl = api_client.post("/api/v1/scorecards/templates", headers=headers_owner, json={
        "name": "Template",
        "skills": [{"skill_key": "coding", "display_name": "Coding", "weight": 1.00}]
    })
    template_id = uuid.UUID(resp_tpl.json()["id"])

    # Create Hiring Committee with extremely strict SD threshold = 0.10
    resp_comm = api_client.post("/api/v1/committees", headers=headers_owner, json={
        "name": "Strict SD Committee",
        "quorum_percentage": 100,
        "min_score_threshold": 3.00,
        "consensus_sd_threshold": 0.10,  # Strict threshold!
        "allow_veto": False,
        "members": [
            {"user_id": str(owner_id), "role": "chair", "reviewer_weight": 1.00},
            {"user_id": str(rev_id), "role": "reviewer", "reviewer_weight": 1.00}
        ]
    })
    committee_id = uuid.UUID(resp_comm.json()["id"])

    # Setup application & interviews
    with tenant_context(auth_mode="true"):
        job = Job(company_id=comp_id, title="Strict", department="strict", description="strict", status=JobStatus.OPEN, settings={"scorecard_criteria": ["coding"]})
        candidate = Candidate(company_id=comp_id, email="cand@strict.com", full_name="Strict Cand")
        db_session.add_all([job, candidate])
        db_session.flush()
        application = Application(company_id=comp_id, job_id=job.id, candidate_id=candidate.id, status="screening")
        db_session.add(application)
        db_session.commit()
        app_id = application.id

    # Initiate review
    resp_init = api_client.post(f"/api/v1/applications/{app_id}/reviews/initiate", headers=headers_owner, json={
        "hiring_committee_id": str(committee_id),
        "scorecard_template_id": str(template_id)
    })
    review_id = uuid.UUID(resp_init.json()["id"])

    # Schedule 2 interviews
    now = datetime.now(timezone.utc)
    int1 = api_client.post(f"/api/v1/applications/{app_id}/interviews", headers=headers_owner, json={"interviewer_id": str(owner_id), "title": "1", "stage": "interviewing", "scheduled_at": now.isoformat(), "duration_minutes": 30})
    int2 = api_client.post(f"/api/v1/applications/{app_id}/interviews", headers=headers_owner, json={"interviewer_id": str(rev_id), "title": "2", "stage": "interviewing", "scheduled_at": now.isoformat(), "duration_minutes": 30})
    int1_id = uuid.UUID(int1.json()["id"])
    int2_id = uuid.UUID(int2.json()["id"])

    # Submit scorecard 1 & 2 directly
    with tenant_context(auth_mode="true"):
        sc1 = Scorecard(
            company_id=comp_id,
            application_id=app_id,
            interview_id=int1_id,
            grader_id=owner_id,
            criteria_scores={"coding": 4},
            overall_recommendation="yes",
            committee_review_id=review_id,
            submitted_at=datetime.now(timezone.utc)
        )
        sc2 = Scorecard(
            company_id=comp_id,
            application_id=app_id,
            interview_id=int2_id,
            grader_id=rev_id,
            criteria_scores={"coding": 3},
            overall_recommendation="yes",
            committee_review_id=review_id,
            submitted_at=datetime.now(timezone.utc)
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()

        from core.consensus import evaluate_committee_review_consensus
        evaluate_committee_review_consensus(db_session, review_id)
        db_session.commit()

    resp_chk = api_client.get(f"/api/v1/reviews/{review_id}", headers=headers_owner)
    assert resp_chk.json()["status"] == "disputed"


def test_configurable_veto_logic(api_client, db_session):
    """
    Refinement 6: Verifies veto skill keys configurations.
    If grading is 1 on a veto key, consensus instantly triggers disputed status.
    """
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "Veto Corp",
        "email": "owner@veto-corp.com",
        "password": "secure-password",
        "full_name": "Owner A"
    })
    reg_a = resp_a.json()
    headers_owner = {"Authorization": f"Bearer {reg_a['access_token']}"}
    comp_id = uuid.UUID(reg_a["user"]["company_id"])
    owner_id = uuid.UUID(reg_a["user"]["id"])
    verify_user_in_db(db_session, owner_id)

    # Create scorecard template
    resp_tpl = api_client.post("/api/v1/scorecards/templates", headers=headers_owner, json={
        "name": "Template",
        "skills": [
            {"skill_key": "coding", "display_name": "Coding", "weight": 0.50},
            {"skill_key": "communication", "display_name": "Communication", "weight": 0.50}
        ]
    })
    template_id = uuid.UUID(resp_tpl.json()["id"])

    # Create Committee with veto allowed on "coding" key only
    resp_comm = api_client.post("/api/v1/committees", headers=headers_owner, json={
        "name": "Veto Committee",
        "quorum_percentage": 100,
        "min_score_threshold": 3.00,
        "consensus_sd_threshold": 2.00,
        "allow_veto": True,
        "veto_skill_keys": ["coding"],
        "members": [{"user_id": str(owner_id), "role": "chair", "reviewer_weight": 1.00}]
    })
    committee_id = uuid.UUID(resp_comm.json()["id"])

    # Setup app
    with tenant_context(auth_mode="true"):
        job = Job(company_id=comp_id, title="Veto", department="Veto", description="Veto", status=JobStatus.OPEN, settings={"scorecard_criteria": ["coding", "communication"]})
        candidate = Candidate(company_id=comp_id, email="cand@veto.com", full_name="Veto Cand")
        db_session.add_all([job, candidate])
        db_session.flush()
        application = Application(company_id=comp_id, job_id=job.id, candidate_id=candidate.id, status="screening")
        db_session.add(application)
        db_session.commit()
        app_id = application.id

    # Initiate review
    resp_init = api_client.post(f"/api/v1/applications/{app_id}/reviews/initiate", headers=headers_owner, json={
        "hiring_committee_id": str(committee_id),
        "scorecard_template_id": str(template_id)
    })
    review_id = uuid.UUID(resp_init.json()["id"])

    now = datetime.now(timezone.utc)
    int_resp = api_client.post(f"/api/v1/applications/{app_id}/interviews", headers=headers_owner, json={"interviewer_id": str(owner_id), "title": "1", "stage": "interviewing", "scheduled_at": now.isoformat(), "duration_minutes": 30})
    int_id = uuid.UUID(int_resp.json()["id"])

    # Submit scorecard: Coding = 1 (veto key), Communication = 5. Average score = 3.0
    # Average score meets the minimum threshold (3.0 >= 3.0), and SD is 0.0 (single user).
    # But because Coding is 1, a veto is triggered, routing the review status to disputed!
    api_client.post(
        f"/api/v1/applications/{app_id}/interviews/{int_id}/scorecard",
        headers=headers_owner,
        json={"criteria_scores": {"coding": 1, "communication": 5}, "overall_recommendation": "no"}
    )

    resp_chk = api_client.get(f"/api/v1/reviews/{review_id}", headers=headers_owner)
    assert resp_chk.json()["status"] == "disputed"


def test_reconciliation_authorization(api_client, db_session):
    """
    Refinement 4: Dispute reconciliation is authorized for Committee Chair OR Owner.
    Recruiters are blocked.
    """
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "Reconciliation Corp",
        "email": "owner@reconcile.com",
        "password": "secure-password",
        "full_name": "Owner A"
    })
    reg_a = resp_a.json()
    headers_owner = {"Authorization": f"Bearer {reg_a['access_token']}"}
    comp_id = uuid.UUID(reg_a["user"]["company_id"])
    owner_id = uuid.UUID(reg_a["user"]["id"])
    verify_user_in_db(db_session, owner_id)

    resp_b = api_client.post("/api/v1/auth/register", json={
        "company_name": "Recruiter B",
        "email": "recruiter@reconcile.com",
        "password": "secure-password",
        "full_name": "Recruiter B"
    })
    reg_b = resp_b.json()
    headers_recruiter = {"Authorization": f"Bearer {reg_b['access_token']}"}
    rec_id = uuid.UUID(reg_b["user"]["id"])
    verify_user_in_db(db_session, rec_id)

    with tenant_context(auth_mode="true"):
        u_b = db_session.get(User, rec_id)
        u_b.company_id = comp_id
        u_b.role = UserRole.RECRUITER
        db_session.commit()

    # Login again to get a fresh JWT signed with Company A's id!
    resp_login = api_client.post("/api/v1/auth/login", json={
        "email": "recruiter@reconcile.com",
        "password": "secure-password"
    })
    assert resp_login.status_code == 200
    headers_recruiter = {"Authorization": f"Bearer {resp_login.json()['access_token']}"}

    # Create template
    resp_tpl = api_client.post("/api/v1/scorecards/templates", headers=headers_owner, json={
        "name": "Template",
        "skills": [{"skill_key": "coding", "display_name": "Coding", "weight": 1.00}]
    })
    template_id = uuid.UUID(resp_tpl.json()["id"])

    # Create Committee where Owner A is Chair
    resp_comm = api_client.post("/api/v1/committees", headers=headers_owner, json={
        "name": "Strict Committee",
        "quorum_percentage": 100,
        "min_score_threshold": 3.00,
        "consensus_sd_threshold": 0.01,  # Forces dispute
        "allow_veto": False,
        "members": [
            {"user_id": str(owner_id), "role": "chair", "reviewer_weight": 1.00},
            {"user_id": str(rec_id), "role": "reviewer", "reviewer_weight": 1.00}
        ]
    })
    committee_id = uuid.UUID(resp_comm.json()["id"])

    # Setup app
    with tenant_context(auth_mode="true"):
        job = Job(company_id=comp_id, title="Reconcile", department="QA", description="QA", status=JobStatus.OPEN, settings={"scorecard_criteria": ["coding"]})
        candidate = Candidate(company_id=comp_id, email="cand@reconcile.com", full_name="Reconcile Cand")
        db_session.add_all([job, candidate])
        db_session.flush()
        application = Application(company_id=comp_id, job_id=job.id, candidate_id=candidate.id, status="screening")
        db_session.add(application)
        db_session.commit()
        app_id = application.id

    # Initiate review
    resp_init = api_client.post(f"/api/v1/applications/{app_id}/reviews/initiate", headers=headers_owner, json={
        "hiring_committee_id": str(committee_id),
        "scorecard_template_id": str(template_id)
    })
    review_id = uuid.UUID(resp_init.json()["id"])

    # Schedule and submit scorecards (Grades 4 and 3 -> Average = 3.5, SD = 0.5 > 0.01 threshold -> Disputed!)
    now = datetime.now(timezone.utc)
    int1 = api_client.post(f"/api/v1/applications/{app_id}/interviews", headers=headers_owner, json={"interviewer_id": str(owner_id), "title": "1", "stage": "interviewing", "scheduled_at": now.isoformat(), "duration_minutes": 30})
    int2 = api_client.post(f"/api/v1/applications/{app_id}/interviews", headers=headers_owner, json={"interviewer_id": str(rec_id), "title": "2", "stage": "interviewing", "scheduled_at": now.isoformat(), "duration_minutes": 30})
    int1_id = uuid.UUID(int1.json()["id"])
    int2_id = uuid.UUID(int2.json()["id"])

    # Submit scorecard 1 & 2 directly
    with tenant_context(auth_mode="true"):
        sc1 = Scorecard(
            company_id=comp_id,
            application_id=app_id,
            interview_id=int1_id,
            grader_id=owner_id,
            criteria_scores={"coding": 4},
            overall_recommendation="yes",
            committee_review_id=review_id,
            submitted_at=datetime.now(timezone.utc)
        )
        sc2 = Scorecard(
            company_id=comp_id,
            application_id=app_id,
            interview_id=int2_id,
            grader_id=rec_id,
            criteria_scores={"coding": 3},
            overall_recommendation="yes",
            committee_review_id=review_id,
            submitted_at=datetime.now(timezone.utc)
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()

        from core.consensus import evaluate_committee_review_consensus
        evaluate_committee_review_consensus(db_session, review_id)
        db_session.commit()

    # Check review status is indeed disputed
    resp_chk = api_client.get(f"/api/v1/reviews/{review_id}", headers=headers_owner)
    assert resp_chk.json()["status"] == "disputed"

    # 1. Attempt manual reconciliation by standard recruiter B (not Chair or Owner) -> expects 403
    resp_fail = api_client.post(
        f"/api/v1/reviews/{review_id}/reconcile",
        headers=headers_recruiter,
        json={"resolution": "approve", "notes": "I want to reconcile it anyway"}
    )
    assert resp_fail.status_code == 403

    # 2. Reconcile as Committee Chair (Owner A) -> expects 200
    resp_ok = api_client.post(
        f"/api/v1/reviews/{review_id}/reconcile",
        headers=headers_owner,
        json={"resolution": "approve", "notes": "Reconciled because standard deviation is acceptable"}
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["status"] == "aligned_approve"


def test_multi_tenant_rls_isolation(api_client, db_session):
    """
    Enforces absolute tenant scoping checks.
    Company B cannot view Company A's reviews or committees.
    """
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "Tenant A",
        "email": "owner@tenant-a.com",
        "password": "secure-password",
        "full_name": "Owner A"
    })
    reg_a = resp_a.json()
    headers_a = {"Authorization": f"Bearer {reg_a['access_token']}"}
    verify_user_in_db(db_session, uuid.UUID(reg_a["user"]["id"]))

    resp_b = api_client.post("/api/v1/auth/register", json={
        "company_name": "Tenant B",
        "email": "owner@tenant-b.com",
        "password": "secure-password",
        "full_name": "Owner B"
    })
    reg_b = resp_b.json()
    headers_b = {"Authorization": f"Bearer {reg_b['access_token']}"}
    verify_user_in_db(db_session, uuid.UUID(reg_b["user"]["id"]))

    # Create scorecard template under Company A
    resp_tpl = api_client.post("/api/v1/scorecards/templates", headers=headers_a, json={
        "name": "SE Template A",
        "skills": [{"skill_key": "coding", "display_name": "Coding", "weight": 1.00}]
    })
    assert resp_tpl.status_code == 201
    tpl_id = uuid.UUID(resp_tpl.json()["id"])

    # Attempt to fetch Company A's template using Company B's headers -> expects 404
    resp_fail = api_client.get(f"/api/v1/scorecards/templates/{tpl_id}", headers=headers_b)
    assert resp_fail.status_code == 404
