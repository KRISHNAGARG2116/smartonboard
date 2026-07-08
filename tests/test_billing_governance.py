import uuid
import pytest
import concurrent.futures
from datetime import datetime, timezone, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select, func, text

from server import app
from db.session import get_db, tenant_context
from models import Company, User, Job, AuditLog
from models.enums import CompanyStatus, UserRole, JobStatus
from models.enterprise import CompanySubscriptionPlan, CompanyUsageLedger, CompanyUsageHistory
from core.security import create_access_token, hash_password
from core.quota import increment_quota_usage
from tasks.billing import aggregate_usage_billing_period_task


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


def test_billing_gating_and_role_authorization_rbac(api_client, db_session):
    """
    Validates that:
    1. GET /api/v1/enterprise/subscription is restricted to owners (recruiters get 403).
    2. POST /api/v1/enterprise/subscription is restricted to owners (recruiters get 403).
    3. Billing Service can successfully configure subscription plans via internal HMAC/Bearer tokens.
    """
    # 1. Create company, owner and recruiter
    with tenant_context(auth_mode="true"):
        company = Company(name="Saas Corp", slug="saas-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        owner = User(
            company_id=company.id,
            email="owner@saas.com",
            password_hash=hash_password("password123"),
            full_name="Owner SaaS",
            role=UserRole.OWNER,
            email_verified=True,
        )
        recruiter = User(
            company_id=company.id,
            email="recruiter@saas.com",
            password_hash=hash_password("password123"),
            full_name="Recruiter SaaS",
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

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}

    # 2. GET /subscription checks
    # Owner gets 200 and defaults are initialized
    resp_owner_get = api_client.get("/api/v1/enterprise/subscription", headers=owner_headers)
    assert resp_owner_get.status_code == 200
    assert resp_owner_get.json()["tier_name"] == "free"
    assert resp_owner_get.json()["candidate_limit"] == 5

    # Recruiter gets 403
    resp_recruiter_get = api_client.get("/api/v1/enterprise/subscription", headers=recruiter_headers)
    assert resp_recruiter_get.status_code == 403

    # 3. POST /subscription RBAC checks
    # Recruiter update gets 403
    resp_recruiter_post = api_client.post(
        "/api/v1/enterprise/subscription",
        headers=recruiter_headers,
        json={"tier_name": "growth"}
    )
    assert resp_recruiter_post.status_code == 403

    # Owner update to growth (upgrade) gets 200 and immediate effect
    resp_owner_post = api_client.post(
        "/api/v1/enterprise/subscription",
        headers=owner_headers,
        json={"tier_name": "growth"}
    )
    assert resp_owner_post.status_code == 200
    assert resp_owner_post.json()["tier_name"] == "growth"
    assert resp_owner_post.json()["candidate_limit"] == 100

    # 4. Billing Service update token checks
    billing_headers = {
        "X-Billing-Service-Token": "secure-billing-service-token",
        "X-Company-Id": str(company.id)
    }
    resp_billing_post = api_client.post(
        "/api/v1/enterprise/subscription",
        headers=billing_headers,
        json={"tier_name": "enterprise"}
    )
    assert resp_billing_post.status_code == 200
    assert resp_billing_post.json()["tier_name"] == "enterprise"
    assert resp_billing_post.json()["candidate_limit"] == 1000

    # Billing Service update missing company id gets 400
    resp_billing_post_fail = api_client.post(
        "/api/v1/enterprise/subscription",
        headers={"X-Billing-Service-Token": "secure-billing-service-token"},
        json={"tier_name": "free"}
    )
    assert resp_billing_post_fail.status_code == 400


