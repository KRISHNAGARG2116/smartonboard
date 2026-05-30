# Multi-Tenant Database Row-Level Security (RLS) Verification Report
**Target Audience:** Future Developers & Core Engineering Team  
**Subject:** Technical Architecture, Root-Cause Analysis, and Verification of multi-tenant RLS Isolation.

---

## 1. Summary of the Original RLS Issue

During initial development of the multi-tenant SaaS recruiting platform, PostgreSQL **Row-Level Security (RLS)** was introduced to ensure strict tenant separation across shared databases. 

However, two major runtime issues were observed:
1. **The Transaction Commit Erasure**: After executing write operations, calling `db.commit()` terminated the database transaction and cleared transaction-scoped PostgreSQL session configuration variables (`app.company_id` and `app.auth_mode`). Subsequent reads or `db.refresh()` statements running in a new transaction failed with exceptions (such as `psycopg.errors.InsufficientPrivilege: new row violates row-level security policy`) or returned empty results because RLS variables were missing.
2. **The Registration Unique Collision Crash**: During the bootstrap process (such as user signup or checking unique company slugs), RLS was overly restrictive on the `companies` table. Because the tenant identifier was not yet available, the system checked for duplicate slugs under a restrictive context, returning zero matches and proceeding to attempt inserts that triggered database unique constraint violations.

---

## 2. Root Cause Analysis (RCA)

