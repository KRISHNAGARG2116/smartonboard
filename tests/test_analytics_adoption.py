import pytest
import uuid
import os
import csv
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
    Application,
    Candidate,
    Scorecard,
    Interview,
    AuditLog
)
from models.insight_interaction import AIInsightInteraction
from models.export_job import ExportJob
from models.recruiter_insight import AIRecruiterInsight
from models.enums import UserRole, JobStatus, ApplicationStatus
from celery_worker import generate_analytics_export_async, cleanup_expired_exports_async


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


def test_recruiter_decision_outcomes_and_effectiveness(api_client, db_session):
    """
    Verify complete Phase 3 analytics, outcomes snapshotting, and effectiveness logic:
    - POST /intelligence/applications/{id}/decide-outcome records outcome decisions
      (ACCEPTED, DISMISSED, OVERRIDDEN) and logs snaps.
    - GET /analytics/effectiveness computes correct accuracy metrics and averages match scores from AuditLogs.
    - GET /analytics/adoption tracks viewed counts and recruiter agreement benchmarks.
    - GET /analytics/fairness logs anonymized fairness aggregates.
    """
    # 1. Register Company A (Recruiter A)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Analytics adoption Corp",
        "email": "recruiter_adoption@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Recruiter A"
    })
    assert resp.status_code == 201
    reg_a = resp.json()
    token_a = reg_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    comp_a_id = uuid.UUID(reg_a["user"]["company_id"])
    recruiter_a_id = uuid.UUID(reg_a["user"]["id"])

    # 2. Setup Job, Candidate, Application in Company A
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_a_id)})
        
        job_a = Job(
            company_id=comp_a_id,
            title="Analytics SRE",
            department="Operations",
            description="Optimize analytics databases.",
            status=JobStatus.OPEN,
        )
        db_session.add(job_a)
        db_session.flush()

        candidate_a = Candidate(
            company_id=comp_a_id,
            email="candidate_adoption@test.com",
            full_name="Candidate Adoption"
        )
        db_session.add(candidate_a)
        db_session.flush()

        app_a = Application(
            company_id=comp_a_id,
            job_id=job_a.id,
            candidate_id=candidate_a.id,
            status=ApplicationStatus.HIRED,
            source="Referral"
        )
        db_session.add(app_a)
        db_session.flush()
        app_a_id = app_a.id

        # Insert a pre-existing completed Hiring Recommendation insight
        insight = AIRecruiterInsight(
            company_id=comp_a_id,
            application_id=app_a_id,
            insight_type="hiring_recommendation",
            content="# Hiring Recommendation: HIRE\nWe recommend HIRE.",
            generation_status="COMPLETED",
            checksum="dummy_checksum",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            model_version="llama-3.3-70b-versatile"
        )
        db_session.add(insight)
        
        # Log a dummy match score in AuditLogs
        log_audit = AuditLog(
            company_id=comp_a_id,
            actor_type="SYSTEM",
            action="ai.match_score_generated",
            metadata_json={"evaluation_id": str(app_a_id), "score": 92.5},
            timestamp=datetime.now(timezone.utc)
        )
        db_session.add(log_audit)
        db_session.commit()

    # 3. Post a recruiter decide-outcome decision: ACCEPTED
    outcome_resp = api_client.post(
        f"/api/v1/intelligence/applications/{app_a_id}/decide-outcome",
        json={
            "insight_type": "hiring_recommendation",
            "decision": "ACCEPTED"
        },
        headers=headers_a
    )
    assert outcome_resp.status_code == 200
    assert outcome_resp.json()["success"] is True

    # 4. Check AI Effectiveness Endpoint
    eff_resp = api_client.get("/api/v1/analytics/effectiveness", headers=headers_a)
    assert eff_resp.status_code == 200
    eff_data = eff_resp.json()
    assert eff_data["metrics"]["total_evaluations"] == 1
    assert eff_data["metrics"]["ai_recommended_hired_rate"] == 1.0
    assert eff_data["metrics"]["false_positive_rate"] == 0.0
    assert eff_data["metrics"]["average_match_score_hired"] == 92.5

    # 5. Check Recruiter Adoption Metrics Endpoint
    adopt_resp = api_client.get("/api/v1/analytics/adoption", headers=headers_a)
    assert adopt_resp.status_code == 200
    adopt_data = adopt_resp.json()
    # Expect 1 recruiter entry matching Recruiter A
    assert len(adopt_data["recruiter_engagement"]) == 1
    assert adopt_data["recruiter_engagement"][0]["recruiter_id"] == str(recruiter_a_id)
    assert adopt_data["recruiter_engagement"][0]["agreement_rate"] == 1.0

    # 6. Check Fairness Metrics Endpoint (anonymized metrics, no protected tags)
    fair_resp = api_client.get("/api/v1/analytics/fairness", headers=headers_a)
    assert fair_resp.status_code == 200
    fair_data = fair_resp.json()
    assert fair_data["average_match_score"] == 92.5
    assert fair_data["override_rate"] == 0.0


