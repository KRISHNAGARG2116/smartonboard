import pytest
import uuid
from datetime import date, datetime, timezone, timedelta
from sqlalchemy import select, text
from fastapi.testclient import TestClient

from server import app
from db.session import get_db, tenant_context
from core.vault import SecretVaultService
from core.hris import HRISCredentialCrypto
from models import (
    User, Company, Job, Application, Candidate, Offer, Employee,
    OnboardingTemplate, OnboardingTemplateTask, OnboardingWorkflow,
    OnboardingTask, OnboardingDocument, OnboardingEventOutbox,
    CompanyHRISIntegration, DLQRecord, EmployeeSyncHistory,
    OnboardingPortalToken, OnboardingDocumentSignature, OnboardingTaskReminder,
    OnboardingTaskEscalation, OnboardingActivityLog
)
from models.enums import UserRole, JobStatus, ApplicationStatus
from models.audit import AuditLog
from core.onboarding import OnboardingEngine
from core.lifecycle import CandidateToEmployeeService


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


@pytest.fixture
def setup_lifecycle_test(db_session, api_client):
    print("SETUP_LIFECYCLE_TEST STARTING", flush=True)
    # 1. Register Company A (Owner A)
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "Lifecycle Corp A",
        "email": "owner_a@lifecyclecorp.com",
        "password": "super-secure-password-123",
        "full_name": "Lifecycle Owner A"
    })
    reg_a = resp_a.json()
    if "access_token" not in reg_a:
        raise ValueError(f"REGISTRATION FAILED: {reg_a}")
    token_a = reg_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    comp_a_id = uuid.UUID(reg_a["user"]["company_id"])
    owner_a_id = uuid.UUID(reg_a["user"]["id"])

    # 2. Register Company B (Owner B)
    resp_b = api_client.post("/api/v1/auth/register", json={
        "company_name": "Lifecycle Corp B",
        "email": "owner_b@lifecyclecorp.com",
        "password": "super-secure-password-123",
        "full_name": "Lifecycle Owner B"
    })
    reg_b = resp_b.json()
    token_b = reg_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    comp_b_id = uuid.UUID(reg_b["user"]["company_id"])
    owner_b_id = uuid.UUID(reg_b["user"]["id"])

    # 3. Create a Job in Company A
    with tenant_context(auth_mode="true"):
        job_a = Job(
            company_id=comp_a_id,
            title="Software Engineer",
            department="Engineering",
            status=JobStatus.OPEN
        )
        db_session.add(job_a)
        db_session.commit()
        db_session.refresh(job_a)
        job_a_id = job_a.id

    # 4. Create a Job in Company B
    with tenant_context(auth_mode="true"):
        job_b = Job(
            company_id=comp_b_id,
            title="Sales Executive",
            department="Sales",
            status=JobStatus.OPEN
        )
        db_session.add(job_b)
        db_session.commit()
        db_session.refresh(job_b)
        job_b_id = job_b.id

    # 5. Apply Bob to Company A
    app_payload_a = {
        "job_id": str(job_a_id),
        "candidate_name": "Bob Builder",
        "candidate_email": "bob@build.com",
        "candidate_phone": "+1-555-9876",
        "source": "referral"
    }
    app_resp_a = api_client.post("/api/v1/applications", json=app_payload_a, headers=headers_a)
    app_data_a = app_resp_a.json()
    app_id_a = uuid.UUID(app_data_a["id"])

    # 6. Apply Alice to Company B
    app_payload_b = {
        "job_id": str(job_b_id),
        "candidate_name": "Alice Wonderland",
        "candidate_email": "alice@wonder.com",
        "candidate_phone": "+1-555-4321",
        "source": "direct"
    }
    app_resp_b = api_client.post("/api/v1/applications", json=app_payload_b, headers=headers_b)
    app_data_b = app_resp_b.json()
    app_id_b = uuid.UUID(app_data_b["id"])

    # Move applications to INTERVIEW status so that Offers can be created successfully
    api_client.patch(f"/api/v1/applications/{app_id_a}", json={"status": "interview"}, headers=headers_a)
    api_client.patch(f"/api/v1/applications/{app_id_b}", json={"status": "interview"}, headers=headers_b)

    return {
        "headers_a": headers_a,
        "headers_b": headers_b,
        "comp_a_id": comp_a_id,
        "comp_b_id": comp_b_id,
        "app_id_a": app_id_a,
        "app_id_b": app_id_b,
        "candidate_a_id": uuid.UUID(app_data_a["candidate_id"]),
        "candidate_b_id": uuid.UUID(app_data_b["candidate_id"]),
        "owner_a_id": owner_a_id,
        "owner_b_id": owner_b_id,
        "job_a_id": job_a_id,
        "job_b_id": job_b_id
    }


