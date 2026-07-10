import uuid
from datetime import datetime, date, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from db.session import tenant_context
from models import User, Company
from models.enums import UserRole
from models.employees import Employee, OnboardingWorkflow, OnboardingTask
from models.employee_onboarding import EmployeeOnboarding
from models.onboarding_task_dependencies import OnboardingTaskDependency
from core.security import create_access_token
from server import app

@pytest.fixture
def db_session_test(db_engine):
    """Create a scoped test database session and override app dependencies."""
    from sqlalchemy.orm import Session
    from api.deps import get_db, get_employee_db, get_tenant_db
    
    db = Session(db_engine)
    
    def override_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_employee_db] = override_db
    app.dependency_overrides[get_tenant_db] = override_db
    
    yield db
    
    app.dependency_overrides.clear()
    db.close()

@pytest.fixture
def onboarding_setup(db_session_test):
    """Seed DB with a test company, manager employee, candidate user, and employee user."""
    db = db_session_test
    
    with tenant_context(auth_mode="true"):
        # Create company
        company = Company(name="Test Corp Onb", slug="test-corp-onb", status="active")
        db.add(company)
        db.flush()

        # Create manager/supervisor
        manager_user = User(
            company_id=company.id,
            email="manager_onb@testcorp.com",
            password_hash="hash",
            full_name="Manager Bob",
            role=UserRole.RECRUITER,
            email_verified=True,
        )
        db.add(manager_user)
        db.flush()

        manager_emp = Employee(
            company_id=company.id,
            email="manager_onb@testcorp.com",
            full_name="Manager Bob",
            job_title="Engineering Director",
            employment_type="full_time",
            status="active",
            start_date=date.today() - timedelta(days=365),
            user_id=manager_user.id,
        )
        db.add(manager_emp)
        db.flush()

        # Create employee user
        employee_user = User(
            company_id=company.id,
            email="newhire_onb@testcorp.com",
            password_hash="hash",
            full_name="New Hire Alice",
            role=UserRole.EMPLOYEE,
            email_verified=True,
        )
        db.add(employee_user)
        db.flush()

        employee = Employee(
            company_id=company.id,
            email="newhire_onb@testcorp.com",
            full_name="New Hire Alice",
            job_title="Software Engineer",
            department="Engineering",
            employment_type="full_time",
            status="onboarding",
            start_date=date.today() + timedelta(days=14),
            supervisor_id=manager_emp.id,
            user_id=employee_user.id,
        )
        db.add(employee)
        db.flush()

        # Create workflow & status
        workflow = OnboardingWorkflow(
            company_id=company.id,
            employee_id=employee.id,
            status="initiated",
        )
        db.add(workflow)
        db.flush()

        onboarding = EmployeeOnboarding(
            company_id=company.id,
            employee_id=employee.id,
            template_name="Engineering Template",
            template_version=3,
            template_snapshot_created_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db.add(onboarding)
        db.flush()

        # Add tasks
        task_nda = OnboardingTask(
            company_id=company.id,
            workflow_id=workflow.id,
            title="Sign NDA",
            status="pending",
            task_type="document_signature",
            phase="preboarding",
            is_optional=False,
        )
        task_laptop = OnboardingTask(
            company_id=company.id,
            workflow_id=workflow.id,
            title="Request Laptop",
            status="pending",
            task_type="equipment_request",
            phase="day_1",
            is_optional=True,
        )
        db.add(task_nda)
        db.add(task_laptop)
        db.flush()

        # Add dependency: Laptop depends on NDA
        dep = OnboardingTaskDependency(
            task_id=task_laptop.id,
            depends_on_task_id=task_nda.id,
        )
        db.add(dep)
        db.commit()

        # Generate tokens
        employee_token = create_access_token(
            str(employee_user.id),
            {"company_id": str(company.id), "role": "employee", "email": employee_user.email}
        )
        manager_token = create_access_token(
            str(manager_user.id),
            {"company_id": str(company.id), "role": "recruiter", "email": manager_user.email}
        )

        yield {
            "company_id": company.id,
            "employee_user_id": employee_user.id,
            "employee_id": employee.id,
            "manager_user_id": manager_user.id,
            "manager_employee_id": manager_emp.id,
            "employee_token": employee_token,
            "manager_token": manager_token,
            "task_nda_id": task_nda.id,
            "task_laptop_id": task_laptop.id,
        }

        # Cleanup
        db.delete(dep)
        db.delete(task_laptop)
        db.delete(task_nda)
        db.delete(onboarding)
        db.delete(workflow)
        db.delete(employee)
        db.delete(employee_user)
        db.delete(manager_emp)
        db.delete(manager_user)
        db.delete(company)
        db.commit()


def test_employee_auth_and_dashboard(onboarding_setup):
    """Verify employee token validation and dashboard loading details."""
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {onboarding_setup['employee_token']}"}

    # Test token verification
    response = client.get("/api/v1/employee/auth/verify", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "newhire_onb@testcorp.com"
    assert response.json()["role"] == "employee"

    # Test dashboard retrieval
    response = client.get("/api/v1/employee/dashboard", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["employee"]["full_name"] == "New Hire Alice"
    assert data["onboarding"]["template_name"] == "Engineering Template"
    assert data["onboarding"]["progress_percentage"] == 0

    # Test welcome center assets
    response = client.get("/api/v1/employee/welcome/welcome-center", headers=headers)
    assert response.status_code == 200
    assert "welcome_video_url" in response.json()
    assert "ceo_message" in response.json()


def test_employee_checklist_dependencies_and_completion(onboarding_setup):
    """Verify checklist retrieval, blocked task dependency checking, and onboarding completion."""
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {onboarding_setup['employee_token']}"}

    # Get checklist
    response = client.get("/api/v1/employee/checklist", headers=headers)
    assert response.status_code == 200
    phases = response.json()
    assert len(phases["preboarding"]) == 1
    assert phases["preboarding"][0]["title"] == "Sign NDA"
    assert phases["day_1"][0]["title"] == "Request Laptop"
    assert phases["day_1"][0]["is_blocked"] is True  # blocked by NDA

    # Attempt to complete blocked task (Request Laptop)
    response = client.post(f"/api/v1/employee/checklist/{onboarding_setup['task_laptop_id']}/complete", headers=headers)
    assert response.status_code == 400
    assert "blocked" in response.json()["detail"].lower()

    # Complete the prerequisite (Sign NDA)
    response = client.post(f"/api/v1/employee/checklist/{onboarding_setup['task_nda_id']}/complete", headers=headers)
    assert response.status_code == 200
    assert response.json()["onboarding_status"] == "completed"  # only NDA is required; Laptop is optional!

    # Complete Request Laptop (now unblocked)
    response = client.post(f"/api/v1/employee/checklist/{onboarding_setup['task_laptop_id']}/complete", headers=headers)
    assert response.status_code == 200
