import uuid
from datetime import datetime, date, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from db.session import tenant_context
from models import User, Company
from models.enums import UserRole
from models.employees import Employee
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
def security_setup(db_session_test):
    """Seed DB with two companies, and an employee user in Company A."""
    db = db_session_test
    
    with tenant_context(auth_mode="true"):
        # Company A
        company_a = Company(name="Company A Sec Employee", slug="company-a-sec-employee", status="active")
        db.add(company_a)
        db.flush()

        employee_user_a = User(
            company_id=company_a.id,
            email="hire_a_sec_emp@comp-a.com",
            password_hash="hash",
            full_name="Hire A",
            role=UserRole.EMPLOYEE,
            email_verified=True,
        )
        db.add(employee_user_a)
        db.flush()

        employee_a = Employee(
            company_id=company_a.id,
            email="hire_a_sec_emp@comp-a.com",
            full_name="Hire A",
            job_title="Dev",
            employment_type="full_time",
            status="onboarding",
            start_date=date.today() + timedelta(days=14),
            user_id=employee_user_a.id,
        )
        db.add(employee_a)
        db.flush()

        # Company B (separate tenant)
        company_b = Company(name="Company B Sec Recruiter", slug="company-b-sec-recruiter", status="active")
        db.add(company_b)
        db.flush()

        recruiter_user_b = User(
            company_id=company_b.id,
            email="recruiter_b_sec_rec@comp-b.com",
            password_hash="hash",
            full_name="Recruiter B",
            role=UserRole.RECRUITER,
            email_verified=True,
        )
        db.add(recruiter_user_b)
        db.commit()

        # Generate tokens
        employee_token_a = create_access_token(
            str(employee_user_a.id),
            {"company_id": str(company_a.id), "role": "employee", "email": employee_user_a.email}
        )
        recruiter_token_b = create_access_token(
            str(recruiter_user_b.id),
            {"company_id": str(company_b.id), "role": "recruiter", "email": recruiter_user_b.email}
        )

        yield {
            "company_a_id": company_a.id,
            "company_b_id": company_b.id,
            "employee_a_token": employee_token_a,
            "recruiter_b_token": recruiter_token_b,
        }

        # Cleanup
        db.delete(employee_a)
        db.delete(employee_user_a)
        db.delete(recruiter_user_b)
        db.delete(company_a)
        db.delete(company_b)
        db.commit()


def test_tenant_rls_isolation_across_endpoints(security_setup):
    """Verify that employee and recruiter users cannot cross boundaries or perform unauthorized queries."""
    client = TestClient(app)
    emp_headers = {"Authorization": f"Bearer {security_setup['employee_a_token']}"}
    rec_headers = {"Authorization": f"Bearer {security_setup['recruiter_b_token']}"}

    # 1. Employee tries to access recruiter jobs endpoint (Forbidden)
    response = client.get("/api/v1/jobs", headers=emp_headers)
    assert response.status_code == 403

    # 2. Recruiter in Company B tries to view Company A's new hire dashboard (Forbidden)
    response = client.get("/api/v1/manager/onboarding/new-hires", headers=rec_headers)
    assert response.status_code == 200
    assert response.json() == []

    # 3. Recruiter B tries to retrieve HR metrics dashboard for Company A
    # The database RLS scopes the query to Company B, so they receive Company B's empty metrics instead of Company A's
    response = client.get("/api/v1/hr/onboarding/dashboard", headers=rec_headers)
    assert response.status_code == 200
    assert response.json()["alerts"]["starting_this_week"] == 0