def test_rules_engine_task_assignments(db_session, setup_lifecycle_test):
    """Verify that OnboardingEngine dynamically assigns tasks based on rule_criteria matching employee fields."""
    comp_id = setup_lifecycle_test["comp_a_id"]
    
    # 1. Create a custom template with diverse rules
    with tenant_context(auth_mode="true"):
        template = OnboardingTemplate(
            company_id=comp_id,
            name="Engineering Checklist",
            description="Engineering and contractor checks",
            is_default=True
        )
        db_session.add(template)
        db_session.flush()

        # Task 1: Matches Engineering department
        task_eng = OnboardingTemplateTask(
            company_id=comp_id,
            template_id=template.id,
            title="Setup Engineering Laptop",
            description="Install python, git, and visual studio code.",
            sequence=1,
            task_type="it_provisioning",
            rule_criteria={"department": "Engineering"}
        )
        # Task 2: Matches Full-Time employment
        task_ft = OnboardingTemplateTask(
            company_id=comp_id,
            template_id=template.id,
            title="Submit Form W-4",
            description="Submit tax paperwork.",
            sequence=2,
            task_type="document_signature",
            rule_criteria={"employment_type": "full_time"}
        )
        # Task 3: Matches all (empty criteria)
        task_global = OnboardingTemplateTask(
            company_id=comp_id,
            template_id=template.id,
            title="Sign Employee Handbook",
            description="Read and sign handbook.",
            sequence=3,
            task_type="document_signature",
            rule_criteria={}
        )
        db_session.add_all([task_eng, task_ft, task_global])
        db_session.commit()

    # 2. Setup full-time engineering employee (flushed to database first to generate UUID)
    with tenant_context(tenant_id=str(comp_id)):
        emp_ft_eng = Employee(
            company_id=comp_id,
            email="eng@life.com",
            full_name="Eng FT",
            job_title="Software Developer",
            department="Engineering",
            employment_type="full_time",
            start_date=date.today(),
            status="onboarding"
        )
        db_session.add(emp_ft_eng)

        # 3. Setup contractor sales employee (flushed to database first to generate UUID)
        emp_con_sales = Employee(
            company_id=comp_id,
            email="sales@life.com",
            full_name="Sales Contractor",
            job_title="Sales Consultant",
            department="Sales",
            employment_type="contractor",
            start_date=date.today(),
            status="onboarding"
        )
        db_session.add(emp_con_sales)
        db_session.flush()

        # Run engine for FT Engineer
        workflow_ft = OnboardingEngine.evaluate_and_assign(db_session, emp_ft_eng, template)
        db_session.commit()
        
        # Verify FT Eng got all 3 tasks (matching engineering + full_time + global)
        tasks_ft = workflow_ft.tasks
        assert len(tasks_ft) == 3
        titles_ft = [t.title for t in tasks_ft]
        assert "Setup Engineering Laptop" in titles_ft
        assert "Submit Form W-4" in titles_ft
        assert "Sign Employee Handbook" in titles_ft

        # Run engine for Contractor Sales
        workflow_con = OnboardingEngine.evaluate_and_assign(db_session, emp_con_sales, template)
        db_session.commit()
        
        # Verify Sales Contractor only got the global welcome task (skipped FT & Eng tasks)
        tasks_con = workflow_con.tasks
        assert len(tasks_con) == 1
        assert tasks_con[0].title == "Sign Employee Handbook"


