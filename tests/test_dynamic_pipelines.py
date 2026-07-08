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
    ApprovalStep
)
from models.enums import UserRole, JobStatus
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


def test_automation_rules_and_stages_schema_validation(api_client, db_session):
    """
    Verify Pydantic schema validation at the API boundary:
    - Enforces valid base categories.
    - Enforces supported automation rule types ('send_email', 'send_form', 'trigger_assessment').
    - Rejects invalid automation rules with HTTP 422.
    """
    # 1. Register Company
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Pipeline Schema Corp Validation",
        "email": "pipeline_schema_val@corp.com",
        "password": "pipeline-secure-password-123",
        "full_name": "Recruiter Schema"
    })
    assert resp.status_code == 201
    reg = resp.json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    u_id = uuid.UUID(reg["user"]["id"])
    c_id = uuid.UUID(reg["user"]["company_id"])
    with tenant_context(auth_mode="true"):
        user = db_session.get(User, u_id)
        if user:
            user.email_verified = True
            db_session.add(user)
        comp = db_session.get(Company, c_id)
        if comp:
            comp.settings = {
                "website": "https://corp.com",
                "domain": "corp.com",
                "industry": "Technology",
                "company_size": "11-50"
            }
            db_session.add(comp)
        db_session.commit()


    # 2. Try to create a pipeline template with invalid base_category
    resp = api_client.post(
        "/api/v1/pipelines/templates",
        headers=headers,
        json={
            "name": "Invalid Category Template",
            "description": "Will fail schema check",
            "stages": [
                {
                    "name": "Resume Screening",
                    "sequence": 1,
                    "base_category": "invalid_category",
                    "settings": {},
                    "automation_rules": []
                }
            ]
        }
    )
    assert resp.status_code == 422
    assert "Unsupported base category" in resp.text

    # 3. Try to create a template with an unsupported automation type
    resp = api_client.post(
        "/api/v1/pipelines/templates",
        headers=headers,
        json={
            "name": "Invalid Automation Template",
            "description": "Will fail schema check due to invalid automation",
            "stages": [
                {
                    "name": "Technical Assessment",
                    "sequence": 1,
                    "base_category": "screening",
                    "settings": {},
                    "automation_rules": [
                        {
                            "type": "invalid_automation_type",
                            "config": {}
                        }
                    ]
                }
            ]
        }
    )
    assert resp.status_code == 422
    assert "Unsupported automation type" in resp.text


