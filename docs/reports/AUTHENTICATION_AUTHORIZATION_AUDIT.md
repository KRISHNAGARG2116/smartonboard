# Authentication & Authorization Security Audit Report

**Audited By:** SmartOnboard Agentic AI Security Auditor  
**Audit Date:** 2026-06-09  
**Target Codebase:** SmartOnboard backend services (`smartonboard-main`)  
**Overall Verdict:** ⚠️ PARTIAL COMPLIANCE (Contains Critical Security Gaps)

---

## 1. Authentication System Overview

SmartOnboard uses a custom JSON Web Token (JWT) authentication system designed to isolate recruiters, candidates, and portal users securely.

### JWT Types and Structures
* **Recruiter JWT Access Token:** Issued upon email/password or SSO login.
  * **Payload Claims:**
    * `sub`: User UUID (`str`)
    * `company_id`: Company UUID (`str`)
    * `role`: User role value (e.g. `owner`, `recruiter`)
    * `email`: User email (`str`)
    * `session_id`: User session UUID (`str`)
    * `jti`: JWT ID UUID (`str`)
    * `exp`: Token expiration timestamp (`int`)
* **Candidate JWT Access Token:** Issued upon candidate registration/login.
  * **Payload Claims:**
    * `sub`: User UUID (`str`)
    * `company_id`: `None` (candidates are tenantless)
    * `role`: `"candidate"`
    * `email`: Candidate email (`str`)
    * `session_id`: User session UUID (`str`)
    * `jti`: JWT ID UUID (`str`)
    * `exp`: Token expiration timestamp (`int`)
* **Portal JWT Access Token:** Used for the legacy employee onboarding portal.
  * **Payload Claims:**
    * `sub`: Employee UUID (`str`)
    * `company_id`: Company UUID (`str`)
    * `scopes`: Allowed scopes (e.g. `["onboarding:read", "onboarding:write"]`)
    * `type`: `"portal"`
    * `jti`: JWT ID UUID (`str`)
    * `exp`: Token expiration timestamp (`int`)

### Session Management & Transport
* **Access Tokens:** Transmitted via HTTP `Authorization: Bearer <token>` headers.
* **Refresh Tokens:** Transmitted via an HTTP-Only, Secure, SameSite=Lax cookie named `refresh_token`, or optionally in the body of `/refresh` POST requests. They are verified against hashes in the database to detect replay attacks.

---

## 2. Key Security Code Locations