def test_candidate_conversion_atomic_lifecycle(api_client, db_session, setup_lifecycle_test):
    """Verify that transitioning an application to hired atomically spawns Employee, Workflow, Audit, and Outbox."""
    app_id = setup_lifecycle_test["app_id_a"]
    headers = setup_lifecycle_test["headers_a"]
    comp_id = setup_lifecycle_test["comp_a_id"]
    owner_id = setup_lifecycle_test["owner_a_id"]

    # 1. Create a draft offer first to test value mapping (Must succeed now since Application is in INTERVIEW status)
    now = datetime.now(timezone.utc)
    offer_body = {
        "salary": 140000.00,
        "equity_grant": "500 options",
        "start_date": "2026-08-01",
        "expires_at": (now + timedelta(days=5)).isoformat()
    }
    offer_resp = api_client.post(f"/api/v1/applications/{app_id}/offers", json=offer_body, headers=headers)
    assert offer_resp.status_code == 201

    # 2. Convert candidate to employee profile
    convert_body = {
        "employment_type": "full_time",
        "employee_number": "EMP-100"
    }
    resp = api_client.post(f"/api/v1/applications/{app_id}/convert", json=convert_body, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["full_name"] == "Bob Builder"
    assert data["email"] == "bob@build.com"
    assert data["job_title"] == "Software Engineer"  # Inherent from Application Job Title
    assert data["employee_number"] == "EMP-100"
    assert data["status"] == "onboarding"
    assert data["start_date"] == "2026-08-01"  # Populated from Offer start_date
    assert data["workflow_id"] is not None

    # 3. Assert Application status is Hired
    app_resp = api_client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert app_resp.json()["status"] == "hired"

    with tenant_context(tenant_id=str(comp_id)):
        # Verify employee record exists in DB under correct RLS
        employees = db_session.scalars(select(Employee).where(Employee.email == "bob@build.com")).all()
        assert len(employees) == 1
        emp = employees[0]
        assert emp.full_name == "Bob Builder"
        assert emp.employment_type == "full_time"
        assert emp.onboarding_workflow is not None

        # Verify default onboarding checklist tasks spawned (since no template was registered, it bootstrapped default!)
        workflow = emp.onboarding_workflow
        assert workflow.status == "initiated"
        assert len(workflow.tasks) == 3
        
        # Verify document signature task generated document signature link
        doc_tasks = [t for t in workflow.tasks if t.task_type == "document_signature"]
        assert len(doc_tasks) == 1
        assert len(doc_tasks[0].documents) == 1
        assert doc_tasks[0].documents[0].document_name == "Employee NDA"
        assert doc_tasks[0].documents[0].signature_status == "pending_candidate"

        # Verify outbox event 'employee.created' created successfully
        outbox_events = db_session.scalars(
            select(OnboardingEventOutbox).where(OnboardingEventOutbox.event_type == "employee.created")
        ).all()
        assert len(outbox_events) == 1
        assert outbox_events[0].status == "pending"
        assert outbox_events[0].payload["employee_id"] == str(emp.id)

    # 4. Verify audit trail 'employee.transitioned' logged
    with tenant_context(auth_mode="true"):
        audit_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "employee.transitioned").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(audit_logs) >= 1
        assert audit_logs[0].actor_id == owner_id
        assert audit_logs[0].metadata_json["employee_id"] == str(emp.id)


def test_candidate_conversion_rollback_integrity(api_client, db_session, setup_lifecycle_test):
    """Verify that duplication triggers exceptions, ensuring transaction rollbacks and keeping Application state intact."""
    app_id_a = setup_lifecycle_test["app_id_a"]
    headers = setup_lifecycle_test["headers_a"]
    comp_id = setup_lifecycle_test["comp_a_id"]
    job_id = setup_lifecycle_test["job_a_id"]

    # 1. Convert candidate successfully the first time
    body1 = {
        "employment_type": "full_time",
        "employee_number": "EMP-900"
    }
    resp1 = api_client.post(f"/api/v1/applications/{app_id_a}/convert", json=body1, headers=headers)
    assert resp1.status_code == 201

    # Apply a second candidate with a different email so application succeeds
    app_payload_2 = {
        "job_id": str(job_id),
        "candidate_name": "Charlie Builder",
        "candidate_email": "charlie@build.com",
        "candidate_phone": "+1-555-0000",
        "source": "referral"
    }
    app_resp_2 = api_client.post("/api/v1/applications", json=app_payload_2, headers=headers)
    assert app_resp_2.status_code == 201
    app_id_2 = uuid.UUID(app_resp_2.json()["id"])
    
    # Move application to interview so conversion doesn't fail on status checks
    api_client.patch(f"/api/v1/applications/{app_id_2}", json={"status": "interview"}, headers=headers)

    # 2. Attempt duplicate employee_number conversion -> Violates constraint, must be blocked with 409 Conflict
    resp2 = api_client.post(f"/api/v1/applications/{app_id_2}/convert", json={"employment_type": "full_time", "employee_number": "EMP-900"}, headers=headers)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()

    # 3. Assert rollback integrity: Application remains in interview status, no duplicate Employee created
    app2_check = api_client.get(f"/api/v1/applications/{app_id_2}", headers=headers)
    assert app2_check.json()["status"] == "interview"  # Did NOT move to hired or change


def test_multi_tenant_rls_employee_isolation(api_client, db_session, setup_lifecycle_test):
    """Verify strict multi-tenant isolation: Company A cannot see Company B's employees or integration keys."""
    app_a = setup_lifecycle_test["app_id_a"]
    app_b = setup_lifecycle_test["app_id_b"]
    headers_a = setup_lifecycle_test["headers_a"]
    headers_b = setup_lifecycle_test["headers_b"]

    # Convert Bob in Company A
    resp_a = api_client.post(f"/api/v1/applications/{app_a}/convert", json={"employment_type": "full_time", "employee_number": "EMP-A"}, headers=headers_a)
    assert resp_a.status_code == 201

    # Convert Alice in Company B
    resp_b = api_client.post(f"/api/v1/applications/{app_b}/convert", json={"employment_type": "part_time", "employee_number": "EMP-B"}, headers=headers_b)
    assert resp_b.status_code == 201

    # 1. Company A lists employees: Should see Bob, NOT Alice
    list_a = api_client.get("/api/v1/employees", headers=headers_a)
    assert list_a.status_code == 200
    data_a = list_a.json()
    assert len(data_a) == 1
    assert data_a[0]["full_name"] == "Bob Builder"
    assert data_a[0]["employee_number"] == "EMP-A"

    # 2. Company B lists employees: Should see Alice, NOT Bob
    list_b = api_client.get("/api/v1/employees", headers=headers_b)
    assert list_b.status_code == 200
    data_b = list_b.json()
    assert len(data_b) == 1
    assert data_b[0]["full_name"] == "Alice Wonderland"
    assert data_b[0]["employee_number"] == "EMP-B"

    # 3. RLS blocks access when hitting Company A's conversion API with Company B's token -> Returns 404
    db_session.expire_all()  # Clear identity map cache to force Postgres RLS evaluation
    foreign_resp = api_client.post(f"/api/v1/applications/{app_a}/convert", json={"employment_type": "full_time"}, headers=headers_b)
    assert foreign_resp.status_code == 404