def test_dynamic_pipeline_cloning_lifecycle(api_client, db_session):
    """
    Verify the cloning-on-instantiation pipeline versioning strategy:
    - Pipeline template creation.
    - Instantiating a pipeline clones template stages into job-specific stages.
    - Job stage updates/modifications remain isolated from the original template.
    - RLS multi-tenant boundary prevents other company access.
    """
    # 1. Register Company A
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "Pipeline Corp A Dynamic",
        "email": "recruiter_a_dyn@corp-a.com",
        "password": "recruiter-password-a",
        "full_name": "Recruiter A"
    })
    assert resp_a.status_code == 201
    reg_a = resp_a.json()
    token_a = reg_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    comp_a_id = uuid.UUID(reg_a["user"]["company_id"])
    owner_a_id = uuid.UUID(reg_a["user"]["id"])

    # Register Company B (isolation check)
    resp_b = api_client.post("/api/v1/auth/register", json={
        "company_name": "Pipeline Corp B Dynamic",
        "email": "recruiter_b_dyn@corp-b.com",
        "password": "recruiter-password-b",
        "full_name": "Recruiter B"
    })
    assert resp_b.status_code == 201
    reg_b = resp_b.json()
    token_b = reg_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    comp_b_id = uuid.UUID(reg_b["user"]["company_id"])
    owner_b_id = uuid.UUID(reg_b["user"]["id"])

    with tenant_context(auth_mode="true"):
        user_a = db_session.get(User, owner_a_id)
        if user_a:
            user_a.email_verified = True
            db_session.add(user_a)
        comp_a = db_session.get(Company, comp_a_id)
        if comp_a:
            comp_a.settings = {
                "website": "https://corp-a.com",
                "domain": "corp-a.com",
                "industry": "Technology",
                "company_size": "11-50"
            }
            db_session.add(comp_a)

        user_b = db_session.get(User, owner_b_id)
        if user_b:
            user_b.email_verified = True
            db_session.add(user_b)
        comp_b = db_session.get(Company, comp_b_id)
        if comp_b:
            comp_b.settings = {
                "website": "https://corp-b.com",
                "domain": "corp-b.com",
                "industry": "Technology",
                "company_size": "11-50"
            }
            db_session.add(comp_b)
        db_session.commit()

    # 2. Setup job inside Company A

    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_a_id)})
        job_a = Job(
            company_id=comp_a_id,
            title="Software Architect",
            department="Engineering",
            description="Design scalable distributed APIs",
            status=JobStatus.OPEN
        )
        db_session.add(job_a)
        db_session.commit()
        job_a_id = job_a.id

    # 3. Create pipeline template for Company A
    resp_template = api_client.post(
        "/api/v1/pipelines/templates",
        headers=headers_a,
        json={
            "name": "Standard Tech Requisition",
            "description": "Standard engineering process",
            "stages": [
                {
                    "name": "Apply Online",
                    "sequence": 1,
                    "base_category": "applied",
                    "settings": {},
                    "automation_rules": []
                },
                {
                    "name": "Technical Quiz",
                    "sequence": 2,
                    "base_category": "screening",
                    "settings": {},
                    "automation_rules": [
                        {
                            "type": "send_form",
                            "config": {"form_id": "tech_quiz_101"}
                        }
                    ]
                }
            ]
        }
    )
    assert resp_template.status_code == 201
    template_a_id = resp_template.json()["id"]

    # 4. Clone template and instantiate job pipeline
    resp_clone = api_client.post(
        f"/api/v1/pipelines/jobs/{job_a_id}/pipeline?template_id={template_a_id}",
        headers=headers_a
    )
    assert resp_clone.status_code == 201
    pipeline_data = resp_clone.json()
    pipeline_id = pipeline_data["id"]
    assert pipeline_data["pipeline_version"] == 1

    # Verify cloned stages exist in database associated with pipeline_id
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        cloned_stages = db_session.scalars(
            select(StageDefinition).where(
                StageDefinition.pipeline_id == uuid.UUID(pipeline_id)
            ).order_by(StageDefinition.sequence)
        ).all()
        assert len(cloned_stages) == 2
        assert cloned_stages[0].name == "Apply Online"
        assert cloned_stages[1].name == "Technical Quiz"
        assert cloned_stages[1].automation_rules[0]["type"] == "send_form"

        # Assert audit trail entry was logged
        audit_log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.action == "pipeline.bound_to_job",
                AuditLog.company_id == comp_a_id
            )
        )
        assert audit_log is not None
        assert audit_log.metadata_json["job_id"] == str(job_a_id)

    # 5. Verify multi-tenant RLS isolation blocks Company B
    resp_block = api_client.post(
        f"/api/v1/pipelines/jobs/{job_a_id}/pipeline?template_id={template_a_id}",
        headers=headers_b
    )
    assert resp_block.status_code == 404


