import uuid
from datetime import datetime, date, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from db.session import tenant_context
from models import User, Company
from models.enums import UserRole
from models.employees import Employee
from models.employee_equipment_request import EmployeeEquipmentRequest
from models.employee_provisioning_request import EmployeeProvisioningRequest
from core.security import create_access_token
from server import app

@pytest.fixture
def db_session_test(db_engine):
    """Create a scoped test database session and override app dependencies."""
    from sqlalchemy.orm import Session
    from typing import Annotated
    from fastapi import Depends
    from models import User
    from api.deps import get_db, get_employee_db, get_tenant_db, get_onboarded_recruiter
    
    db = Session(db_engine)
    
    def override_db():
        try:
            yield db
        finally:
            pass
            
    def override_get_tenant_db(current_user: Annotated[User, Depends(get_onboarded_recruiter)]):
        from db.session import set_tenant_context
        set_tenant_context(db, str(current_user.company_id))
        yield db
            
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_employee_db] = override_db
    app.dependency_overrides[get_tenant_db] = override_get_tenant_db
    
    yield db
    
    app.dependency_overrides.clear()
    db.close()

@pytest.fixture
def provisioning_setup(db_session_test):
    """Seed test company, employee, and manager supervisor."""
    db = db_session_test
    
    with tenant_context(auth_mode="true"):
        # Create company
        company = Company(name="Test Corp Equip Prov", slug="test-corp-equip-prov", status="active")
        db.add(company)
        db.flush()

        manager_user = User(
            company_id=company.id,
            email="manager_prov@testcorpequip.com",
            password_hash="hash",
            full_name="Manager Bob",
            role=UserRole.RECRUITER,
            email_verified=True,
        )
        db.add(manager_user)
        db.flush()

        manager_emp = Employee(
            company_id=company.id,
            email="manager_prov@testcorpequip.com",
            full_name="Manager Bob",
            job_title="Engineering Director",
            employment_type="full_time",
            status="active",
            start_date=date.today() - timedelta(days=365),
            user_id=manager_user.id,
        )
        db.add(manager_emp)
        db.flush()

        employee_user = User(
            company_id=company.id,
            email="newhire_prov@testcorpequip.com",
            password_hash="hash",
            full_name="New Hire Alice",
            role=UserRole.EMPLOYEE,
            email_verified=True,
        )
        db.add(employee_user)
        db.flush()

        employee = Employee(
            company_id=company.id,
            email="newhire_prov@testcorpequip.com",
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
        }

        # Cleanup
        db.query(EmployeeEquipmentRequest).filter(EmployeeEquipmentRequest.employee_id == employee.id).delete()
        db.query(EmployeeProvisioningRequest).filter(EmployeeProvisioningRequest.employee_id == employee.id).delete()
        db.delete(employee)
        db.delete(employee_user)
        db.delete(manager_emp)
        db.delete(manager_user)
        db.delete(company)
        db.commit()


def test_equipment_lifecycle_requisitions(provisioning_setup):
    """Test employee hardware requisition submission and manager resolution approval."""
    client = TestClient(app)
    emp_headers = {"Authorization": f"Bearer {provisioning_setup['employee_token']}"}
    mgr_headers = {"Authorization": f"Bearer {provisioning_setup['manager_token']}"}

    # 1. Create equipment request
    response = client.post(
        "/api/v1/employee/equipment",
        json={"item_type": "laptop", "item_name": "MacBook Pro M3 Max 16GB", "notes": "Developer preference"},
        headers=emp_headers
    )
    assert response.status_code == 201
    eq_req = response.json()
    assert eq_req["status"] == "requested"

    # 2. Get list of equipment
    response = client.get("/api/v1/employee/equipment", headers=emp_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["item_name"] == "MacBook Pro M3 Max 16GB"

    # 3. Modify equipment request
    response = client.put(
        f"/api/v1/employee/equipment/{eq_req['id']}",
        json={"item_name": "MacBook Pro M3 Max 32GB", "notes": "Developer preference - upgraded memory"},
        headers=emp_headers
    )
    assert response.status_code == 200
    assert response.json()["item_name"] == "MacBook Pro M3 Max 32GB"

    # 4. Manager reviews pending approvals
    response = client.get("/api/v1/manager/onboarding/approvals", headers=mgr_headers)
    assert response.status_code == 200
    assert len(response.json()["equipment"]) == 1
    assert response.json()["equipment"][0]["item_name"] == "MacBook Pro M3 Max 32GB"

    # 5. Manager approves the request
    response = client.post(
        f"/api/v1/manager/onboarding/approvals/equipment/{eq_req['id']}/resolve",
        json={"decision": "approve", "notes": "Approved for dev use"},
        headers=mgr_headers
    )
    assert response.status_code == 200

    # 6. Verify equipment request status changes to approved
    response = client.get("/api/v1/employee/equipment", headers=emp_headers)
    assert response.status_code == 200
    assert response.json()[0]["status"] == "approved"

    # 7. Attempt to edit approved request is blocked
    response = client.put(
        f"/api/v1/employee/equipment/{eq_req['id']}",
        json={"item_name": "MacBook Pro M3 Max 64GB"},
        headers=emp_headers
    )
    assert response.status_code == 403


def test_it_provisioning_dependencies(provisioning_setup, db_session_test):
    """Test provisioning request status retrieval with dependency verification."""
    db = db_session_test

    # Seed provisioning chain (Slack depends on SSO, SSO depends on Email)
    with tenant_context(auth_mode="true"):
        email_pr = EmployeeProvisioningRequest(
            company_id=provisioning_setup["company_id"],
            employee_id=provisioning_setup["employee_id"],
            service_name="email",
            status="provisioned",
        )
        db.add(email_pr)
        db.flush()

        sso_pr = EmployeeProvisioningRequest(
            company_id=provisioning_setup["company_id"],
            employee_id=provisioning_setup["employee_id"],
            service_name="sso",
            status="pending",
            depends_on_provisioning_id=email_pr.id,
        )
        db.add(sso_pr)
        db.flush()

        slack_pr = EmployeeProvisioningRequest(
            company_id=provisioning_setup["company_id"],
            employee_id=provisioning_setup["employee_id"],
            service_name="slack",
            status="pending",
            depends_on_provisioning_id=sso_pr.id,
        )
        db.add(slack_pr)
        db.commit()

    client = TestClient(app)
    emp_headers = {"Authorization": f"Bearer {provisioning_setup['employee_token']}"}

    # Fetch provisioning list
    response = client.get("/api/v1/employee/provisioning", headers=emp_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    # Check dependency mapping in return response
    slack_info = next(item for item in data if item["service_name"] == "slack")
    assert slack_info["depends_on_service"] == "sso"
    assert slack_info["depends_on_status"] == "pending"

    email_info = next(item for item in data if item["service_name"] == "email")
    assert email_info["depends_on_service"] is None
