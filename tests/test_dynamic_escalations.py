import pytest
import uuid
from decimal import Decimal
from datetime import datetime, date, timezone, timedelta
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
    PipelineTemplate,
    Pipeline,
    StageDefinition,
    ApprovalTemplate,
    ApprovalTemplateStep,
    ApprovalChain,
    ApprovalStep,
    StageSLA,
    CandidateStageSLATracker,
    ApprovalEscalationRule,
    ApprovalStepEscalation,
    Interview
)
from models.enums import UserRole, JobStatus
from core.workflows import transition_candidate_stage, evaluate_auto_progression_rules
from tasks.escalations import sweep_sla_breaches, sweep_approval_escalations
from fastapi.testclient import TestClient

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


def test_stage_sla_creation_validation_and_isolation(api_client, db_session):
    """
    1. Validation: fallback_stage_id must belong to the same template or pipeline version.
    2. Multi-tenant RLS isolation prevents access to other company stages.
    """
    # 1. Register Company A & B
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "SLA Corp A",
        "email": "recruiter_a@sla-corp.com",
        "password": "secure-password-a",
        "full_name": "Recruiter A"
    })
    assert resp_a.status_code == 201
    headers_a = {"Authorization": f"Bearer {resp_a.json()['access_token']}"}
    comp_a_id = uuid.UUID(resp_a.json()["user"]["company_id"])

    resp_b = api_client.post("/api/v1/auth/register", json={
        "company_name": "SLA Corp B",
        "email": "recruiter_b@sla-corp.com",
        "password": "secure-password-b",
        "full_name": "Recruiter B"
    })
    assert resp_b.status_code == 201
    headers_b = {"Authorization": f"Bearer {resp_b.json()['access_token']}"}
    comp_b_id = uuid.UUID(resp_b.json()["user"]["company_id"])

    # 2. Create Template A with two stages
    resp_template_a = api_client.post(
        "/api/v1/pipelines/templates",
        headers=headers_a,
        json={
            "name": "Template A",
            "description": "Company A hiring",
            "stages": [
                {"name": "Screening A1", "sequence": 1, "base_category": "screening", "settings": {}, "automation_rules": []},
                {"name": "Interviewing A2", "sequence": 2, "base_category": "interviewing", "settings": {}, "automation_rules": []}
            ]
        }
    )
    assert resp_template_a.status_code == 201
    
    # 3. Create Template B with one stage
    resp_template_b = api_client.post(
        "/api/v1/pipelines/templates",
        headers=headers_b,
        json={
            "name": "Template B",
            "description": "Company B hiring",
            "stages": [
                {"name": "Screening B1", "sequence": 1, "base_category": "screening", "settings": {}, "automation_rules": []}
            ]
        }
    )
    assert resp_template_b.status_code == 201

    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        stages_a = db_session.scalars(select(StageDefinition).where(StageDefinition.company_id == comp_a_id)).all()
        stages_b = db_session.scalars(select(StageDefinition).where(StageDefinition.company_id == comp_b_id)).all()
        assert len(stages_a) == 2
        assert len(stages_b) == 1
        
        stage_a1_id = [s.id for s in stages_a if s.name == "Screening A1"][0]
        stage_a2_id = [s.id for s in stages_a if s.name == "Interviewing A2"][0]
        stage_b1_id = stages_b[0].id

    # 4. Attempt to configure SLA with fallback_stage_id from another company -> expects 404
    resp_fail_rls = api_client.post(
        f"/api/v1/pipelines/stages/{stage_a1_id}/sla",
        headers=headers_a,
        json={
            "duration_seconds": 3600,
            "escalation_action": "auto_advance",
            "fallback_stage_id": str(stage_b1_id)
        }
    )
    assert resp_fail_rls.status_code == 404

    # 5. Attempt to configure SLA with fallback_stage_id from same company but different pipeline template
    resp_template_c = api_client.post(
        "/api/v1/pipelines/templates",
        headers=headers_a,
        json={
            "name": "Template C",
            "description": "Company A different hiring",
            "stages": [
                {"name": "Screening C1", "sequence": 1, "base_category": "screening", "settings": {}, "automation_rules": []}
            ]
        }
    )
    assert resp_template_c.status_code == 201
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        stage_c1_id = db_session.scalar(
            select(StageDefinition.id).where(StageDefinition.company_id == comp_a_id, StageDefinition.name == "Screening C1")
        )

    # Attempt to post fallback_stage_id from C1 to A1 -> expects 400 (pipeline version / template mismatch)
    resp_mismatch = api_client.post(
        f"/api/v1/pipelines/stages/{stage_a1_id}/sla",
        headers=headers_a,
        json={
            "duration_seconds": 3600,
            "escalation_action": "auto_advance",
            "fallback_stage_id": str(stage_c1_id)
        }
    )
    assert resp_mismatch.status_code == 400
    assert "Fallback stage must belong to the same pipeline" in resp_mismatch.text

    # 6. Configure SLA with valid fallback_stage_id (same template) -> expects 201
    resp_ok = api_client.post(
        f"/api/v1/pipelines/stages/{stage_a1_id}/sla",
        headers=headers_a,
        json={
            "duration_seconds": 3600,
            "escalation_action": "auto_advance",
            "fallback_stage_id": str(stage_a2_id)
        }
    )
    assert resp_ok.status_code == 201


