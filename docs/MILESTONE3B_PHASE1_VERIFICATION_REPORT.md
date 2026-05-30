# Verification Report: Milestone 3B Phase 1 — Ingress Protection & Security Hardening

This engineering report documents the successful implementation, testing, and security validation of **Milestone 3B Phase 1** (Ingress Protection & Security Hardening). All API endpoints are rate-limited, large files are rejected before parsing, production environment startup is strictly checked, and 100% of the integration test suite passes green.

---

## 1. What Was Changed & Files Modified

We integrated rate-limiting configurations, payload validations, and environment checks across the following backend files:

| File Path | Description of Changes |
| :--- | :--- |
| [backend/core/limiter.py](file:///Users/krishnagarg/smartonboard-main/backend/core/limiter.py) | • Created a global `limiter` instance using `slowapi`. <br>• Wrote a custom `tenant_rate_limit_key` function that uses a decoded JWT `company_id` claim if authenticated, falling back to client IP address for unauthenticated requests. |
| [backend/server.py](file:///Users/krishnagarg/smartonboard-main/backend/server.py) | • Mounted `slowapi` exception handler and global rate-limiter state onto the FastAPI app instance.<br>• Decorated `/api/onboard`, `/api/screen`, `/api/screen/upload`, and `/api/recruit` with rate limits of `5/minute`.<br>• Enforced a strict maximum file size of 5MB (`MAX_FILE_SIZE = 5 * 1024 * 1024` bytes) on PDF and text resume uploads. Oversized payloads are rejected before parsing and return `413 Payload Too Large` responses. |
| [backend/api/auth.py](file:///Users/krishnagarg/smartonboard-main/backend/api/auth.py) | • Enforced rate limits of `5/minute` on `/register`, `10/minute` on `/login`, and `100/minute` on `/me`. |
| [backend/core/config.py](file:///Users/krishnagarg/smartonboard-main/backend/core/config.py) | • Added strict boot checks. If the environment is production (`os.getenv("ENV") == "production"` or `os.getenv("FASTAPI_ENV") == "production"`), the application throws a `ValueError` immediately upon settings instantiation if `JWT_SECRET_KEY` is missing/defaulted, `GROQ_API_KEY` is missing, or `DATABASE_URL` is missing, crashing the startup sequence. |
| [tests/conftest.py](file:///Users/krishnagarg/smartonboard-main/tests/conftest.py) | • Set `limiter.enabled = False` globally for all unit/integration tests by default to prevent false-positives from successive test requests, while keeping it configurable for specific testing. |
| [tests/test_ingress_security.py](file:///Users/krishnagarg/smartonboard-main/tests/test_ingress_security.py) | • Authored the automated ingress security test suite validating `slowapi` rate limiting (429), upload size limits (413), and strict production boot requirements. |

---

## 2. Ingress Safeguards & Validation Architecture

### 1. Tenant-Aware API Rate Limiting
* **Goal:** Protect platform cost variables and backend CPU limits from malicious overload.
* **Mechanism:** The `tenant_rate_limit_key` utility decodes incoming JWT tokens securely. If a valid `company_id` exists in the token, the rate limit is isolated per-tenant. Otherwise, the limiter isolates requests by client IP address. Rate limits are set at:
  * Authentication (Register): `5/minute`
  * Authentication (Login): `10/minute`
  * AI Evaluations & Document Generation: `5/minute`
  * Candidate Resume Uploads: `5/minute`

### 2. Early payload Rejection (5MB Upload Limit)
* **Goal:** Block Zip Bombs and RAM resource exhaustion.
* **Mechanism:** We execute a two-layer validation check:
  1. **Pre-Read Header Check:** Inspect request header `Content-Length` before loading bytes. If it exceeds 5MB, immediately abort and throw `413 Payload Too Large`.
  2. **Read Limit Validation:** Inspect `len(content)` after reading the uploaded file to ensure no one bypasses checks by omitting headers.

### 3. Strict Production Boot Validation
* **Goal:** Prevent misconfigured, weak, or un-secure deployments in production.
* **Mechanism:** Upon initialization of the `Settings` class, if production mode is active, the app strictly validates environment keys:
  - `DATABASE_URL` must be set.
  - `JWT_SECRET_KEY` must be set and cannot be the default fallback value `"change-me-in-production"`.
  - `GROQ_API_KEY` must be set.
  Violations throw a loud `ValueError` at the configuration layer, halting FastAPI startup before mounting routers or engines.

---

## 3. Test Execution Results

All **17 integration tests** (RLS, registration, RBAC security, and ingress protection) pass successfully:

```text
============================= test session starts ==============================
platform darwin -- Python 3.11.5, pytest-9.0.3, pluggy-1.6.0 -- /Users/krishnagarg/smartonboard-main/.venv/bin/python3.11
cachedir: .pytest_cache
rootdir: /Users/krishnagarg/smartonboard-main
configfile: pyproject.toml
plugins: asyncio-1.4.0, langsmith-0.8.7, anyio-4.13.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 17 items

tests/test_auth_registration.py::test_registration_success PASSED
tests/test_auth_registration.py::test_registration_duplicate_email PASSED
tests/test_auth_registration.py::test_registration_slug_collision_handled PASSED
tests/test_auth_registration.py::test_registration_under_rls PASSED
tests/test_auth_registration.py::test_registration_multi_tenant_scenarios PASSED
tests/test_auth_security.py::test_company_suspension_blocks_protected_routes PASSED
tests/test_auth_security.py::test_rbac_require_owner_enforcement PASSED
tests/test_auth_security.py::test_rbac_require_recruiter_enforcement PASSED
tests/test_auth_security.py::test_login_timing_decoy_triggered PASSED
tests/test_ingress_security.py::test_api_rate_limiting_triggered PASSED
tests/test_ingress_security.py::test_upload_size_limit_screen_upload PASSED
tests/test_ingress_security.py::test_upload_size_limit_recruit PASSED
tests/test_ingress_security.py::test_production_secrets_validation PASSED
tests/test_tenant_rls.py::test_rls_context_vars PASSED
tests/test_tenant_rls.py::test_rls_commit_survival PASSED
tests/test_tenant_rls.py::test_rls_strict_isolation PASSED
tests/test_tenant_rls.py::test_registration_bootstrap_visibility PASSED

======================= 17 passed, 5 warnings in 10.61s ========================
```

---

## 4. Verification Evidence & Hardening Protections

1. **Rate Limiting Proof:** Sending more than 10 successive requests to `/api/v1/auth/login` triggers `429 Too Many Requests` (detail: `"Rate limit exceeded"`).
2. **Payload Size Proof:** Sending a 6MB mock PDF to `/api/screen/upload` or `/api/recruit` returns `413 Payload Too Large` (detail: `"File too large. Maximum allowed size is 5 MB."`).
3. **Production Validation Proof:** Setting `ENV=production` while unsetting required keys or using insecure defaults triggers `ValueError` and prevents the application from booting.
