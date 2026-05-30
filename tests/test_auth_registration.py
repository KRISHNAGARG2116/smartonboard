import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from server import app
from db.session import get_db, tenant_context
from models import Company, User
from models.enums import CompanyStatus, UserRole


@pytest.fixture
def api_client(db_session):
    # Override get_db to use our test database session bound to the non-superuser test user
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_registration_success(api_client, db_session):
    """Verify that a standard, correct registration request succeeds and returns proper JWT."""
    payload = {
        "email": "owner@newcompany.com",
        "password": "securepassword123",
        "full_name": "New Owner",
        "company_name": "New Company Inc",
    }

    response = api_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "owner@newcompany.com"
    assert data["user"]["full_name"] == "New Owner"
    assert data["user"]["role"] == "owner"
    assert data["user"]["company_id"] is not None

    # Check database persistence
    with tenant_context(auth_mode="true"):
        company = db_session.scalar(
            select(Company).where(Company.slug == "new-company-inc")
        )
        assert company is not None
        assert company.name == "New Company Inc"

        user = db_session.scalar(
            select(User).where(User.email == "owner@newcompany.com")
        )
        assert user is not None
        assert user.company_id == company.id


def test_registration_duplicate_email(api_client, db_session):
    """Verify that registering with an already existing email returns HTTP 409 and does not crash."""
    # 1. First registration
    payload1 = {
        "email": "duplicate@company.com",
        "password": "password123",
        "full_name": "User One",
        "company_name": "First Company",
    }
    response1 = api_client.post("/api/v1/auth/register", json=payload1)
    assert response1.status_code == 201

    # 2. Second registration with the same email (different company)
    payload2 = {
        "email": "duplicate@company.com",
        "password": "password456",
        "full_name": "User Two",
        "company_name": "Second Company",
    }
    response2 = api_client.post("/api/v1/auth/register", json=payload2)
    assert response2.status_code == 409
    assert response2.json()["detail"] == "Email already registered"


def test_registration_slug_collision_handled(api_client, db_session):
    """Verify slug generation generates unique slugs for same company name and handles collisions gracefully."""
    # 1. Register Company A with name "Unique Corp"
    payload1 = {
        "email": "owner@uniquecorp1.com",
        "password": "password123",
        "full_name": "Owner One",
        "company_name": "Unique Corp",
    }
    response1 = api_client.post("/api/v1/auth/register", json=payload1)
    assert response1.status_code == 201
    
    # 2. Register Company B with same name "Unique Corp" (different owner email)
    # The system should automatically suffix the slug to prevent constraint crash!
    payload2 = {
        "email": "owner@uniquecorp2.com",
        "password": "password123",
        "full_name": "Owner Two",
        "company_name": "Unique Corp",
    }
    response2 = api_client.post("/api/v1/auth/register", json=payload2)
    assert response2.status_code == 201

    # 3. Check database to verify both companies created with unique slugs
    with tenant_context(auth_mode="true"):
        companies = list(db_session.scalars(select(Company).where(Company.name == "Unique Corp")).all())
        assert len(companies) == 2
        slugs = [c.slug for c in companies]
        assert "unique-corp" in slugs
        # The other slug should have a random 6-character suffix, e.g. "unique-corp-xxxxxx"
        other_slug = [s for s in slugs if s != "unique-corp"][0]
        assert other_slug.startswith("unique-corp-")


def test_registration_under_rls(api_client, db_session):
    """Verify that registration works correctly under strict RLS environments."""
    # 1. Create a company in RLS mode
    with tenant_context(auth_mode="true"):
        co_existing = Company(name="Existing Corp", slug="existing-corp", status=CompanyStatus.ACTIVE)
        db_session.add(co_existing)
        db_session.commit()

    # 2. Register a new user and company via API. 
    # Even if RLS isolates existing-corp, register endpoint must check existing slugs/emails globally.
    payload = {
        "email": "newuser@corp.com",
        "password": "password123",
        "full_name": "New User",
        "company_name": "New Corp",
    }
    response = api_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201


def test_registration_multi_tenant_scenarios(api_client, db_session):
    """Verify that multiple successive registrations correctly partition users and companies under RLS."""
    # Register Company Alpha
    res_alpha = api_client.post("/api/v1/auth/register", json={
        "email": "admin@alpha.com",
        "password": "password123",
        "full_name": "Admin Alpha",
        "company_name": "Alpha Corp",
    })
    assert res_alpha.status_code == 201
    cid_alpha = res_alpha.json()["user"]["company_id"]

    # Register Company Beta
    res_beta = api_client.post("/api/v1/auth/register", json={
        "email": "admin@beta.com",
        "password": "password123",
        "full_name": "Admin Beta",
        "company_name": "Beta Corp",
    })
    assert res_beta.status_code == 201
    cid_beta = res_beta.json()["user"]["company_id"]

    # Verify RLS tenant isolation: Company Alpha user cannot read Company Beta records and vice-versa
    with tenant_context(tenant_id=cid_alpha):
        users_alpha = list(db_session.scalars(select(User)).all())
        user_emails = [u.email for u in users_alpha]
        assert "admin@alpha.com" in user_emails
        assert "admin@beta.com" not in user_emails

    with tenant_context(tenant_id=cid_beta):
        users_beta = list(db_session.scalars(select(User)).all())
        user_emails = [u.email for u in users_beta]
        assert "admin@beta.com" in user_emails
        assert "admin@alpha.com" not in user_emails