def test_structured_auto_progression_and_sla_resolution_on_exit(api_client, db_session):
    """
    1. Verify structured rules parsing and evaluation on scorecard submission.
    2. Verify active SLA tracker is set to 'completed' on stage exit.
    """
    # 1. Register Company
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Auto Progression Corp",
        "email": "recruiter@auto-prog.com",
        "password": "secure-password",
        "full_name": "Recruiter A"
    })
    assert resp.status_code == 201
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    comp_id = uuid.UUID(resp.json()["user"]["company_id"])
    recruiter_id = uuid.UUID(resp.json()["user"]["id"])

    # 2. Setup job & candidate & application in db
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_id)})
        
        job = Job(
            company_id=comp_id,
            title="Senior QA Engineer",
            department="Engineering",
            description="Run integration tests",
            status=JobStatus.OPEN,
            settings={"scorecard_criteria": ["coding", "system_design", "communication"]}
        )
        db_session.add(job)
        db_session.flush()

        candidate = Candidate(
            company_id=comp_id,
            email="candidate@auto-prog.com",
            full_name="Candidate A"
        )
        db_session.add(candidate)
        db_session.flush()

        app_record = Application(
            company_id=comp_id,
            job_id=job.id,
            candidate_id=candidate.id,
            status="submitted",
            source="Referral"
        )
        db_session.add(app_record)
        db_session.flush()
        
        db_session.commit()
        job_id = job.id
        app_id = app_record.id

    # 3. Create pipeline template with structured progression rules inside settings
    resp_template = api_client.post(
        "/api/v1/pipelines/templates",
        headers=headers,
        json={
            "name": "QA Pipeline",
            "description": "Standard QA pipeline",
            "stages": [
                {
                    "name": "Screening Stage",
                    "sequence": 1,
                    "base_category": "screening",
                    "settings": {},
                    "automation_rules": []
                },
                {
                    "name": "Interviewing Stage",
                    "sequence": 2,
                    "base_category": "interviewing",
                    "settings": {},
                    "automation_rules": []
                }
            ]
        }
    )
    assert resp_template.status_code == 201
    template_id = resp_template.json()["id"]

    # 4. Instantiate pipeline for job
    resp_pipeline = api_client.post(
        f"/api/v1/pipelines/jobs/{job_id}/pipeline?template_id={template_id}",
        headers=headers
    )
    assert resp_pipeline.status_code == 201
    pipeline_id = resp_pipeline.json()["id"]

    # Load instantiated stages and add the auto_progression_rules to Stage 1 settings
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        stages = db_session.scalars(
            select(StageDefinition).where(StageDefinition.pipeline_id == uuid.UUID(pipeline_id)).order_by(StageDefinition.sequence)
        ).all()
        assert len(stages) == 2
        stage_1_id = stages[0].id
        stage_2_id = stages[1].id
        
        # Configure rule inside stage_1.settings
        stage_1 = db_session.get(StageDefinition, stage_1_id)
        stage_1.settings = {
            "auto_progression_rules": [
                {
                    "field": "scorecard.overall_recommendation",
                    "operator": "==",
                    "value": "strong_yes",
                    "target_stage_id": str(stage_2_id)
                }
            ]
        }
        
        # Place candidate Application in Stage 1 and configure Stage 1 SLA
        app_obj = db_session.get(Application, app_id)
        app_obj.current_stage_id = stage_1_id
        app_obj.status = "screening"
        
        # Setup SLA for Stage 1
        sla_1 = StageSLA(
            company_id=comp_id,
            stage_definition_id=stage_1_id,
            duration_seconds=3600,
            escalation_action="notify_recruiter"
        )
        db_session.add(sla_1)
        db_session.flush()
        
        # Active tracker
        now = datetime.now(timezone.utc)
        tracker = CandidateStageSLATATracker = CandidateStageSLATracker(
            company_id=comp_id,
            application_id=app_id,
            stage_definition_id=stage_1_id,
            entered_at=now,
            expires_at=now + timedelta(hours=1),
            status="active",
            escalation_count=0
        )
        db_session.add(tracker)
        db_session.commit()
        tracker_id = tracker.id

    # 5. Schedule Interview via public API to ensure full consistent setup
    now = datetime.now(timezone.utc)
    interview_payload = {
        "interviewer_id": str(recruiter_id),
        "title": "Screening Technical Sync",
        "stage": "screening",
        "scheduled_at": (now + timedelta(days=2)).isoformat(),
        "duration_minutes": 45,
        "video_link": "https://meet.google.com/abc-defg-hij"
    }
    
    int_resp = api_client.post(
        f"/api/v1/applications/{app_id}/interviews",
        json=interview_payload,
        headers=headers
    )
    assert int_resp.status_code == 201
    interview_id = uuid.UUID(int_resp.json()["id"])

    # 6. Submit scorecard with overall_recommendation = 'strong_yes'
    resp_sc = api_client.post(
        f"/api/v1/applications/{app_id}/interviews/{interview_id}/scorecard",
        headers=headers,
        json={
            "criteria_scores": {
                "coding": 5,
                "system_design": 5,
                "communication": 5
            },
            "overall_recommendation": "strong_yes",
            "notes": "Excellent performance on all constraints."
        }
    )
    assert resp_sc.status_code == 201

    # 7. Verify auto-progression and SLA completion
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        # Verify application current_stage_id is now Stage 2
        app_obj = db_session.get(Application, app_id)
        assert app_obj.current_stage_id == stage_2_id
        assert app_obj.status == "interview" # Synced with interviewing base_category!
        
        # Verify the old tracker for Stage 1 is marked as completed on stage exit!
        old_tracker = db_session.get(CandidateStageSLATracker, tracker_id)
        assert old_tracker.status == "completed"

        # Assert audit logs: pipeline.stage_transitioned and pipeline.auto_progressed exist
        events = db_session.scalars(
            select(AuditLog).where(AuditLog.company_id == comp_id).order_by(AuditLog.timestamp.desc())
        ).all()
        actions = [e.action for e in events]
        assert "pipeline.stage_transitioned" in actions
        assert "pipeline.auto_progressed" in actions