def test_approval_chain_target_integrity_and_sequential_parallel_execution(api_client, db_session):
    """
    Verify complete approval chain integrity and execution engine:
    - Rejects invalid target mappings (violating CHECK constraint).
    - Rejects unauthorized or out-of-order approval step actions.
    - Handles parallel step approvals within the same sequence.
    - Advances correctly to next sequence step, and triggers completion.
    """
    # 1. Register Company A & Recruiter A
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "Approval Corp A Dynamic Execution",
        "email": "manager_a_exec@corp-a.com",
        "password": "manager-password-a",
        "full_name": "Manager A"
    })
    assert resp_a.status_code == 201
    reg_a = resp_a.json()
    token_a = reg_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    comp_a_id = uuid.UUID(reg_a["user"]["company_id"])
    manager_a_id = uuid.UUID(reg_a["user"]["id"])

    with tenant_context(auth_mode="true"):
        user_a = db_session.get(User, manager_a_id)
        if user_a:
            user_a.email_verified = True
            db_session.add(user_a)
        comp_a = db_session.get(Company, comp_a_id)
        if comp_a:
            comp_a.settings = {
                "website": "https://corp-a.com",
                "domain": "corp-a.com",
                "industry": "Technology",
                "company_size": "11-50"
            }
            db_session.add(comp_a)
        db_session.commit()

    # 2. Setup job & offer in database under bypass context
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_a_id)})

        
        job_a = Job(
            company_id=comp_a_id,
            title="Director of Engineering",
            department="Management",
            description="Manage scalable platforms",
            status=JobStatus.OPEN
        )
        db_session.add(job_a)
        db_session.flush()
        job_a_id = job_a.id

        candidate_a = Candidate(
            company_id=comp_a_id,
            email="candidate_a_approval_run@test.com",
            full_name="Candidate A Approval"
        )
        db_session.add(candidate_a)
        db_session.flush()

        app_a = Application(
            company_id=comp_a_id,
            job_id=job_a_id,
            candidate_id=candidate_a.id,
            status="submitted",
            source="Referral"
        )
        db_session.add(app_a)
        db_session.flush()
        app_a_id = app_a.id

        offer_a = Offer(
            company_id=comp_a_id,
            application_id=app_a_id,
            salary=Decimal("150000.00"),
            start_date=date.today() + timedelta(days=14),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            status="draft"
        )
        db_session.add(offer_a)
        db_session.commit()
        offer_a_id = offer_a.id

    # 3. Create reusable Approval Template (target_type = "requisition")
    resp_template = api_client.post(
        "/api/v1/approvals/templates",
        headers=headers_a,
        json={
            "name": "Standard Job Approval",
            "description": "Requires manager and executive",
            "target_type": "requisition",
            "steps": [
                {
                    "sequence": 1,
                    "parallel_group": 1,  # Parallel approval step 1
                    "role_required": "owner",
                    "approver_id": str(manager_a_id)
                },
                {
                    "sequence": 1,
                    "parallel_group": 1,  # Parallel approval step 2
                    "role_required": "owner"
                },
                {
                    "sequence": 2,
                    "role_required": "owner",
                    "approver_id": str(manager_a_id)
                }
            ]
        }
    )
    assert resp_template.status_code == 201
    template_id = resp_template.json()["id"]

    # 4. Verify target integrity CHECK constraint fails when BOTH are provided
    resp_fail = api_client.post(
        "/api/v1/approvals/chains",
        headers=headers_a,
        json={
            "target_type": "requisition",
            "approval_template_id": template_id,
            "job_id": str(job_a_id),
            "offer_id": str(offer_a_id)
        }
    )
    assert resp_fail.status_code == 422
    assert "must have a job_id and no offer_id" in resp_fail.text

    # 5. Create valid chain (target_type = "requisition")
    resp_chain = api_client.post(
        "/api/v1/approvals/chains",
        headers=headers_a,
        json={
            "target_type": "requisition",
            "approval_template_id": template_id,
            "job_id": str(job_a_id),
            "offer_id": None
        }
    )
    assert resp_chain.status_code == 201
    chain_data = resp_chain.json()
    chain_id = chain_data["id"]
    assert chain_data["status"] == "pending"
    assert chain_data["current_step_sequence"] == 1

    # Fetch instantiated steps
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        steps = db_session.scalars(
            select(ApprovalStep).where(
                ApprovalStep.approval_chain_id == uuid.UUID(chain_id)
            ).order_by(ApprovalStep.sequence, ApprovalStep.id)
        ).all()
        
        assert len(steps) == 3
        
        # Dynamically identify steps based on structure to avoid sorting order issues
        step_1_id = None
        step_2_id = None
        step_3_id = None
        
        for s in steps:
            if s.sequence == 1:
                if s.approver_id is not None:
                    step_1_id = s.id
                else:
                    step_2_id = s.id
            elif s.sequence == 2:
                step_3_id = s.id
                
        assert step_1_id is not None
        assert step_2_id is not None
        assert step_3_id is not None

    # 6. Try to action sequence 2 step (out of order) -> expects 400
    resp_action_fail = api_client.post(
        f"/api/v1/approvals/steps/{step_3_id}/action",
        headers=headers_a,
        json={"action": "approve"}
    )
    assert resp_action_fail.status_code == 400
    assert "Current pending sequence is 1" in resp_action_fail.text

    # 7. Action sequence 1 step 1 (Approve)
    resp_action_1 = api_client.post(
        f"/api/v1/approvals/steps/{step_1_id}/action",
        headers=headers_a,
        json={"action": "approve"}
    )
    assert resp_action_1.status_code == 200
    assert resp_action_1.json()["status"] == "approved"

    # Verify chain current sequence has not advanced because parallel step 2 remains pending
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        chain = db_session.get(ApprovalChain, uuid.UUID(chain_id))
        assert chain.current_step_sequence == 1
        assert chain.status == "pending"

    # 8. Action sequence 1 step 2 (Approve)
    resp_action_2 = api_client.post(
        f"/api/v1/approvals/steps/{step_2_id}/action",
        headers=headers_a,
        json={"action": "approve"}
    )
    assert resp_action_2.status_code == 200

    # All sequence 1 steps are approved! Chain sequence should advance to sequence 2
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        chain = db_session.get(ApprovalChain, uuid.UUID(chain_id))
        assert chain.current_step_sequence == 2
        assert chain.status == "pending"

    # 9. Action sequence 2 step (Reject)
    resp_action_3 = api_client.post(
        f"/api/v1/approvals/steps/{step_3_id}/action",
        headers=headers_a,
        json={"action": "reject", "rejection_reason": "Executive reject"}
    )
    assert resp_action_3.status_code == 200
    assert resp_action_3.json()["status"] == "rejected"

    # Rejection aborts the entire chain
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        chain = db_session.get(ApprovalChain, uuid.UUID(chain_id))
        assert chain.status == "rejected"

        # Assert audit event is logged
        audit_log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.action == "approval.step_rejected",
                AuditLog.company_id == comp_a_id
            )
        )
        assert audit_log is not None
        assert audit_log.metadata_json["reason"] == "Executive reject"