### Issue A: Transaction-Scoped Variables (`is_local=true`)
In the initial implementation, `set_tenant_context` applied tenant scoping using:
```sql
SELECT set_config('app.company_id', :company_id, true)
```
Setting the third parameter (`is_local`) to `true` scopes the session parameter to the **current transaction block only**. Once a transaction committed, PostgreSQL performed a cleanup, discarding these configurations. The subsequent statements (which run in a new transaction in SQLAlchemy's session lifecycle) executed in an unauthenticated database context.

### Issue B: The Connection Pool Reset Cache Bug
To avoid redundant `set_config` statements on every SQL execution, the active tenant context was cached in Python in SQLAlchemy's connection information dictionary (`connection.info`). 
However, when connections were returned to the SQLAlchemy `QueuePool`, connection reset routines (such as `RESET ALL` or transaction rollback) were executed by PostgreSQL, clearing all custom session variables. The Python-side `connection.info` remained cached. On connection checkout, the event listener saw the cached Python state, falsely assumed RLS was active, and skipped applying RLS, allowing queries to run in an unauthenticated state.

### Issue C: Overly Restrictive Companies RLS Policy
The RLS policy on the `companies` table did not evaluate the `app.auth_mode = 'true'` configuration bypass. When registration workflows attempted to query existing company slugs globally to prevent unique key constraint conflicts, the query returned no records, leading to key collision crashes.

---

## 3. Files Modified

The following files were modified or created to remediate these issues:

1. **[backend/db/session.py](file:///Users/krishnagarg/smartonboard-main/backend/db/session.py)**:
   * Replaced transaction-scoped setting with session-scoped setting (`is_local=false`).
   * Removed connection-level RLS parameter caching in `connection.info` to avoid pooling caching bugs.
   * Registered event listeners on class-level `Session` (`after_begin`) and `Engine` (`before_cursor_execute`) to enforce ContextVars-based context replication across all transactions and cursor executes.
2. **[backend/api/deps.py](file:///Users/krishnagarg/smartonboard-main/backend/api/deps.py)**:
   * Updated `get_current_user` and `get_tenant_db` dependency injections to safely manage the `ContextVars` lifecycle across async scopes.
3. **[backend/api/auth.py](file:///Users/krishnagarg/smartonboard-main/backend/api/auth.py)**:
   * Wrapped registration and login bootstrap workflows inside standard `with tenant_context(...)` scoping.
4. **[tests/conftest.py](file:///Users/krishnagarg/smartonboard-main/tests/conftest.py)**:
   * Setup standard transaction scopes (`autocommit=False`) instead of persistent connection-level wrapping to allow natural transaction boundaries.
   * Created a non-superuser database role `smartonboard_test_user` to reliably simulate and test RLS enforcement in test environments.
5. **[tests/test_tenant_rls.py](file:///Users/krishnagarg/smartonboard-main/tests/test_tenant_rls.py)**:
   * Wrote high-coverage integration tests validating commit survival, company isolation, and registration bootstrap visibility.

---

## 4. Migration Changes

We introduced a new Alembic migration:
* **Migration ID:** `002`
* **Filename:** `alembic/versions/002_fix_companies_rls_policy.py`

This migration dropped the original restrictive policy and replaced it with a policy checking the bypass parameter `app.auth_mode`:

```sql
-- UPGRADE
DROP POLICY IF EXISTS tenant_isolation_companies ON companies;

CREATE POLICY tenant_isolation_companies ON companies
FOR ALL
USING (
    id = NULLIF(current_setting('app.company_id', true), '')::uuid
    OR current_setting('app.auth_mode', true) = 'true'
)
WITH CHECK (
    id = NULLIF(current_setting('app.company_id', true), '')::uuid
    OR current_setting('app.auth_mode', true) = 'true'
);
```

---

## 5. Test Results Before vs. After Fix

### Before Fix
Tests failed during execution against PostgreSQL under standard RLS enforcement:
* `test_rls_commit_survival`: **FAIL** (`psycopg.errors.InsufficientPrivilege: new row violates row-level security policy`)
* `test_rls_strict_isolation`: **FAIL** (Company A was able to read Company B records due to stuck transaction boundaries)
* `test_registration_bootstrap_visibility`: **FAIL** (`psycopg.errors.UniqueViolation: duplicate key value violates unique constraint "companies_slug_key"`)

### After Fix
All integration tests pass flawlessly:
* `test_rls_context_vars`: **PASS**
* `test_rls_commit_survival`: **PASS**
* `test_rls_strict_isolation`: **PASS**
* `test_registration_bootstrap_visibility`: **PASS**

```text
tests/test_tenant_rls.py::test_rls_context_vars PASSED
tests/test_tenant_rls.py::test_rls_commit_survival PASSED
tests/test_tenant_rls.py::test_rls_strict_isolation PASSED
tests/test_tenant_rls.py::test_registration_bootstrap_visibility PASSED
============================== 4 passed in 0.17s ===============================
```

---

## 6. Verification Evidence

Verification has been conducted using standard `pytest` under a non-superuser database role (`smartonboard_test_user`). The non-superuser status ensures that PostgreSQL does not bypass RLS (as it does for superusers/owners), confirming that the isolation policies are active and enforced by the database engine.

All tables are successfully truncated in foreign-key reverse dependency order during the test teardown lifecycle to prevent cross-contamination:
```python
for table in ("applications", "candidates", "jobs", "users", "companies"):
    conn.execute(text(f"DELETE FROM {table}"))
```

---

## 7. Remaining Risks

1. **Background Tasks Scoping**:
   * *Description:* When spinning up tasks asynchronously (e.g. using Celery, multiprocessing, or asyncio background tasks), Python's `ContextVars` are isolated to their parent task loop.
   * *Risk:* Running background tasks that access the database without wrapping them in a `tenant_context` block will default to an empty context, causing RLS to hide records or block modifications.
   * *Action:* Future developers must decorate or wrap background tasks in `tenant_context(tenant_id=str(company_id))` explicitly.
2. **Superuser Database Connections**:
   * *Description:* PostgreSQL bypasses RLS policies entirely for superusers (e.g. the default docker-compose database user `smartonboard`).
   * *Risk:* If production application servers connect using superuser credentials, RLS is ignored, creating an accidental security vulnerability.
   * *Action:* Production database connections must connect using a standard, non-superuser role (similar to `smartonboard_test_user`) with RLS fully active.

---

## 8. Recommendations for the Next Milestone

Having verified that multi-tenant RLS isolation is robust and survives transaction boundaries, we recommend proceeding to the following milestones:

### Milestone 2: Production Authentication & Role-Based Access Control (RBAC)
* **Goal:** Implement secure `/auth/login` and `/auth/register` controllers returning signed JWTs containing `company_id`.
* **Details:** Write dependency injection logic that extracts `company_id` from JWT tokens and automatically scopes standard requests inside the backend routing layer.
* **Role Check:** Enforce RBAC permissions (`OWNER`, `RECRUITER`) across job creation and screening endpoints.