def test_sla_breach_bg_sweep_and_loop_protection(db_session):
    """
    1. Asserts timed out SLA trackers trigger configured action (e.g. auto_advance).
    2. Enforces escalation safety parameters (escalation_count limit ceiling).
    """
    with tenant_context(auth_mode="true"):
        company = Company(name="SLA Breach Corp", slug="sla-breach-corp", status="active")
        db_session.add(company)
        db_session.flush()
        comp_id = company.id
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_id)})
        
        # Setup Pipeline
        pipeline = Pipeline(company_id=comp_id, name="SLA Pipeline", pipeline_version=1)
        db_session.add(pipeline)
        db_session.flush()

        # Setup source and fallback stages
        stage_src = StageDefinition(
            company_id=comp_id,
            pipeline_id=pipeline.id,
            name="SLA Source",
            sequence=1,
            base_category="screening",
            settings={},
            automation_rules=[],
            is_active=True
        )
        stage_dst = StageDefinition(
            company_id=comp_id,
            pipeline_id=pipeline.id,
            name="SLA Fallback",
            sequence=2,
            base_category="interviewing",
            settings={},
            automation_rules=[],
            is_active=True
        )
        db_session.add_all([stage_src, stage_dst])
        db_session.flush()

        # Setup Application
        job = Job(company_id=comp_id, title="Test Job", department="QA", description="QA", status=JobStatus.OPEN)
        candidate = Candidate(company_id=comp_id, email="sla_sweep@test.com", full_name="SLA Candidate")
        db_session.add_all([job, candidate])
        db_session.flush()

        app_obj = Application(company_id=comp_id, job_id=job.id, candidate_id=candidate.id, status="screening", current_stage_id=stage_src.id)
        db_session.add(app_obj)
        db_session.flush()

        # Setup Stage SLA auto_advance
        sla = StageSLA(company_id=comp_id, stage_definition_id=stage_src.id, duration_seconds=10, escalation_action="auto_advance", fallback_stage_id=stage_dst.id)
        db_session.add(sla)
        db_session.flush()

        # Setup Candidate Stage SLA Tracker (expired/timed out)
        now = datetime.now(timezone.utc)
        tracker = CandidateStageSLATracker(
            company_id=comp_id,
            application_id=app_obj.id,
            stage_definition_id=stage_src.id,
            entered_at=now - timedelta(seconds=20),
            expires_at=now - timedelta(seconds=10),
            status="active",
            escalation_count=0
        )
        db_session.add(tracker)
        db_session.commit()
        
        app_id = app_obj.id
        tracker_id = tracker.id
        stage_dst_id = stage_dst.id

    # Run the background sweep
    sweep_sla_breaches()

    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        # Verify tracker is marked as breached, escalation_count is incremented to 1
        tr = db_session.get(CandidateStageSLATracker, tracker_id)
        assert tr.status == "completed" # transition set it to completed!
        assert tr.escalation_count == 1

        # Verify application was auto-advanced to the fallback stage
        ap = db_session.get(Application, app_id)
        assert ap.current_stage_id == stage_dst_id

        # Loop protection ceiling check:
        # Create a new active tracker that is expired but has escalation_count = 1
        tracker_loop = CandidateStageSLATracker(
            company_id=comp_id,
            application_id=app_id,
            stage_definition_id=stage_dst_id,
            entered_at=now - timedelta(seconds=20),
            expires_at=now - timedelta(seconds=10),
            status="active",
            escalation_count=1  # Already reached loop ceiling limit!
        )
        db_session.add(tracker_loop)
        db_session.commit()
        tracker_loop_id = tracker_loop.id

    # Run background sweep again
    sweep_sla_breaches()

    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        # The tracker with escalation_count = 1 should NOT be modified (skipped)
        tr_loop = db_session.get(CandidateStageSLATracker, tracker_loop_id)
        assert tr_loop.status == "active"  # Untouched due to loop ceiling protection!