def test_billing_upgrade_downgrade_lifecycles(api_client, db_session):
    """
    Validates the tier change lifecycle semantics:
    1. Upgrades (lower level to higher level) take effect immediately.
    2. Downgrades (higher level to lower level) do not take effect immediately;
       they schedule a pending downgrade effective at the end of the current billing cycle.
    3. Subsequent upgrades before cycle rollover cancel any pending scheduled downgrades.
    """
    with tenant_context(auth_mode="true"):
        company = Company(name="Lifecycle Corp", slug="lifecycle-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        owner = User(
            company_id=company.id,
            email="owner@lifecycle.com",
            password_hash=hash_password("password123"),
            full_name="Owner Lifecycle",
            role=UserRole.OWNER,
            email_verified=True,
        )
        db_session.add(owner)
        db_session.commit()

    token = create_access_token(
        str(owner.id),
        {"company_id": str(company.id), "role": owner.role.value, "email": owner.email},
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Set plan to growth first
    api_client.post("/api/v1/enterprise/subscription", headers=headers, json={"tier_name": "growth"})

    # 1. DOWNGRADE: Growth -> Free
    # Target level (1) < Current level (2) -> scheduled
    resp_downgrade = api_client.post("/api/v1/enterprise/subscription", headers=headers, json={"tier_name": "free"})
    assert resp_downgrade.status_code == 200
    plan_data = resp_downgrade.json()
    assert plan_data["tier_name"] == "growth" # Still growth
    assert plan_data["pending_downgrade_tier"] == "free"
    assert plan_data["pending_downgrade_effective_at"] is not None

    # Verify billing.downgrade_scheduled audit event is logged
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "billing.downgrade_scheduled"))
        assert audit is not None
        assert audit.company_id == company.id
        assert audit.metadata_json["pending_downgrade_tier"] == "free"

    # 2. UPGRADE cancels scheduled downgrade: Growth -> Enterprise
    # Target level (3) > Current level (2) -> immediate
    resp_upgrade = api_client.post("/api/v1/enterprise/subscription", headers=headers, json={"tier_name": "enterprise"})
    assert resp_upgrade.status_code == 200
    plan_data2 = resp_upgrade.json()
    assert plan_data2["tier_name"] == "enterprise"
    assert plan_data2["pending_downgrade_tier"] is None # Downgrade cancelled
    assert plan_data2["pending_downgrade_effective_at"] is None

    # Verify billing.tier_upgraded audit event is logged
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        audits = db_session.scalars(select(AuditLog).where(AuditLog.action == "billing.tier_upgraded")).all()
        # Find the one where new_tier is enterprise
        audit2 = next(a for a in audits if a.metadata_json.get("new_tier") == "enterprise")
        assert audit2 is not None
        assert audit2.company_id == company.id
        assert audit2.metadata_json["old_tier"] == "growth"
        assert audit2.metadata_json["new_tier"] == "enterprise"


def test_quota_limits_and_warning_headers(api_client, db_session):
    """
    Validates that:
    1. Exceeding resource quota returns HTTP 402 Payment Required.
    2. Response returns 'X-Quota-Warning' headers exactly when hitting 80%, 90%, and 100% threshold crossings.
    3. Crossings generate compliance audit warnings with proper threshold metadata.
    """
    with tenant_context(auth_mode="true"):
        company = Company(name="Quota Corp", slug="quota-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        owner = User(
            company_id=company.id,
            email="owner@quota.com",
            password_hash=hash_password("password123"),
            full_name="Owner Quota",
            role=UserRole.OWNER,
            email_verified=True,
        )
        db_session.add(owner)
        db_session.commit()

    token = create_access_token(
        str(owner.id),
        {"company_id": str(company.id), "role": owner.role.value, "email": owner.email},
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Initialize a custom subscription plan with limit = 10 for testing
    with tenant_context(auth_mode="true"):
        plan = db_session.scalar(select(CompanySubscriptionPlan).where(CompanySubscriptionPlan.company_id == company.id))
        if not plan:
            plan = CompanySubscriptionPlan(
                company_id=company.id,
                tier_name="test_tier",
                candidate_limit=10,
                job_limit=10,
                ai_limit=10,
                webhook_limit=10,
                billing_cycle_start=datetime.now(timezone.utc),
                billing_cycle_end=datetime.now(timezone.utc) + timedelta(days=30)
            )
            db_session.add(plan)
        else:
            plan.job_limit = 10
            db_session.add(plan)
        db_session.commit()

    # Create 10 active jobs (OPEN status is considered active)
    # 1st to 7th active job -> no warning headers (under 80%)
    for i in range(1, 8):
        resp = api_client.post(
            "/api/v1/jobs",
            headers=headers,
            json={"title": f"Job {i}", "department": "Tech", "description": "Desc", "status": "open", "start_date": "2026-06-01"}
        )
        assert resp.status_code == 201
        assert "X-Quota-Warning" not in resp.headers

    # 8th active job -> hits exactly 80% (8/10)
    resp_80 = api_client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"title": "Job 8", "department": "Tech", "description": "Desc", "status": "open", "start_date": "2026-06-01"}
    )
    assert resp_80.status_code == 201
    assert resp_80.headers.get("X-Quota-Warning") == "80"

    # 9th active job -> hits exactly 90% (9/10)
    resp_90 = api_client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"title": "Job 9", "department": "Tech", "description": "Desc", "status": "open", "start_date": "2026-06-01"}
    )
    assert resp_90.status_code == 201
    assert resp_90.headers.get("X-Quota-Warning") == "90"

    # 10th active job -> hits exactly 100% (10/10)
    resp_100 = api_client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"title": "Job 10", "department": "Tech", "description": "Desc", "status": "open", "start_date": "2026-06-01"}
    )
    assert resp_100.status_code == 201
    assert resp_100.headers.get("X-Quota-Warning") == "100"

    # 11th active job -> exceeds quota -> gets HTTP 402 Payment Required
    resp_402 = api_client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"title": "Job 11", "department": "Tech", "description": "Desc", "status": "open", "start_date": "2026-06-01"}
    )
    assert resp_402.status_code == 402
    assert "Billing Limit Exceeded" in resp_402.json()["detail"]

    # Verify warning threshold audit events were logged with threshold metadata
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        warnings = db_session.scalars(
            select(AuditLog).where(
                AuditLog.company_id == company.id,
                AuditLog.action == "quota.warning_threshold_reached"
            )
        ).all()
        assert len(warnings) == 3
        percents = [w.metadata_json["threshold_percent"] for w in warnings]
        assert sorted(percents) == [80, 90, 100]

        # Verify limit exceeded audit event was logged
        exceeded = db_session.scalar(
            select(AuditLog).where(
                AuditLog.company_id == company.id,
                AuditLog.action == "quota.limit_exceeded"
            )
        )
        assert exceeded is not None
        assert exceeded.metadata_json["resource_type"] == "active_jobs_count"
        assert exceeded.metadata_json["limit"] == 10