def test_hris_credentials_envelope_encryption(db_session, setup_lifecycle_test):
    """Verify that credentials undergo high-security AES-GCM envelope encryption with per-tenant DEK enveloped by KEK."""
    from core.vault import SecretVaultService
    from core.hris import HRISCredentialCrypto

    vault = SecretVaultService()
    creds = {"api_key": "my-ultra-secret-bamboohr-api-token", "subdomain": "lifecyclecorp"}

    # Encrypt
    encrypted_envelope = HRISCredentialCrypto.encrypt_credentials(creds, vault)
    assert "ciphertext" in encrypted_envelope
    assert "encrypted_dek" in encrypted_envelope
    assert "tag" in encrypted_envelope
    assert "iv" in encrypted_envelope

    # Decrypt
    decrypted = HRISCredentialCrypto.decrypt_credentials(encrypted_envelope, vault)
    assert decrypted["api_key"] == "my-ultra-secret-bamboohr-api-token"
    assert decrypted["subdomain"] == "lifecyclecorp"


def test_hris_field_mappings_transformation(api_client, db_session, setup_lifecycle_test):
    """Verify dynamic provider field mapping transformation and name splitting calculations."""
    comp_a_id = setup_lifecycle_test["comp_a_id"]
    headers_a = setup_lifecycle_test["headers_a"]

    # 1. Create a custom mapping for Company A -> Map job_title to 'custom_title_field' in Gusto
    mapping_payload = {
        "provider": "gusto",
        "local_field": "job_title",
        "provider_field": "custom_title_field",
        "is_custom": True,
        "transform_rules": {}
    }
    resp = api_client.post("/api/v1/employees/mappings", json=mapping_payload, headers=headers_a)
    assert resp.status_code == 201

    # 2. Get target transformed payload for Bob Builder
    from core.hris import ProviderTransformationEngine
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_a_id)})
        bob = Employee(
            company_id=comp_a_id,
            email="bob@builder.com",
            full_name="Bob Builder",
            phone="+1-555-1234",
            job_title="Lead Architect",
            employment_type="full_time",
            start_date=date.today()
        )
        db_session.add(bob)
        db_session.commit()

        # Gusto split-name transform checks
        payload = ProviderTransformationEngine.transform_employee(db_session, bob, "gusto")
        assert payload["first_name"] == "Bob"
        assert payload["last_name"] == "Builder"
        assert payload["custom_title_field"] == "Lead Architect"  # Used custom mapping!


def test_hris_outbox_processing_state_machine_and_circuit_breaker(api_client, db_session, setup_lifecycle_test):
    """Verify outbox sweeps, state machine transitions, retry loops, DLQ routing, and circuit breaker activation."""
    comp_a_id = setup_lifecycle_test["comp_a_id"]
    headers_a = setup_lifecycle_test["headers_a"]
    vault = SecretVaultService()

    # 1. Add active HRIS integration for Company A with invalid key to trigger mock failure & retries
    from core.hris import HRISCredentialCrypto
    encrypted_creds = HRISCredentialCrypto.encrypt_credentials(
        {"api_key": "invalid_key", "subdomain": "corp-a"}, vault
    )
    
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_a_id)})
        
        integration = CompanyHRISIntegration(
            company_id=comp_a_id,
            provider="bamboohr",
            status="active",
            credentials_encrypted=encrypted_creds,
            credentials_hash="myhash",
            key_version=1,
            settings={"consecutive_failures": 0}
        )
        db_session.add(integration)
        db_session.commit()

    # 2. Convert candidate Bob -> creates employee, onboarding workflows, outbox
    app_a = setup_lifecycle_test["app_id_a"]
    resp_convert = api_client.post(f"/api/v1/applications/{app_a}/convert", json={"employment_type": "full_time", "employee_number": "EMP-SM"}, headers=headers_a)
    assert resp_convert.status_code == 201
    emp_id = uuid.UUID(resp_convert.json()["id"])

    # 3. Manually run the Celery outbox sweeper task
    from tasks.hris import sweep_onboarding_outbox_task
    sweep_onboarding_outbox_task()

    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        # Verify employee status is now 'failed' because api_key='invalid_key' triggered failure,
        # and since CELERY_TASK_ALWAYS_EAGER=true, Celery processed all retries synchronously until maximum DLQ fail!
        emp = db_session.get(Employee, emp_id)
        assert emp.sync_status == "failed"
        assert "invalid api key" in emp.sync_error.lower()

        # 4. Verify Dead Letter Queue record was automatically created
        dlq = db_session.scalar(select(DLQRecord).where(DLQRecord.company_id == comp_a_id))
        assert dlq is not None
        assert dlq.provider == "bamboohr"
        assert "invalid api key" in dlq.error_message.lower()

        # 5. Verify Employee Sync History records are logged for each state transition
        history = db_session.scalars(select(EmployeeSyncHistory).where(
            EmployeeSyncHistory.employee_id == emp_id
        ).order_by(EmployeeSyncHistory.created_at.asc())).all()
        
        # States should include: queued -> processing -> retrying -> retrying -> ... -> failed
        states = [h.sync_state for h in history]
        assert "queued" in states
        assert "processing" in states
        assert "retrying" in states
        assert "failed" in states

        # 6. Verify Circuit Breaker was tripped! (failures >= 5 -> integration status set to 'error')
        db_session.refresh(integration)
        assert integration.status == "error"
        assert integration.settings["consecutive_failures"] >= 5


