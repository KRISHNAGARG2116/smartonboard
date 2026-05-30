import pytest
from sqlalchemy import select

from db.session import tenant_context, tenant_id_var, auth_mode_var
from models import Company, User, Job, Candidate, Application
from models.enums import CompanyStatus, UserRole, JobStatus, ApplicationStatus


def test_rls_context_vars():
    """Verify ContextVars set and reset logic via context manager."""
    assert tenant_id_var.get() == ""
    assert auth_mode_var.get() == "false"

    with tenant_context(tenant_id="123-abc", auth_mode="true"):
        assert tenant_id_var.get() == "123-abc"
        assert auth_mode_var.get() == "true"

    assert tenant_id_var.get() == ""
    assert auth_mode_var.get() == "false"


def test_rls_commit_survival(db_session):
    """Verify that tenant context survives commits and subsequent reads work perfectly."""
    # 1. Create a tenant company and owner user in auth bootstrap mode
    with tenant_context(auth_mode="true"):
        company = Company(name="Test Corp", slug="test-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        user = User(
            company_id=company.id,
            email="owner@testcorp.com",
            password_hash="dummyhash",
            full_name="Owner User",
            role=UserRole.OWNER,
        )
        db_session.add(user)
        db_session.commit()

    # 2. Scope the database operations to the created company
    with tenant_context(tenant_id=str(company.id)):
        # Create a Job
        job = Job(
            company_id=company.id,
            title="Senior QA Engineer",
            department="QA",
            description="Testing multi-tenant isolation",
            status=JobStatus.OPEN,
        )
        db_session.add(job)
        
        # In the original broken implementation, db.commit() terminated the transaction,
        # which cleared pg_config variables. The db.refresh(job) below would fail under RLS!
        db_session.commit()
        
        # Verify RLS context survives the commit and refresh succeeds
        db_session.refresh(job)
        assert job.title == "Senior QA Engineer"

        # Verify query reads also survive the commit
        queried_jobs = list(db_session.scalars(select(Job).where(Job.id == job.id)).all())
        assert len(queried_jobs) == 1
        assert queried_jobs[0].title == "Senior QA Engineer"


def test_rls_strict_isolation(db_session):
    """Verify strict isolation: Company A cannot see Company B's records under any circumstances."""
    # 1. Create two companies under auth bootstrap mode
    with tenant_context(auth_mode="true"):
        co_a = Company(name="Company A", slug="co-a", status=CompanyStatus.ACTIVE)
        co_b = Company(name="Company B", slug="co-b", status=CompanyStatus.ACTIVE)
        db_session.add(co_a)
        db_session.add(co_b)
        db_session.flush()

        # Create user owners
        owner_a = User(
            company_id=co_a.id,
            email="admin@a.com",
            password_hash="hash",
            full_name="Admin A",
            role=UserRole.OWNER,
        )
        owner_b = User(
            company_id=co_b.id,
            email="admin@b.com",
            password_hash="hash",
            full_name="Admin B",
            role=UserRole.OWNER,
        )
        db_session.add(owner_a)
        db_session.add(owner_b)
        db_session.commit()

    # 2. Scope to Company A and create Job A
    with tenant_context(tenant_id=str(co_a.id)):
        job_a = Job(
            company_id=co_a.id,
            title="Engineer A",
            department="Engineering",
            description="Acme Job A",
            status=JobStatus.OPEN,
        )
        db_session.add(job_a)
        db_session.commit()

    # 3. Scope to Company B and create Job B
    with tenant_context(tenant_id=str(co_b.id)):
        job_b = Job(
            company_id=co_b.id,
            title="Engineer B",
            department="Engineering",
            description="Acme Job B",
            status=JobStatus.OPEN,
        )
        db_session.add(job_b)
        db_session.commit()

    # 4. Under Company A context:
    # - Must see Job A.
    # - Must NOT see Job B.
    with tenant_context(tenant_id=str(co_a.id)):
        all_jobs = list(db_session.scalars(select(Job)).all())
        job_ids = [j.id for j in all_jobs]
        assert job_a.id in job_ids
        assert job_b.id not in job_ids

        # Attempting to fetch Job B directly should return None due to RLS
        job_b_hidden = db_session.scalar(select(Job).where(Job.id == job_b.id))
        assert job_b_hidden is None

    # 5. Under Company B context:
    # - Must see Job B.
    # - Must NOT see Job A.
    with tenant_context(tenant_id=str(co_b.id)):
        all_jobs = list(db_session.scalars(select(Job)).all())
        job_ids = [j.id for j in all_jobs]
        assert job_b.id in job_ids
        assert job_a.id not in job_ids

        job_a_hidden = db_session.scalar(select(Job).where(Job.id == job_a.id))
        assert job_a_hidden is None


def test_registration_bootstrap_visibility(db_session):
    """Verify that auth_mode='true' allows viewing all companies/slugs globally during register/login."""
    # 1. Create a company in bootstrap mode
    with tenant_context(auth_mode="true"):
        co_existing = Company(name="Original Company", slug="original-company", status=CompanyStatus.ACTIVE)
        db_session.add(co_existing)
        db_session.commit()

    # 2. Attempt registration checks:
    # - Without auth_mode="true" (isolated): cannot see original-company slug.
    with tenant_context(auth_mode="false"):
        co_slug = db_session.scalar(select(Company.slug).where(Company.slug == "original-company"))
        assert co_slug is None  # RLS filters it out!

    # - With auth_mode="true" (bootstrap mode): can see original-company slug to prevent collision!
    with tenant_context(auth_mode="true"):
        co_slug = db_session.scalar(select(Company.slug).where(Company.slug == "original-company"))
        assert co_slug == "original-company"