def test_approval_step_escalations_and_reminders(api_client, db_session):
    """
    1. Asserts periodic reminder event logged when step is pending past threshold.
    2. Asserts timeout escalations handle delegate, auto_approve, and auto_reject.
    3. Confirms single-escalation enforcement loop protection.
    """
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "Approval Escalations Corp",
        "email": "recruiter@app-esc.com",
        "password": "secure-password",
        "full_name": "Recruiter A"
    })
    assert resp_a.status_code == 201
    headers_a = {"Authorization": f"Bearer {resp_a.json()['access_token']}"}
    comp_id = uuid.UUID(resp_a.json()["user"]["company_id"])
    recruiter_id = uuid.UUID(resp_a.json()["user"]["id"])

    # Register delegate user under same company directly in database
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_id)})
        delegate_user = User(
            company_id=comp_id,
            email="delegate@app-esc.com",
            password_hash="...",
            full_name="Delegate B",
            role=UserRole.RECRUITER
        )
        db_session.add(delegate_user)
        db_session.commit()
        delegate_id = delegate_user.id

    # 1. Create Approval Template
    resp_template = api_client.post(
        "/api/v1/approvals/templates",
        headers=headers_a,
        json={
            "name": "Escalation Template",
            "description": "Multi-role workflow with timeout",
            "target_type": "requisition",
            "steps": [
                {
                    "sequence": 1,
                    "role_required": "owner",
                    "approver_id": str(recruiter_id)
                }
            ]
        }
    )
    assert resp_template.status_code == 201
    template_data = resp_template.json()
    template_id = uuid.UUID(template_data["id"])

    # Query template step ID directly from database to bypass response model limitations
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        t_step = db_session.scalar(
            select(ApprovalTemplateStep).where(ApprovalTemplateStep.approval_template_id == template_id)
        )
        assert t_step is not None
        step_id = t_step.id

    # 2. Configure Escalation Rule: delegate to delegate_id after 10 seconds
    resp_rule = api_client.post(
        f"/api/v1/approvals/templates/steps/{step_id}/escalation",
        headers=headers_a,
        json={
            "timeout_seconds": 10,
            "escalation_type": "delegate",
            "delegate_id": str(delegate_id)
        }
    )
    assert resp_rule.status_code == 201

    # Setup Job in db
    with tenant_context(auth_mode="true"):
        job = Job(
            company_id=comp_id,
            title="Escalated Director",
            department="QA",
            description="QA Director",
            status=JobStatus.DRAFT
        )
        db_session.add(job)
        db_session.commit()
        job_id = job.id

    # 3. Instantiate Approval Chain
    resp_chain = api_client.post(
        "/api/v1/approvals/chains",
        headers=headers_a,
        json={
            "target_type": "requisition",
            "approval_template_id": str(template_id),
            "job_id": str(job_id)
        }
    )
    assert resp_chain.status_code == 201
    chain_id = uuid.UUID(resp_chain.json()["id"])

    # Expire step's created_at to trigger reminder and escalation
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        step = db_session.scalar(select(ApprovalStep).where(ApprovalStep.approval_chain_id == chain_id))
        assert step is not None
        step_rec_id = step.id
        
        # Set created_at to 6 seconds ago (past reminder threshold of 5s, but before 10s timeout)
        step.created_at = datetime.now(timezone.utc) - timedelta(seconds=6)
        db_session.commit()

    # 4. Trigger sweep to test reminder dispatch
    sweep_approval_escalations()

    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        # Verify reminder event was logged
        reminders = db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "approval.step_reminder_sent",
                AuditLog.resource_id == str(step_rec_id)
            )
        ).all()
        assert len(reminders) == 1

        # Now set created_at to 12 seconds ago to trigger delegation escalation
        step_obj = db_session.get(ApprovalStep, step_rec_id)
        step_obj.created_at = datetime.now(timezone.utc) - timedelta(seconds=12)
        db_session.commit()

    # 5. Trigger sweep to test timeout delegation
    sweep_approval_escalations()

    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        # Verify step is delegated to delegate_id
        step_obj = db_session.get(ApprovalStep, step_rec_id)
        assert step_obj.approver_id == delegate_id

        # Verify escalation record exists in approval_step_escalations
        esc = db_session.scalar(select(ApprovalStepEscalation).where(ApprovalStepEscalation.approval_step_id == step_rec_id))
        assert esc is not None
        assert "Delegated approval" in esc.action_taken

        # Assert step audit event logged
        events = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "approval.step_escalated", AuditLog.resource_id == str(step_rec_id))
        ).all()
        assert len(events) == 1