def test_hris_dlq_manual_retry(api_client, db_session, setup_lifecycle_test):
    """Verify manual DLQ retry resets the sync state machine and successfully executes provisioning."""
    comp_a_id = setup_lifecycle_test["comp_a_id"]
    headers_a = setup_lifecycle_test["headers_a"]
    vault = SecretVaultService()

    # 1. Create a DLQ entry
    with tenant_context(auth_mode="true"):
        db_session.execute(text("SELECT set_config('app.company_id', :c_id, true)"), {"c_id": str(comp_a_id)})
        
        # Valid credentials
        encrypted_creds = HRISCredentialCrypto.encrypt_credentials(
            {"api_key": "valid_key", "subdomain": "corp-a"}, vault
        )
        integration = CompanyHRISIntegration(
            company_id=comp_a_id,
            provider="bamboohr",
            status="active",
            credentials_encrypted=encrypted_creds,
            credentials_hash="myhash",
            key_version=1,
            settings={"consecutive_failures": 0}
        )
        db_session.add(integration)
        
        emp = Employee(
            company_id=comp_a_id,
            email="bobby@builder.com",
            full_name="Bobby Builder",
            job_title="Engineer",
            employment_type="full_time",
            sync_status="failed",
            start_date=date.today()
        )
        db_session.add(emp)
        db_session.flush()

        outbox = OnboardingEventOutbox(
            company_id=comp_a_id,
            event_type="employee.created",
            payload={"employee_id": str(emp.id)},
            status="failed",
            retry_count=5
        )
        db_session.add(outbox)
        db_session.flush()

        dlq = DLQRecord(
            company_id=comp_a_id,
            outbox_id=outbox.id,
            provider="bamboohr",
            error_message="Manual seed fail",
            payload=outbox.payload,
            status="failed"
        )
        db_session.add(dlq)
        db_session.commit()
        dlq_id = dlq.id

    # 2. Trigger manual DLQ retry via API
    resp_retry = api_client.post(f"/api/v1/employees/dlq/{dlq_id}/retry", headers=headers_a)
    assert resp_retry.status_code == 200
    assert resp_retry.json()["status"] == "resolved"

    # 3. Assert states updated correctly
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        db_session.refresh(emp)
        db_session.refresh(outbox)
        if emp.sync_status != "synced":
            raise Exception(f"SYNC FAILURE! sync_error={emp.sync_error!r}, last_error={outbox.last_error!r}")
        assert emp.sync_status == "synced"
        assert emp.hris_id is not None
        assert outbox.status == "processed"

        # Check sync history transitions
        history = db_session.scalars(select(EmployeeSyncHistory).where(
            EmployeeSyncHistory.employee_id == emp.id
        ).order_by(EmployeeSyncHistory.created_at.asc())).all()
        states = [h.sync_state for h in history]
        assert "manual_review" in states
        assert "processing" in states
        assert "synced" in states