def test_asynchronous_export_lifecycle(api_client, db_session):
    """
    Verify async exporter lifecycle, downloads, expirations, and RLS:
    - POST /analytics/export creates a job and returns 202 Accepted with job_id.
    - background Celery generate task creates the file on disk.
    - GET /analytics/export/download/{id} downloads the completed file.
    - cleanup task removes expired download files and marks jobs EXPIRED.
    """
    # 1. Register Company
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Export queue Corp",
        "email": "recruiter_export@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Recruiter A"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    comp_id = uuid.UUID(resp.json()["user"]["company_id"])

    # 2. Add some dummy interaction metrics
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_id)})
        
        job = Job(company_id=comp_id, title="QA", department="QA", description="Test")
        db_session.add(job)
        db_session.flush()

        candidate = Candidate(company_id=comp_id, email="qa@test.com", full_name="QA Candidate")
        db_session.add(candidate)
        db_session.flush()

        app = Application(company_id=comp_id, job_id=job.id, candidate_id=candidate.id, status=ApplicationStatus.SCREENING)
        db_session.add(app)
        db_session.flush()

        inter = AIInsightInteraction(
            company_id=comp_id,
            user_id=uuid.UUID(resp.json()["user"]["id"]),
            application_id=app.id,
            insight_type="candidate_summary",
            interaction_type="VIEWED"
        )
        db_session.add(inter)
        db_session.commit()

    # 3. Request Asynchronous Export
    export_resp = api_client.post("/api/v1/analytics/export", headers=headers)
    assert export_resp.status_code == 202
    job_id = export_resp.json()["export_id"]

    # Since Eager mode is active, the Celery task generate_analytics_export_async executed synchronously inside delay()
    # 4. Check Status
    status_resp = api_client.get(f"/api/v1/analytics/export/status/{job_id}", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "COMPLETED"

    # 5. Download generated CSV
    download_resp = api_client.get(f"/api/v1/analytics/export/download/{job_id}", headers=headers)
    assert download_resp.status_code == 200
    content = download_resp.text
    assert "Interaction ID" in content
    assert "candidate_summary" in content

    # 6. Verify scheduled TTL expired exports cleanup
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        # Set job expires_at to yesterday to simulate expired TTL
        db_job = db_session.scalar(select(ExportJob).where(ExportJob.id == uuid.UUID(job_id)))
        assert db_job is not None
        db_job.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()

        # Verify generated export file exists before cleanup
        file_path = db_job.file_path
        assert os.path.exists(file_path)

        # Run cleanup task
        cleanup_expired_exports_async()

        # Verify file is deleted and status set to EXPIRED
        assert not os.path.exists(file_path)
        db_session.expire_all()
        db_job_after = db_session.scalar(select(ExportJob).where(ExportJob.id == uuid.UUID(job_id)))
        assert db_job_after.status == "EXPIRED"
        assert db_job_after.file_path is None


def test_gdpr_candidate_deletion_cascades_interactions(api_client, db_session):
    """
    Verify GDPR cascade purging for newly introduced tables:
    - Deleting candidate cascade-deletes related applications.
    - Cascade automatically cleans up related `ai_insight_interactions` via foreign key triggers.
    """
    # 1. Register Company Owner (Only Owners can invoke delete)
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "GDPR Cascade Corp",
        "email": "owner_cascade@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Owner Cascade"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    comp_id = uuid.UUID(resp.json()["user"]["company_id"])
    owner_id = uuid.UUID(resp.json()["user"]["id"])

    # 2. Setup Candidate & Application & Metrics
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_id)})
        
        job = Job(company_id=comp_id, title="Developer", department="Engineering", description="Code")
        db_session.add(job)
        db_session.flush()

        candidate = Candidate(company_id=comp_id, email="gdpr@test.com", full_name="GDPR Candidate")
        db_session.add(candidate)
        db_session.flush()
        cand_id = candidate.id

        app = Application(company_id=comp_id, job_id=job.id, candidate_id=cand_id, status=ApplicationStatus.SCREENING)
        db_session.add(app)
        db_session.flush()
        app_id = app.id

        inter = AIInsightInteraction(
            company_id=comp_id,
            user_id=owner_id,
            application_id=app_id,
            insight_type="candidate_summary",
            interaction_type="VIEWED"
        )
        db_session.add(inter)
        db_session.commit()

    # 3. Call GDPR delete candidate route
    del_resp = api_client.post(
        f"/api/v1/candidates/{cand_id}/delete",
        json={"confirm": True},
        headers=headers
    )
    assert del_resp.status_code == 204

    # 4. Verify RLS cascade purged interactions table
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        # Verify candidate is deleted
        assert db_session.scalar(select(Candidate).where(Candidate.id == cand_id)) is None
        # Verify application is deleted
        assert db_session.scalar(select(Application).where(Application.id == app_id)) is None
        # Verify AIInsightInteraction cascade purged
        assert db_session.scalar(select(AIInsightInteraction).where(AIInsightInteraction.application_id == app_id)) is None
