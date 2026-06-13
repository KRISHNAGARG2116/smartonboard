import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from server import app
from db.session import get_db, tenant_context
from models import Company, User, Job
from models.enums import CompanyStatus, UserRole, JobStatus
from core.security import create_access_token, hash_password


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


def test_company_suspension_blocks_protected_routes(api_client, db_session):
    """Verify that a suspended company's users are blocked from protected endpoints."""
    # 1. Create a company and user in database
    with tenant_context(auth_mode="true"):
        company = Company(name="Suspended Corp", slug="suspended-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        user = User(
            company_id=company.id,
            email="owner@suspended.com",
            password_hash=hash_password("password123"),
            full_name="Owner Suspended",
            role=UserRole.OWNER,
            email_verified=True,
        )
        db_session.add(user)
        db_session.commit()

    # Create a token for the user
    token = create_access_token(
        str(user.id),
        {"company_id": str(user.company_id), "role": user.role.value, "email": user.email},
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Verify initial request succeeds
    response = api_client.get("/api/v1/companies/me", headers=headers)
    assert response.status_code == 200

    # 2. Suspend the company
    with tenant_context(auth_mode="true"):
        company.status = CompanyStatus.SUSPENDED
        db_session.commit()

    # Verify request is now blocked
    response2 = api_client.get("/api/v1/companies/me", headers=headers)
    assert response2.status_code == 401
    assert "suspended" in response2.json()["detail"].lower()

    # Verify login is also blocked
    login_payload = {"email": "owner@suspended.com", "password": "password123"}
    response_login = api_client.post("/api/v1/auth/login", json=login_payload)
    assert response_login.status_code == 401


def test_rbac_require_owner_enforcement(api_client, db_session):
    """Verify that only users with the OWNER role can call owner-restricted administrative endpoints."""
    # 1. Create a company, an owner user, and a recruiter user
    with tenant_context(auth_mode="true"):
        company = Company(name="RBAC Corp", slug="rbac-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        owner = User(
            company_id=company.id,
            email="owner@rbac.com",
            password_hash=hash_password("password123"),
            full_name="Owner Admin",
            role=UserRole.OWNER,
            email_verified=True,
        )
        recruiter = User(
            company_id=company.id,
            email="recruiter@rbac.com",
            password_hash=hash_password("password123"),
            full_name="Recruiter Admin",
            role=UserRole.RECRUITER,
            email_verified=True,
        )
        db_session.add(owner)
        db_session.add(recruiter)
        db_session.commit()

    # Generate tokens
    owner_token = create_access_token(
        str(owner.id),
        {"company_id": str(company.id), "role": owner.role.value, "email": owner.email},
    )
    recruiter_token = create_access_token(
        str(recruiter.id),
        {"company_id": str(company.id), "role": recruiter.role.value, "email": recruiter.email},
    )

    # 2. Try to update company name with OWNER (should succeed)
    response_owner = api_client.patch(
        "/api/v1/companies/me",
        json={"name": "Owner Updated Corp"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response_owner.status_code == 200
    assert response_owner.json()["name"] == "Owner Updated Corp"

    # 3. Try to update company name with RECRUITER (should fail with 403 Forbidden)
    response_recruiter = api_client.patch(
        "/api/v1/companies/me",
        json={"name": "Recruiter Hack Corp"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert response_recruiter.status_code == 403
    assert "forbidden" in response_recruiter.json()["detail"].lower()


def test_rbac_require_recruiter_enforcement(api_client, db_session):
    """Verify that both OWNER and RECRUITER can create and manage jobs (RequireRecruiter)."""
    with tenant_context(auth_mode="true"):
        company = Company(name="Job Corp", slug="job-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        owner = User(
            company_id=company.id,
            email="owner@job.com",
            password_hash=hash_password("password123"),
            full_name="Owner Job",
            role=UserRole.OWNER,
            email_verified=True,
        )
        recruiter = User(
            company_id=company.id,
            email="recruiter@job.com",
            password_hash=hash_password("password123"),
            full_name="Recruiter Job",
            role=UserRole.RECRUITER,
            email_verified=True,
        )
        db_session.add(owner)
        db_session.add(recruiter)
        db_session.commit()

    owner_token = create_access_token(
        str(owner.id),
        {"company_id": str(company.id), "role": owner.role.value, "email": owner.email},
    )
    recruiter_token = create_access_token(
        str(recruiter.id),
        {"company_id": str(company.id), "role": recruiter.role.value, "email": recruiter.email},
    )

    # Recruiters can create jobs
    response1 = api_client.post(
        "/api/v1/jobs",
        json={"title": "QA Lead", "department": "QA", "description": "Desc", "status": "open", "start_date": "2026-06-01"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert response1.status_code == 201

    # Owners can also create jobs
    response2 = api_client.post(
        "/api/v1/jobs",
        json={"title": "Dev Lead", "department": "Dev", "description": "Desc", "status": "open", "start_date": "2026-06-01"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response2.status_code == 201


def test_login_timing_decoy_triggered(api_client, db_session):
    """Verify login timing protection by checking that incorrect users perform bcrypt checks."""
    # Test that a login attempt for a non-existent email runs through verify_password
    # and takes similar timing to standard invalid password attempts.
    payload_nonexistent = {
        "email": "not-found-anywhere-db@nonexistent.com",
        "password": "somepassword123",
    }
    
    start_time = time.perf_counter()
    response = api_client.post("/api/v1/auth/login", json=payload_nonexistent)
    duration = time.perf_counter() - start_time
    
    assert response.status_code == 401
    # Standard bcrypt hashing typically takes >50ms. An instant database exit would be <5ms.
    # Asserting that the duration is significantly longer than immediate lookup validates the decoy hashing path.
    assert duration > 0.05