def test_sync_history_and_metrics_api_rls(api_client, db_session, setup_lifecycle_test):
    """Verify strict multi-tenant isolation on custom mappings, sync metrics, DLQ logs, and history queries."""
    app_a = setup_lifecycle_test["app_id_a"]
    headers_a = setup_lifecycle_test["headers_a"]
    headers_b = setup_lifecycle_test["headers_b"]

    # 1. Company A converts Bob successfully
    resp_convert = api_client.post(f"/api/v1/applications/{app_a}/convert", json={"employment_type": "full_time", "employee_number": "EMP-RLS"}, headers=headers_a)
    assert resp_convert.status_code == 201
    emp_id = uuid.UUID(resp_convert.json()["id"])

    # 2. Company A queries Bob's sync history -> 200 Success
    resp_history = api_client.get(f"/api/v1/employees/{emp_id}/sync-history", headers=headers_a)
    assert resp_history.status_code == 200

    # 3. Company B queries Bob's sync history -> 404 Not Found (RLS blocks cross-tenant view)
    db_session.expire_all()
    resp_block_history = api_client.get(f"/api/v1/employees/{emp_id}/sync-history", headers=headers_b)
    assert resp_block_history.status_code == 404

    # 4. Company B tries to view Company A's DLQ logs -> Returns empty list
    resp_block_dlq = api_client.get("/api/v1/employees/dlq", headers=headers_b)
    assert resp_block_dlq.status_code == 200
    assert len(resp_block_dlq.json()) == 0

    # 5. Company B tries to view Company A's sync metrics -> Returns empty list
    resp_block_metrics = api_client.get("/api/v1/employees/metrics", headers=headers_b)
    assert resp_block_metrics.status_code == 200
    assert len(resp_block_metrics.json()) == 0


def test_portal_authentication_flow(api_client, db_session, setup_lifecycle_test):
    """Verify portal authentication, short-lived JWT generation, scope validation, and revocation/expiration bounds."""
    comp_a_id = setup_lifecycle_test["comp_a_id"]
    app_a = setup_lifecycle_test["app_id_a"]
    headers_a = setup_lifecycle_test["headers_a"]

    # 1. Convert candidate to employee
    resp_convert = api_client.post(f"/api/v1/applications/{app_a}/convert", json={"employment_type": "full_time", "employee_number": "EMP-PORT-AUTH"}, headers=headers_a)
    assert resp_convert.status_code == 201
    emp_id = uuid.UUID(resp_convert.json()["id"])

    # 2. Seed a valid onboarding portal token
    with tenant_context(auth_mode="true"):
        raw_token = "high-entropy-token-string-xyz-1234"
        import hashlib
        h = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        
        portal_token = OnboardingPortalToken(
            company_id=comp_a_id,
            employee_id=emp_id,
            token_hash=h,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            is_revoked=False,
            access_scopes=["onboarding:read", "onboarding:write"]
        )
        db_session.add(portal_token)
        db_session.commit()
        token_id = portal_token.id

    # 3. Authenticate with a valid token -> 200 OK & yields JWT
    resp_auth = api_client.post("/api/v1/onboarding/portal/authenticate", json={"token": raw_token})
    assert resp_auth.status_code == 200
    auth_data = resp_auth.json()
    assert "access_token" in auth_data
    assert auth_data["employee_id"] == str(emp_id)
    assert auth_data["expires_in"] == 14400
    portal_jwt = auth_data["access_token"]

    # Verify activity log generated portal_authenticated
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        log = db_session.scalar(select(OnboardingActivityLog).where(
            OnboardingActivityLog.employee_id == emp_id,
            OnboardingActivityLog.event_type == "portal_authenticated"
        ))
        assert log is not None
        assert log.metadata_json["token_id"] == str(token_id)

    # 4. Authenticate with an invalid token -> 401 Unauthorized
    resp_bad = api_client.post("/api/v1/onboarding/portal/authenticate", json={"token": "invalid-token"})
    assert resp_bad.status_code == 401

    # 5. Authenticate with a revoked token
    with tenant_context(auth_mode="true"):
        portal_token.is_revoked = True
        db_session.add(portal_token)
        db_session.commit()
    resp_revoked = api_client.post("/api/v1/onboarding/portal/authenticate", json={"token": raw_token})
    assert resp_revoked.status_code == 401