### 2.1 Login Implementation Locations
Recruiter and candidate login flows are segregated across different endpoints:
* **Recruiter Email/Password Login:** POST `/api/v1/auth/login` implemented in [api.auth.login](file:///Users/krishnagarg/smartonboard-main/backend/api/auth.py#L279-L382).
* **Candidate Email/Password Login:** POST `/api/v1/auth/login/candidate` implemented in [api.candidate_auth.login_candidate](file:///Users/krishnagarg/smartonboard-main/backend/api/candidate_auth.py#L125-L214).
* **SAML2 ACS Login:** POST `/api/v1/auth/sso/acs` implemented in [api.sso.sso_acs](file:///Users/krishnagarg/smartonboard-main/backend/api/sso.py#L74-L230).
* **OIDC Callback Login:** POST `/api/v1/auth/oidc/callback` implemented in [api.sso.oidc_callback](file:///Users/krishnagarg/smartonboard-main/backend/api/sso.py#L232-L336).
* **Onboarding Portal Authentication:** POST `/onboarding/portal/authenticate` implemented in [api.employees.authenticate_portal](file:///Users/krishnagarg/smartonboard-main/backend/api/employees.py#L284-L370).

### 2.2 Password Validation Locations
Passwords are validated using `pwd_context.verify()` from `passlib.context` using `bcrypt` in [core.security.verify_password](file:///Users/krishnagarg/smartonboard-main/backend/core/security.py#L16-L17):
```python
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```
* **Recruiter Validation:** [api/auth.py:334](file:///Users/krishnagarg/smartonboard-main/backend/api/auth.py#L334):
```python
    if not verify_password(body.password, user.password_hash):
```
* **Candidate Validation:** [api/candidate_auth.py:167](file:///Users/krishnagarg/smartonboard-main/backend/api/candidate_auth.py#L167):
```python
    if not verify_password(body.password, user.password_hash):
```
* **Timing Attack Prevention:** In both endpoints, if a user profile is not found, `verify_password(body.password, dummy_hash)` is invoked to ensure uniform response latency.

### 2.3 JWT Generation Locations
JWTs are generated in [core.security.create_access_token](file:///Users/krishnagarg/smartonboard-main/backend/core/security.py#L20-L27) and [create_refresh_token](file:///Users/krishnagarg/smartonboard-main/backend/core/security.py#L30-L37):
```python
def create_access_token(subject: str, claims: dict[str, Any]) -> str:
    import uuid
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {**claims, "sub": subject, "exp": expire}
    if "jti" not in payload:
        payload["jti"] = str(uuid.uuid4())
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
```
These are orchestrated by `create_user_session_and_tokens` in [api/auth.py:38-101](file:///Users/krishnagarg/smartonboard-main/backend/api/auth.py#L38-L101), which persists sessions in the `UserSession` table.

### 2.4 JWT Verification Locations
Verification takes place in [api/deps.py](file:///Users/krishnagarg/smartonboard-main/backend/api/deps.py) via three core dependencies:
1. **Recruiter JWT Verification:** `get_current_user` ([deps.py:19-80](file:///Users/krishnagarg/smartonboard-main/backend/api/deps.py#L19-L80))
   * Decodes access token via `decode_access_token(credentials.credentials)`.
   * Forbids candidate access: `if role == UserRole.CANDIDATE.value: raise HTTPException(403)`.
   * Asserts token JTI is not in the `RevokedToken` blacklist table.
   * Asserts the associated `UserSession` is active and not expired.
   * Sets the connection-level PostgreSQL Row-Level Security (RLS) company context.
2. **Candidate JWT Verification:** `get_current_candidate` ([deps.py:83-145](file:///Users/krishnagarg/smartonboard-main/backend/api/deps.py#L83-L145))
   * Decodes access token, asserts `role == UserRole.CANDIDATE.value`.
   * Bypasses RLS scope (`with tenant_context(auth_mode="true"):`) to query the candidate user.
3. **Portal JWT Verification:** `get_portal_session` ([deps.py:174-219](file:///Users/krishnagarg/smartonboard-main/backend/api/deps.py#L174-L219))
   * Decodes token, asserts `token_type == "portal"`.
   * Bypasses RLS to assert associated `OnboardingPortalToken` is active.

### 2.5 Refresh Token Handling Locations
Refresh token logic is implemented in POST `/api/v1/auth/refresh` at [api/auth.py:518-645](file:///Users/krishnagarg/smartonboard-main/backend/api/auth.py#L518-L645).
* Extracts refresh token from body or cookie.
* Verifies signature and retrieves session from DB.
* **Replay Attack/Reuse Protection:** Hashes the incoming refresh token and compares it to `session.refresh_token_hash`. If they do not match, a token replay attack is assumed. The entire session is revoked (`session.is_revoked = True`), the cookie is deleted, and a security audit log event is triggered.
```python
    incoming_hash = hashlib.sha256(token.encode()).hexdigest()
    if session.refresh_token_hash != incoming_hash:
        # REPLAY ATTACK: Revoke entire session
        session.is_revoked = True
        db.add(session)
        db.commit()
        response.delete_cookie("refresh_token")
        # Audit log replay attack
        ...
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected. Session revoked.")
```

### 2.6 Logout Implementation
Logout is handled in POST `/api/v1/auth/logout` at [api/auth.py:647-726](file:///Users/krishnagarg/smartonboard-main/backend/api/auth.py#L647-L726).
* Extracts the access token `jti` and session ID.
* Blacklists the access token JTI by writing it to `RevokedToken` (with the token's expiration timestamp).
* Revokes the active session: `session.is_revoked = True`.
* Deletes the `refresh_token` cookie from the client response.

---

## 3. Authorization Models

SmartOnboard combines three authorization mechanisms: Role-Based Access Control (RBAC), Row-Level Security (RLS), and Application-Level Ownership Checks.

### 3.1 Role-Based Access Control (RBAC)
User roles are defined in the `UserRole` enum (`CANDIDATE`, `RECRUITER`, `OWNER`).
Enforced at endpoint route dependencies via `deps.RoleChecker` ([deps.py:161-171](file:///Users/krishnagarg/smartonboard-main/backend/api/deps.py#L161-L171)):
* `RequireOwner`: strictly limits access to users with the `OWNER` role.
* `RequireRecruiter`: allows both `OWNER` and `RECRUITER` roles.
* `CurrentCandidate` / `VerifiedCandidate`: limits access to `CANDIDATE` roles.

### 3.2 Row-Level Security (RLS)
Database isolation is enforced at the PostgreSQL level.
* Active policies restrict queries to rows where `company_id = current_setting('app.company_id')`.
* Managed in [db/session.py](file:///Users/krishnagarg/smartonboard-main/backend/db/session.py) via SQLAlchemy session listeners (`after_begin` and `before_cursor_execute`).
* When `get_current_user` is resolved, the session automatically triggers:
```sql
SELECT set_config('app.company_id', :company_id, false);
SELECT set_config('app.auth_mode', 'false', false);
```
* Candidate endpoints do not have a `company_id` partition and bypass company-level RLS using `with tenant_context(auth_mode="true"):`.

### 3.3 Ownership-Based Authorization
Because candidates bypass DB RLS, the application logic explicitly enforces resource ownership checks.
* **Resume Actions:** `toggle-active` and `delete` in [api/candidate_resumes.py](file:///Users/krishnagarg/smartonboard-main/backend/api/candidate_resumes.py) filter query by candidate ID:
```python
select(CandidateResume).where(
    CandidateResume.id == resume_id,
    CandidateResume.user_id == current_candidate.id
)
```
* **Application/Interview Actions:** [api/candidate_applications.py](file:///Users/krishnagarg/smartonboard-main/backend/api/candidate_applications.py) and [api/candidate_interviews.py](file:///Users/krishnagarg/smartonboard-main/backend/api/candidate_interviews.py) verify that the resource candidate email matches the current candidate's email:
```python
if not app.candidate or app.candidate.email != current_candidate.email.lower():
    raise HTTPException(403)
```

---

## 4. Protected Endpoints Verification Matrix

All endpoints registered under `v1_router` in `backend/api/router.py` were audited.

| Route | Method | File | Authentication Dependency | Authorization Check | Verdict |
|---|---|---|---|---|---|
| `/api/v1/auth/register` | POST | `auth.py` | None (Public) | None | ✅ PASS |
| `/api/v1/auth/login` | POST | `auth.py` | None (Public) | None | ✅ PASS |
| `/api/v1/auth/otp/send` | POST | `auth.py` | None (Public) | None | ✅ PASS |
| `/api/v1/auth/otp/verify` | POST | `auth.py` | None (Public) | None | ✅ PASS |
| `/api/v1/auth/refresh` | POST | `auth.py` | None (Public) | Tokens validated programmatically | ✅ PASS |
| `/api/v1/auth/logout` | POST | `auth.py` | None (Public) | Tokens validated programmatically | ✅ PASS |
| `/api/v1/auth/me` | GET | `auth.py` | `get_current_user` | Recruiter-role restricted | ✅ PASS |
| `/api/v1/auth/sessions` | GET | `auth.py` | `get_current_user` | Queries owned records only | ✅ PASS |
| `/api/v1/auth/sessions/revoke` | POST | `auth.py` | `get_current_user` | Asserts owned session ID | ✅ PASS |
| `/api/v1/auth/register/candidate` | POST | `candidate_auth.py` | None (Public) | None | ✅ PASS |
| `/api/v1/auth/login/candidate` | POST | `candidate_auth.py` | None (Public) | None | ✅ PASS |
| `/api/v1/auth/candidate/email/send-otp` | POST | `candidate_auth.py` | None (Public) | None | ✅ PASS |
| `/api/v1/auth/candidate/email/verify-otp` | POST | `candidate_auth.py` | None (Public) | None | ✅ PASS |
| `/api/v1/auth/candidate/me` | GET | `candidate_auth.py` | `get_current_candidate` | Candidate-role restricted | ✅ PASS |
| `/api/v1/auth/candidate/phone/send-otp` | POST | `candidate_auth.py` | `get_current_candidate` | Candidate-role restricted | ✅ PASS |
| `/api/v1/auth/candidate/phone/verify-otp` | POST | `candidate_auth.py` | `get_current_candidate` | Candidate-role restricted | ✅ PASS |
| `/api/v1/auth/candidate/profile` | PUT | `candidate_auth.py` | `get_current_candidate` | Candidate-role restricted | ⚠️ PARTIAL |
| `/api/v1/jobs/feed` | GET | `candidate_jobs.py` | `get_current_candidate` | Candidate-role restricted | ✅ PASS |
| `/api/v1/candidate/resumes/upload` | POST | `candidate_resumes.py` | `get_verified_candidate` | VerifiedCandidate (MFA required) | ✅ PASS |
| `/api/v1/candidate/resumes` | GET | `candidate_resumes.py` | `get_current_candidate` | Candidate-role restricted | ✅ PASS |
| `/api/v1/candidate/resumes/{resume_id}/toggle-active` | POST | `candidate_resumes.py`Programmatic | `get_current_candidate` | **No MFA Check** (Should be VerifiedCandidate) | ❌ FAIL |
| `/api/v1/candidate/resumes/{resume_id}` | DELETE | `candidate_resumes.py` | `get_current_candidate` | **No MFA Check** (Should be VerifiedCandidate) | ❌ FAIL |
| `/api/v1/applications/apply` | POST | `candidate_applications.py` | `get_verified_candidate` | VerifiedCandidate (MFA required) | ✅ PASS |
| `/api/v1/applications/me` | GET | `candidate_applications.py` | `get_current_candidate` | Candidate-role restricted | ✅ PASS |
| `/api/v1/applications/{application_id}/withdraw` | POST | `candidate_applications.py` | `get_current_candidate` | **No MFA Check** (Should be VerifiedCandidate) | ❌ FAIL |
| `/api/v1/candidate/interviews` | GET | `candidate_interviews.py` | `get_current_candidate` | Candidate-role restricted | ✅ PASS |
| `/api/v1/candidate/bookings/{slot_id}/cancel` | POST | `candidate_interviews.py` | `get_current_candidate` | **No MFA Check** (Should be VerifiedCandidate) | ❌ FAIL |
| `/api/v1/candidate/bookings/{slot_id}/reschedule` | POST | `candidate_interviews.py` | `get_verified_candidate` | VerifiedCandidate (MFA required) | ✅ PASS |
| `/api/v1/companies/me` | GET | `companies.py` | `get_tenant_db` (chained auth) | Recruiter-role restricted + RLS | ✅ PASS |
| `/api/v1/companies/me` | PATCH | `companies.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/jobs` | GET | `jobs.py` | `get_tenant_db` (chained auth) | Recruiter-role restricted + RLS | ✅ PASS |
| `/api/v1/jobs` | POST | `jobs.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/jobs/{job_id}` | GET | `jobs.py` | `get_tenant_db` (chained auth) | Recruiter-role restricted + RLS | ✅ PASS |
| `/api/v1/jobs/{job_id}` | PATCH | `jobs.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/jobs/{job_id}` | DELETE | `jobs.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/jobs/{job_id}/candidate-matches` | POST | `jobs.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications` | GET | `applications.py` | `get_tenant_db` (chained auth) | Recruiter-role restricted + RLS | ✅ PASS |
| `/api/v1/applications` | POST | `applications.py` | `get_tenant_db` (chained auth) | `get_current_user` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}` | GET | `applications.py` | `get_tenant_db` (chained auth) | Recruiter-role restricted + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}` | PATCH | `applications.py` | `get_tenant_db` (chained auth) | `get_current_user` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}` | DELETE | `applications.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/async` | POST | `applications.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/async/status/{task_id}` | GET | `applications.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/qa` | POST | `applications.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/audit/logs` | GET | `audit.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/audit/logs/export` | GET | `audit.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/audit/archive/run` | POST | `audit.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/audit/archive/retrieve` | GET | `audit.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/notes` | POST | `notes.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/notes` | GET | `notes.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/notes/{note_id}` | PATCH | `notes.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/notes/{note_id}` | DELETE | `notes.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/interviews` | POST | `interviews.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/interviews` | GET | `interviews.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/interviews/{interview_id}` | PATCH | `interviews.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/interviews/{interview_id}/scorecard` | POST | `interviews.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/interviews/{interview_id}/scorecard` | GET | `interviews.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/offers` | POST | `offers.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/offers` | GET | `offers.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/offers/{offer_id}` | GET | `offers.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/offers/approve` | POST | `offers.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/offers/send` | POST | `offers.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/offers/decide` | POST | `offers.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/offers/expire` | POST | `offers.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/analytics/funnel` | GET | `analytics.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/analytics/velocity` | GET | `analytics.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/analytics/recruiter-productivity` | GET | `analytics.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/analytics/effectiveness` | GET | `analytics.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/analytics/adoption` | GET | `analytics.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/analytics/fairness` | GET | `analytics.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/analytics/export` | POST | `analytics.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/analytics/export/status/{job_id}` | GET | `analytics.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/analytics/export/download/{job_id}` | GET | `analytics.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/analytics/export` | GET | `analytics.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/intelligence/applications/{id}/candidate-summary` | GET | `intelligence.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/intelligence/applications/{id}/scorecard-consensus` | GET | `intelligence.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/intelligence/applications/{id}/hiring-recommendation` | GET | `intelligence.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/intelligence/applications/{id}/regenerate` | POST | `intelligence.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/intelligence/applications/{id}/decide-outcome` | POST | `intelligence.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/auth/sso/login` | POST | `sso.py` | None (Public) | SAML/OIDC configuration lookup | ✅ PASS |
| `/api/v1/auth/sso/acs` | POST | `sso.py` | None (Public) | SAML Signature, Replay & Expiry Checks | ✅ PASS |
| `/api/v1/auth/oidc/callback` | POST | `sso.py` | None (Public) | Client Secret Vault Decryption & Code Checks | ✅ PASS |
| `/api/v1/auth/calendars/connect` | POST | `calendars.py` | `get_tenant_db` (chained auth) | `get_current_user` + RLS | ✅ PASS |
| `/api/v1/auth/calendars/callback` | POST | `calendars.py` | `get_tenant_db` (chained auth) | `get_current_user` + RLS | ✅ PASS |
| `/api/v1/auth/calendars/{credential_id}/disconnect` | POST | `calendars.py` | `get_tenant_db` (chained auth) | Asserts User ID or OWNER role | ✅ PASS |
| `/api/v1/auth/calendars/{credential_id}/sync` | POST | `calendars.py` | `get_tenant_db` (chained auth) | Asserts User ID or OWNER role | ✅ PASS |
| `/api/v1/schedule/links` | POST | `scheduling.py` | `get_tenant_db` (chained auth) | `get_current_user` + RLS | ✅ PASS |
| `/api/v1/schedule/{raw_token}/availability` | GET | `scheduling.py` | `get_tenant_db` (chained auth) | **No Recruiter Context Check** | ❌ FAIL |
| `/api/v1/schedule/{raw_token}/book` | POST | `scheduling.py` | `get_tenant_db` (chained auth) | **No Recruiter Context Check** | ❌ FAIL |
| `/api/v1/schedule/bookings/{slot_id}/cancel` | POST | `scheduling.py` | `get_tenant_db` (chained auth) | Programmatic token check, no recruiter check | ❌ FAIL |
| `/api/v1/schedule/bookings/{slot_id}/reschedule` | POST | `scheduling.py` | `get_tenant_db` (chained auth) | Programmatic token check, no recruiter check | ❌ FAIL |
| `/api/v1/pipelines/templates` | POST | `pipelines.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/pipelines/jobs/{job_id}/pipeline` | POST | `pipelines.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/pipelines/stages/{stage_id}/sla` | POST | `pipelines.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/approvals/templates` | POST | `approvals.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/approvals/chains` | POST | `approvals.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/approvals/steps/{step_id}/action` | POST | `approvals.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/approvals/templates/steps/{step_id}/escalation` | POST | `approvals.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/candidates/{candidate_id}/delete` | POST | `candidates.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/candidates/compare` | POST | `candidates.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/enterprise/ip-whitelist` | POST | `enterprise.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/enterprise/ip-whitelist` | GET | `enterprise.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/enterprise/ip-whitelist/{whitelist_id}` | DELETE | `enterprise.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/enterprise/smtp` | GET | `enterprise.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/enterprise/smtp` | POST | `enterprise.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/enterprise/smtp/test` | POST | `enterprise.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/enterprise/subscription` | GET | `enterprise.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/enterprise/usage` | GET | `enterprise.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/enterprise/subscription` | POST | `enterprise.py` | None (Direct `get_db`) | `require_owner_or_billing_service` helper | ✅ PASS |
| `/api/v1/enterprise/webhooks` | POST | `webhooks.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/enterprise/webhooks` | GET | `webhooks.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/enterprise/webhooks/{subscription_id}` | DELETE | `webhooks.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/enterprise/webhooks/{subscription_id}/logs` | GET | `webhooks.py` | `get_tenant_db` (chained auth) | `RequireOwner` + RLS | ✅ PASS |
| `/api/v1/applications/{application_id}/convert` | POST | `employees.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/employees` | GET | `employees.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/employees/mappings` | POST | `employees.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/employees/metrics` | GET | `employees.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/employees/dlq` | GET | `employees.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/employees/dlq/{id}/retry` | POST | `employees.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/api/v1/employees/{employee_id}/sync-history` | GET | `employees.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/onboarding/portal/authenticate` | POST | `employees.py` | None (Direct `get_db`) | High-entropy portal token validation | ✅ PASS |
| `/onboarding/portal/checklist` | GET | `employees.py` | `get_portal_session` | Ephemeral portal session scopes | ✅ PASS |
| `/onboarding/portal/documents/{id}/sign` | POST | `employees.py` | `get_portal_session` | Ephemeral portal session scopes | ✅ PASS |
| `/employees/{employee_id}/onboarding-progress` | GET | `employees.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/employees/tasks/{task_id}/escalations/resolve` | POST | `employees.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |
| `/employees/{employee_id}/activity` | GET | `employees.py` | `get_tenant_db` (chained auth) | `RequireRecruiter` + RLS | ✅ PASS |

---

## 5. Security Gaps and Vulnerabilities

Four significant authentication and authorization vulnerabilities were discovered in the codebase audit.

### 5.1 Legacy Unprotected Endpoints in `server.py`
Four endpoints defined directly on the `app` instance in `backend/server.py` are completely unauthenticated and bypass the `/api/v1` router namespace.
* **Vulnerable Routes:**
  * POST `/api/onboard` ([server.py:163-186](file:///Users/krishnagarg/smartonboard-main/backend/server.py#L163-L186))
  * POST `/api/screen` ([server.py:188-200](file:///Users/krishnagarg/smartonboard-main/backend/server.py#L188-L180))
  * POST `/api/screen/upload` ([server.py:224-318](file:///Users/krishnagarg/smartonboard-main/backend/server.py#L224-L318))
  * POST `/api/recruit` ([server.py:320-496](file:///Users/krishnagarg/smartonboard-main/backend/server.py#L320-L496))
* **Impact:** Any client can submit payloads to parse resumes, screen candidate text, create sandbox companies, trigger Celery workers, and upload/promote files on the server without providing a JWT or credential.
* **Evidence:**
```python
@app.post("/api/onboard")
@limiter.limit("5/minute")
async def onboard(request: Request, body: OnboardRequest):
    # No authentication checks exist in this handler
    result = onboard_employee(...)
```

### 5.2 Recruiter-Scope Leaks on Public Scheduling Endpoints
The candidate-facing scheduling endpoints in [api/scheduling.py](file:///Users/krishnagarg/smartonboard-main/backend/api/scheduling.py) incorrectly inject the `get_tenant_db` dependency.
* **Vulnerable Routes:**
  * GET `/api/v1/schedule/{raw_token}/availability` ([scheduling.py:128-263](file:///Users/krishnagarg/smartonboard-main/backend/api/scheduling.py#L128-L263))
  * POST `/api/v1/schedule/{raw_token}/book` ([scheduling.py:265-440](file:///Users/krishnagarg/smartonboard-main/backend/api/scheduling.py#L265-L440))
  * POST `/api/v1/schedule/bookings/{slot_id}/cancel` ([scheduling.py:442-514](file:///Users/krishnagarg/smartonboard-main/backend/api/scheduling.py#L442-L514))
  * POST `/api/v1/schedule/bookings/{slot_id}/reschedule` ([scheduling.py:516-673](file:///Users/krishnagarg/smartonboard-main/backend/api/scheduling.py#L516-L673))
* **Impact:** 
  1. **Denial of Service:** Candidates attempting to access their scheduling links will be blocked with a `401 Unauthorized` error because they do not have a recruiter session JWT (which `get_tenant_db` requires).
  2. **Cross-Tenant Access Bypass:** Because these endpoints bypass RLS globally (`with tenant_context(auth_mode="true"):`) to retrieve the link or slot metadata, and subsequently switch tenant context manually via `with tenant_context(tenant_id=str(link.company_id)):`, *any* recruiter Bearer token from *any* company satisfies the HTTP bearer requirement. Once satisfied, the recruiter from Company B can view, book, cancel, or reschedule slots belonging to Company A.
* **Evidence:**
```python
@router.get("/{raw_token}/availability")
def get_slots_availability(
    raw_token: str,
    request: Request,
    db: Session = Depends(get_tenant_db) # <-- Requires recruiter authentication!
):
    ...
    with tenant_context(auth_mode="true"):
        link = db.scalar(select(SchedulingLink).where(SchedulingLink.token_hash == token_hash))
    ...
    with tenant_context(tenant_id=str(link.company_id)): # <-- Dynamic switch bypasses caller's company restriction!
```

### 5.3 Candidate Verification Guard Gaps (MFA Bypass)
State-changing candidate endpoints fail to apply the `VerifiedCandidate` dependency, allowing unverified candidate accounts (pre-MFA validation) to execute critical operations.
* **Vulnerable Routes:**
  * POST `/api/v1/candidate/resumes/{resume_id}/toggle-active` (uses `CurrentCandidate`)
  * DELETE `/api/v1/candidate/resumes/{resume_id}` (uses `CurrentCandidate`)
  * POST `/api/v1/applications/{application_id}/withdraw` (uses `CurrentCandidate`)
  * POST `/api/v1/candidate/bookings/{slot_id}/cancel` (uses `CurrentCandidate`)
* **Impact:** A newly registered candidate who has not completed email or phone verification can permanently delete resumes from the server, toggle active profile settings, withdraw active job applications, and trigger external calendar event cancellations (affecting recruiter calendars).
* **Evidence:**
```python
@router.post("/candidate/resumes/{resume_id}/toggle-active")
def candidate_toggle_resume_active(
    resume_id: uuid.UUID,
    current_candidate: CurrentCandidate, # <-- Authenticated, but NOT verified candidate!
    db: Annotated[Session, Depends(get_db)],
):
```

---

## 6. Remediations & Recommendations

### P0 — Critical Fixes
1. **Fix Scheduling Endpoints:** Update the database dependency in all public candidate scheduling routes in `scheduling.py` from `get_tenant_db` to `get_db` (unauthenticated session). Rely strictly on token hashes and temporary booking tokens for authorization instead of the recruiter JWT.
2. **Decommission or Protect Legacy Endpoints:** Wrap the legacy endpoints in `server.py` (`/api/onboard`, `/api/screen`, `/api/screen/upload`, `/api/recruit`) with the `get_current_user` or `RequireRecruiter` dependencies, or remove them entirely if they are no longer used by the frontend dashboard.
3. **Enforce Verification Guards:** Upgrade candidate-facing state-changing endpoints in `candidate_resumes.py`, `candidate_applications.py`, and `candidate_interviews.py` from `CurrentCandidate` to `VerifiedCandidate`.

*End of Audit Report*