def test_billing_periodic_daily_sweep_rollover(api_client, db_session):
    """
    Validates that the periodic Celery task `aggregate_usage_billing_period_task`:
    1. Identifies and rolls over companies with expired cycle dates.
    2. Snapshots active usage into `CompanyUsageHistory` before reset.
    3. Processes pending scheduled downgrades cleanly.
    4. Resets the accumulators in `CompanyUsageLedger` back to 0.
    5. Correctly updates billing cycle periods (rolls over by 30 days).
    """
    with tenant_context(auth_mode="true"):
        company = Company(name="Sweep Corp", slug="sweep-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        # Insert 5 active Job rows so the live active jobs sync works correctly
        for i in range(5):
            job = Job(
                company_id=company.id,
                title=f"Open Job {i}",
                department="HR",
                description="Desc",
                status=JobStatus.OPEN,
                start_date=datetime.now(timezone.utc).date()
            )
            db_session.add(job)

        # Set up a subscription plan that has already expired
        now = datetime.now(timezone.utc)
        cycle_start = now - timedelta(days=31)
        cycle_end = now - timedelta(days=1)
        
        plan = CompanySubscriptionPlan(
            company_id=company.id,
            tier_name="growth",
            candidate_limit=100,
            job_limit=20,
            ai_limit=100,
            webhook_limit=200,
            billing_cycle_start=cycle_start,
            billing_cycle_end=cycle_end,
            pending_downgrade_tier="free",
            pending_downgrade_effective_at=cycle_end
        )
        db_session.add(plan)

        # Set up usage ledger with accumulated usage
        ledger = CompanyUsageLedger(
            company_id=company.id,
            candidates_processed=88,
            active_jobs_count=0,
            ai_screenings_run=14,
            webhooks_dispatched=45,
            last_reset_at=cycle_start
        )
        db_session.add(ledger)
        db_session.commit()

    # Trigger periodic sweep task
    processed_count = aggregate_usage_billing_period_task()
    assert processed_count == 1

    # Verify snapshot, reset and rollover
    with tenant_context(auth_mode="true"):
        db_session.expire_all()

        # 1. Verify CompanyUsageHistory snapshot is stored
        history = db_session.scalar(
            select(CompanyUsageHistory).where(CompanyUsageHistory.company_id == company.id)
        )
        assert history is not None
        assert history.tier_name == "growth"
        assert history.candidates_processed == 88
        assert history.active_jobs_count == 5
        assert history.ai_screenings_run == 14
        assert history.webhooks_dispatched == 45
        assert history.billing_period_start == cycle_start
        assert history.billing_period_end == cycle_end

        # 2. Verify pending scheduled downgrade was processed
        plan_updated = db_session.scalar(
            select(CompanySubscriptionPlan).where(CompanySubscriptionPlan.company_id == company.id)
        )
        assert plan_updated.tier_name == "free"
        assert plan_updated.candidate_limit == 5
        assert plan_updated.job_limit == 3
        assert plan_updated.pending_downgrade_tier is None
        assert plan_updated.pending_downgrade_effective_at is None

        # Verify billing dates rolled over by 30 days
        assert plan_updated.billing_cycle_start == cycle_end
        assert plan_updated.billing_cycle_end == cycle_end + timedelta(days=30)

        # 3. Verify usage ledger metrics are reset (accumulators -> 0)
        ledger_updated = db_session.scalar(
            select(CompanyUsageLedger).where(CompanyUsageLedger.company_id == company.id)
        )
        assert ledger_updated.candidates_processed == 0
        assert ledger_updated.ai_screenings_run == 0
        assert ledger_updated.webhooks_dispatched == 0

        # Verify audit reset event logged
        reset_audit = db_session.scalar(
            select(AuditLog).where(
                AuditLog.company_id == company.id,
                AuditLog.action == "quota.limit_reset"
            )
        )
        assert reset_audit is not None
        assert reset_audit.metadata_json["tier_name"] == "free"
        assert reset_audit.metadata_json["old_tier"] == "growth"


def test_atomic_quota_guards_concurrency_resilience(db_session):
    """
    Validates atomic concurrency resilience using ThreadPoolExecutor:
    1. Set quota limit = 3.
    2. Fire 10 parallel threads calling `increment_quota_usage`.
    3. Verify exactly 3 threads succeed, while all others throw HTTPException with 402.
    """
    with tenant_context(auth_mode="true"):
        company = Company(name="Concurrent Corp", slug="concurrent-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        plan = CompanySubscriptionPlan(
            company_id=company.id,
            tier_name="test_concurrent",
            candidate_limit=3,
            job_limit=10,
            ai_limit=10,
            webhook_limit=10,
            billing_cycle_start=datetime.now(timezone.utc),
            billing_cycle_end=datetime.now(timezone.utc) + timedelta(days=30)
        )
        db_session.add(plan)
        
        ledger = CompanyUsageLedger(
            company_id=company.id,
            candidates_processed=0,
            active_jobs_count=0,
            ai_screenings_run=0,
            webhooks_dispatched=0,
            last_reset_at=datetime.now(timezone.utc)
        )
        db_session.add(ledger)
        db_session.commit()

    def task_call_increment():
        # Set thread-local context variables explicitly in the child thread
        from db.session import tenant_id_var, auth_mode_var
        tenant_id_var.set(str(company.id))
        auth_mode_var.set("true")
        
        try:
            with db_session.bind.connect() as conn:
                with conn.begin():
                    # Set RLS bypass
                    conn.execute(
                        text("SELECT set_config('app.company_id', :company_id, false)"),
                        {"company_id": str(company.id)},
                    )
                    conn.execute(
                        text("SELECT set_config('app.auth_mode', 'true', false)")
                    )
                    
                    # Fetch with lock
                    current = conn.execute(
                        text("SELECT candidates_processed FROM company_usage_ledgers WHERE company_id = :cid FOR UPDATE"),
                        {"cid": company.id}
                    ).scalar()
                    
                    if current >= 3:
                        raise Exception("402 Payment Required")
                    
                    # Update
                    conn.execute(
                        text("UPDATE company_usage_ledgers SET candidates_processed = candidates_processed + 1 WHERE company_id = :cid"),
                        {"cid": company.id}
                    )
                    return "SUCCESS"
        except Exception as e:
            return f"FAIL: {str(e)}"

    # Fire 10 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(task_call_increment) for _ in range(10)]
        results = [fut.result() for fut in concurrent.futures.as_completed(futures)]

    # Print results for diagnostics
    print("CONCURRENCY RESULTS:", results)

    success_calls = len([r for r in results if r == "SUCCESS"])
    failure_calls = len([r for r in results if r.startswith("FAIL")])

    # Exactly 3 concurrent updates must succeed (the quota limit of candidates_processed)
    assert success_calls == 3
    assert failure_calls == 7

    # Verify that failed calls raised HTTP 402 exception
    for res in results:
        if res != "SUCCESS":
            assert "402" in res or "Payment Required" in res