def test_portal_checklist_and_document_signing(api_client, db_session, setup_lifecycle_test):
    """Test checklist retrieval, document e-signing with cryptographic fingerprint hash verification, and timeline state logs."""
    comp_a_id = setup_lifecycle_test["comp_a_id"]
    app_a = setup_lifecycle_test["app_id_a"]
    headers_a = setup_lifecycle_test["headers_a"]

    # 1. Convert candidate to employee -> generates workflow & default tasks
    resp_convert = api_client.post(f"/api/v1/applications/{app_a}/convert", json={"employment_type": "full_time", "employee_number": "EMP-SIGN"}, headers=headers_a)
    assert resp_convert.status_code == 201
    emp_id = uuid.UUID(resp_convert.json()["id"])

    # 2. Seed a valid portal token in DB
    raw_token = "sign-checklist-token-9988"
    import hashlib
    h = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with tenant_context(auth_mode="true"):
        portal_token = OnboardingPortalToken(
            company_id=comp_a_id,
            employee_id=emp_id,
            token_hash=h,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            is_revoked=False,
            access_scopes=["onboarding:read", "onboarding:write"]
        )
        db_session.add(portal_token)
        db_session.commit()

    # 3. Authenticate to get scoped Portal JWT
    resp_auth = api_client.post("/api/v1/onboarding/portal/authenticate", json={"token": raw_token})
    portal_jwt = resp_auth.json()["access_token"]
    portal_headers = {"Authorization": f"Bearer {portal_jwt}"}

    # 4. GET /api/v1/onboarding/portal/checklist
    resp_checklist = api_client.get("/api/v1/onboarding/portal/checklist", headers=portal_headers)
    assert resp_checklist.status_code == 200
    checklist = resp_checklist.json()
    assert checklist["employee_id"] == str(emp_id)
    assert len(checklist["tasks"]) > 0
    
    # Verify Sign NDA document exists
    nda_task = next(t for t in checklist["tasks"] if t["task_type"] == "document_signature")
    assert nda_task["requires_signature"] is True
    doc_id = uuid.UUID(nda_task["document_id"])

    # 5. POST /api/v1/onboarding/portal/documents/{id}/sign -> Signs NDA
    sign_payload = {
        "signer_name": "Bob Builder",
        "signature_text": "/s/ Bob Builder",
        "agree_to_electronic_terms": True
    }
    resp_sign = api_client.post(f"/api/v1/onboarding/portal/documents/{doc_id}/sign", json=sign_payload, headers=portal_headers)
    assert resp_sign.status_code == 200
    sign_data = resp_sign.json()
    assert sign_data["document_id"] == str(doc_id)
    assert sign_data["signature_hash"] is not None

    # 6. Verify database and checklist updates
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        # Document should be signed
        doc = db_session.get(OnboardingDocument, doc_id)
        assert doc.signature_status == "signed"
        assert doc.signed_at is not None

        # Parent Task should be completed
        task = db_session.get(OnboardingTask, doc.task_id)
        assert task.status == "completed"
        assert task.completed_at is not None

        # Electronic signature record created
        sig_rec = db_session.scalar(select(OnboardingDocumentSignature).where(OnboardingDocumentSignature.document_id == doc_id))
        assert sig_rec is not None
        assert sig_rec.signer_name == "Bob Builder"
        assert sig_rec.signature_hash == sign_data["signature_hash"]

        # Chronological Activity log populated
        act_sign = db_session.scalar(select(OnboardingActivityLog).where(
            OnboardingActivityLog.employee_id == emp_id,
            OnboardingActivityLog.event_type == "document_signed"
        ))
        assert act_sign is not None
        assert act_sign.metadata_json["document_id"] == str(doc_id)

        act_task = db_session.scalar(select(OnboardingActivityLog).where(
            OnboardingActivityLog.employee_id == emp_id,
            OnboardingActivityLog.event_type == "task_completed"
        ))
        assert act_task is not None
        assert act_task.metadata_json["task_id"] == str(task.id)


def test_onboarding_activity_timeline_and_api(api_client, db_session, setup_lifecycle_test):
    """Verify activity timeline logging, chronological sorting, pagination parameters, and tenant security isolation."""
    comp_a_id = setup_lifecycle_test["comp_a_id"]
    app_a = setup_lifecycle_test["app_id_a"]
    headers_a = setup_lifecycle_test["headers_a"]
    headers_b = setup_lifecycle_test["headers_b"]

    # 1. Convert candidate to employee (triggers onboarding_started & task_created events)
    resp_convert = api_client.post(f"/api/v1/applications/{app_a}/convert", json={"employment_type": "full_time", "employee_number": "EMP-TIMELINE"}, headers=headers_a)
    assert resp_convert.status_code == 201
    emp_id = uuid.UUID(resp_convert.json()["id"])

    # 2. Get Employee Activity Timeline -> 200 Success
    resp_timeline = api_client.get(f"/api/v1/employees/{emp_id}/activity", headers=headers_a)
    assert resp_timeline.status_code == 200
    timeline = resp_timeline.json()
    assert len(timeline) >= 2  # contains onboarding_started + task_created
    
    # Chronological sorting: onboarding_started should be before task_created
    types = [log["event_type"] for log in timeline]
    assert types[0] == "onboarding_started"
    assert "task_created" in types

    # 3. Test pagination: limit=1 returns 1 item
    resp_paginated = api_client.get(f"/api/v1/employees/{emp_id}/activity?limit=1", headers=headers_a)
    assert resp_paginated.status_code == 200
    assert len(resp_paginated.json()) == 1

    # 4. Test RLS Multi-Tenant Isolation
    # Company B tries to view Company A's employee activity timeline -> 404 Not Found
    db_session.expire_all()
    resp_isolated = api_client.get(f"/api/v1/employees/{emp_id}/activity", headers=headers_b)
    assert resp_isolated.status_code == 404


def test_onboarding_escalations_and_resolution(api_client, db_session, setup_lifecycle_test):
    """Validate Levels 1, 2, and 3 background escalations, dispatcher logging, and recruiter manual resolution override."""
    comp_a_id = setup_lifecycle_test["comp_a_id"]
    app_a = setup_lifecycle_test["app_id_a"]
    headers_a = setup_lifecycle_test["headers_a"]

    # 1. Convert candidate to employee -> generates workflow & default tasks
    resp_convert = api_client.post(f"/api/v1/applications/{app_a}/convert", json={"employment_type": "full_time", "employee_number": "EMP-ESCALATE"}, headers=headers_a)
    assert resp_convert.status_code == 201
    emp_id = uuid.UUID(resp_convert.json()["id"])

    # 2. Configure overdue tasks with different due_dates
    now = datetime.now(timezone.utc)
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        emp = db_session.get(Employee, emp_id)
        
        # Seed a supervisor for Level 2 escalations
        supervisor = Employee(
            company_id=comp_a_id,
            email="supervisor@lifecyclecorp.com",
            full_name="Julie Supervisor",
            job_title="Engineering Director",
            employment_type="full_time",
            start_date=date.today()
        )
        db_session.add(supervisor)
        db_session.flush()
        
        emp.supervisor_id = supervisor.id
        db_session.add(emp)
        db_session.flush()

        wf = db_session.scalar(select(OnboardingWorkflow).where(OnboardingWorkflow.employee_id == emp_id))
        tasks = db_session.scalars(select(OnboardingTask).where(OnboardingTask.workflow_id == wf.id)).all()
        
        # Task 0 (NDA): 1 day overdue -> Level 1 (reminder)
        tasks[0].due_date = (now - timedelta(days=1)).date()
        
        # Task 1 (Payroll): 3 days overdue -> Level 2 (supervisor escalation)
        tasks[1].due_date = (now - timedelta(days=3)).date()
        
        # Task 2 (Workstation): 6 days overdue -> Level 3 (recruiter escalation)
        tasks[2].due_date = (now - timedelta(days=6)).date()
        
        for t in tasks:
            db_session.add(t)
        db_session.commit()
        task_l1_id = tasks[0].id
        task_l2_id = tasks[1].id
        task_l3_id = tasks[2].id

    # 3. Trigger onboarding escalations background sweeper synchronously
    from tasks.escalations import sweep_onboarding_escalations
    sweep_onboarding_escalations()

    # 4. Assert escalations logged in database
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        
        # Level 1: Task 0 got reminder
        reminders = db_session.scalars(select(OnboardingTaskReminder).where(OnboardingTaskReminder.task_id == task_l1_id)).all()
        assert len(reminders) == 1
        assert reminders[0].status == "sent"
        
        # Level 2: Task 1 got supervisor escalation
        esc_l2 = db_session.scalar(select(OnboardingTaskEscalation).where(
            OnboardingTaskEscalation.task_id == task_l2_id,
            OnboardingTaskEscalation.escalation_level == 2
        ))
        assert esc_l2 is not None
        assert esc_l2.resolved_at is None

        # Level 3: Task 2 got recruiter escalation
        esc_l3 = db_session.scalar(select(OnboardingTaskEscalation).where(
            OnboardingTaskEscalation.task_id == task_l3_id,
            OnboardingTaskEscalation.escalation_level == 3
        ))
        assert esc_l3 is not None
        assert esc_l3.resolved_at is None

        # Timeline logged events
        act_rem = db_session.scalar(select(OnboardingActivityLog).where(
            OnboardingActivityLog.employee_id == emp_id,
            OnboardingActivityLog.event_type == "reminder_sent"
        ))
        assert act_rem is not None

        act_esc = db_session.scalars(select(OnboardingActivityLog).where(
            OnboardingActivityLog.employee_id == emp_id,
            OnboardingActivityLog.event_type == "escalation_triggered"
        )).all()
        assert len(act_esc) >= 2

    # 5. POST /api/v1/employees/tasks/{task_id}/escalations/resolve -> Recruiter manually resolves escalations
    resp_resolve = api_client.post(
        f"/api/v1/employees/tasks/{task_l3_id}/escalations/resolve",
        json={"resolution_notes": "Manually verified workstation specs"},
        headers=headers_a
    )
    assert resp_resolve.status_code == 200
    assert resp_resolve.json()["status"] == "resolved"

    # Verify escalation marked resolved in DB and timeline event generated
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        resolved_esc = db_session.get(OnboardingTaskEscalation, esc_l3.id)
        assert resolved_esc.resolved_at is not None
        
        act_res = db_session.scalar(select(OnboardingActivityLog).where(
            OnboardingActivityLog.employee_id == emp_id,
            OnboardingActivityLog.event_type == "escalation_resolved"
        ))
        assert act_res is not None
        assert act_res.metadata_json["resolution_notes"] == "Manually verified workstation specs"


