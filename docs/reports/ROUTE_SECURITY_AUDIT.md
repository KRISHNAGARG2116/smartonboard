# ROUTE_SECURITY_AUDIT.md
# Route Protection Audit

**Audited By:** SmartOnboard Security Subagent  
**Audit Date:** 2026-06-07  
**Scope:** Frontend route guards, backend endpoint authentication, cross-role isolation  
**Overall Status:** ⚠️ PARTIAL

---

## 1. Executive Summary

The application has a solid foundation for route security:
- **Frontend `ProtectedRoute` component** enforces authentication and role-based access
- **Backend dependencies** (`get_current_user`, `get_current_candidate`, `RoleChecker`) properly separate recruiter and candidate access
- **Row-Level Security (RLS)** is enforced via `set_tenant_context` on all recruiter queries

However, there are gaps:
- Onboarding wizard can be bypassed via direct URL navigation
- Some candidate state-changing endpoints lack `VerifiedCandidate` guard
- localStorage-based onboarding has no server-side enforcement

---

## 2. Frontend Route Protection

### 2.1 ProtectedRoute Component (PASS ✅)

**Location:** [`ProtectedRoute.tsx`](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/ProtectedRoute.tsx)

| Check | Implemented? |
|---|---|
| Authentication required | ✅ Redirects to login if `!user` |
| Role-based access control | ✅ Checks `allowedRoles` array |
| Loading state handling | ✅ Shows spinner during auth load |
| Role-appropriate redirects | ✅ Candidates → `/candidate/dashboard`, Recruiters → `/recruiter/dashboard` |
| Onboarding enforcement | ❌ Not checked |

### 2.2 Route Configuration ([`App.tsx`](file:///Users/krishnagarg/smartonboard-main/frontend/src/App.tsx))

#### Guest Routes (No Auth Required) — PASS ✅
| Route | Page | Status |
|---|---|---|
| `/` | Landing | ✅ Public |
| `/login` | Login | ✅ Public |
| `/register` | Register | ✅ Public |
| `/recruiter/login` | RecruiterLogin | ✅ Public |
| `/recruiter/register` | RecruiterRegister | ✅ Public |
| `/candidate/login` | CandidateLogin | ✅ Public |
| `/candidate/register` | CandidateRegister | ✅ Public |

#### Recruiter Routes — PASS ✅
| Route | Page | Roles | Status |
|---|---|---|---|
| `/recruiter/dashboard` | RecruiterDashboard | `owner`, `recruiter` | ✅ Protected |
| `/recruiter/jobs` | RecruiterJobs | `owner`, `recruiter` | ✅ Protected |
| `/recruiter/candidates` | CandidateDirectory | `owner`, `recruiter` | ✅ Protected |
| `/recruiter/pipeline` | PipelineBoard | `owner`, `recruiter` | ✅ Protected |
| `/recruiter/interviews` | RecruiterInterviews | `owner`, `recruiter` | ✅ Protected |
| `/recruiter/analytics` | AnalyticsDashboard | `owner`, `recruiter` | ✅ Protected |
| `/recruiter/settings` | RecruiterSettings | `owner`, `recruiter` | ✅ Protected |

#### Candidate Routes — PASS ✅
| Route | Page | Roles | Status |
|---|---|---|---|
| `/candidate/dashboard` | CandidateDashboard | `candidate` | ✅ Protected |
| `/candidate/resumes` | ResumeLibrary | `candidate` | ✅ Protected |
| `/candidate/jobs` | CandidateJobFeed | `candidate` | ✅ Protected |
| `/candidate/applications` | CandidateApplications | `candidate` | ✅ Protected |
| `/candidate/interviews` | CandidateInterviews | `candidate` | ✅ Protected |
| `/candidate/profile` | CandidateProfilePage | `candidate` | ✅ Protected |
| `/candidate/settings` | CandidateSettings | `candidate` | ✅ Protected |

#### Wildcard Fallback — PASS ✅
| Route | Behavior |
|---|---|
| `*` | Redirects to `/` |

---

## 3. Backend Endpoint Security

### 3.1 Authentication Dependencies

| Dependency | File | Purpose | Status |
|---|---|---|---|
| `get_current_user` | [`deps.py:19-80`](file:///Users/krishnagarg/smartonboard-main/backend/api/deps.py#L19-L80) | JWT validation + company/user verification | ✅ PASS |
| `get_current_candidate` | [`deps.py:83-145`](file:///Users/krishnagarg/smartonboard-main/backend/api/deps.py#L83-L145) | JWT validation + candidate role check | ✅ PASS |
| `get_verified_candidate` | [`deps.py:245-259`](file:///Users/krishnagarg/smartonboard-main/backend/api/deps.py#L245-L259) | Email + phone verified check | ✅ PASS |
| `RoleChecker` | [`deps.py:161-171`](file:///Users/krishnagarg/smartonboard-main/backend/api/deps.py#L161-L171) | Role-based authorization | ✅ PASS |
| `get_portal_session` | [`deps.py:174-219`](file:///Users/krishnagarg/smartonboard-main/backend/api/deps.py#L174-L219) | Employee portal token validation | ✅ PASS |

### 3.2 Cross-Role Isolation (PASS ✅)

The `get_current_user` function (line 29-33) explicitly rejects candidates:
```python
if role == UserRole.CANDIDATE.value:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Candidates are not permitted to access recruiter resources",
    )
```

The `get_current_candidate` function (line 105-109) explicitly rejects non-candidates:
```python
if role != UserRole.CANDIDATE.value:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This endpoint requires candidate authentication",
    )
```

**Result:** A candidate JWT cannot access recruiter endpoints, and a recruiter JWT cannot access candidate endpoints.

### 3.3 Session Security (PASS ✅)

Both `get_current_user` and `get_current_candidate` implement:
- Token revocation check via `RevokedToken` table
- Session validity check (is_revoked, expiration)
- Session activity tracking (`last_active` update)
- JTI (JWT ID) blacklist checking

### 3.4 Tenant Isolation (PASS ✅)

- Recruiter queries use `TenantDb` which sets tenant context via `set_tenant_context(db, company_id)`
- Candidate queries bypass RLS via `tenant_context(auth_mode="true")` — appropriate since candidates have no company_id
- All recruiter-facing queries filter by `company_id == current_user.company_id`

---

## 4. Backend Endpoint Guard Summary

### 4.1 Recruiter Endpoints (All PASS ✅)

| Router | Prefix | Guard | File |
|---|---|---|---|
| Jobs | `/jobs` | `RequireRecruiter` / `TenantDb` | [`jobs.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/jobs.py) |
| Applications | `/applications` | `RequireRecruiter` / `CurrentUser` / `TenantDb` | [`applications.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/applications.py) |
| Interviews | `/applications/{id}/interviews` | `RequireRecruiter` / `TenantDb` | [`interviews.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/interviews.py) |
| Pipelines | `/pipelines` | `RequireRecruiter` / `TenantDb` | [`pipelines.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/pipelines.py) |
| Candidates | `/candidates` | Recruiter guards | [`candidates.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/candidates.py) |
| Analytics | `/analytics` | Recruiter guards | [`analytics.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/analytics.py) |
| Intelligence | `/intelligence` | Recruiter guards | [`intelligence.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/intelligence.py) |
| Scheduling | `/scheduling` | Recruiter guards | [`scheduling.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/scheduling.py) |
| Committees | `/committees` | Recruiter guards | [`committees.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/committees.py) |
| Approvals | `/approvals` | Recruiter guards | [`approvals.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/approvals.py) |
| Notes | `/notes` | Recruiter guards | [`notes.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/notes.py) |
| Offers | `/offers` | Recruiter guards | [`offers.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/offers.py) |

### 4.2 Candidate Endpoints (PARTIAL ⚠️)

| Endpoint | Guard | Should Be | Status |
|---|---|---|---|
| Resume Upload | `VerifiedCandidate` | `VerifiedCandidate` | ✅ PASS |
| Resume List | `CurrentCandidate` | `CurrentCandidate` | ✅ PASS |
| Resume Toggle | `CurrentCandidate` | `VerifiedCandidate` | ❌ FAIL |
| Resume Delete | `CurrentCandidate` | `VerifiedCandidate` | ❌ FAIL |
| Apply to Job | `VerifiedCandidate` | `VerifiedCandidate` | ✅ PASS |
| List Applications | `CurrentCandidate` | `CurrentCandidate` | ✅ PASS |
| Withdraw Application | `CurrentCandidate` | `VerifiedCandidate` | ❌ FAIL |
| List Interviews | `CurrentCandidate` | `CurrentCandidate` | ✅ PASS |
| Cancel Booking | `CurrentCandidate` | `VerifiedCandidate` | ❌ FAIL |
| Reschedule Booking | `VerifiedCandidate` | `VerifiedCandidate` | ✅ PASS |
| Job Feed | `CurrentCandidate` | `CurrentCandidate` | ✅ PASS |
| Profile /me | `CurrentCandidate` | `CurrentCandidate` | ✅ PASS |
| Profile Update | `CurrentCandidate` | `CurrentCandidate` | ⚠️ PARTIAL |

---

## 5. Rate Limiting (PASS ✅)

Rate limiting is applied to sensitive endpoints via the `@limiter.limit()` decorator:

| Endpoint | Rate Limit |
|---|---|
| Candidate Register | 5/minute |
| Candidate Login | 10/minute |
| Email Send OTP | 3/minute |
| Email Verify OTP | 5/minute |
| Phone Send OTP | 3/minute |
| Phone Verify OTP | 5/minute |
| Profile Update | 10/minute |
| Candidate /me | 100/minute |

IP-based brute force lockout is also implemented for candidate login via `is_ip_blocked` / `record_failed_login`.

---

## 6. Audit Logging (PASS ✅)

All sensitive operations across both candidate and recruiter endpoints log structured audit events via `log_audit_event()` including:
- Actor type and ID
- IP address and User-Agent
- Resource type and ID
- Action metadata

---

## 7. Consolidated Risk Assessment

| Risk Area | Severity | Status |
|---|---|---|
| Authentication (JWT validation) | — | ✅ PASS |
| Cross-role isolation | — | ✅ PASS |
| Session management | — | ✅ PASS |
| Token revocation | — | ✅ PASS |
| Tenant isolation (RLS) | — | ✅ PASS |
| Rate limiting | — | ✅ PASS |
| Audit logging | — | ✅ PASS |
| Candidate verification guards | HIGH | ⚠️ PARTIAL — 4 endpoints missing `VerifiedCandidate` |
| Onboarding enforcement | HIGH | ❌ FAIL — frontend-only, dashboard-only, bypassable |
| localStorage key naming | LOW | ❌ FAIL — uses legacy `smartonboard_` prefix |
| Wildcard route handling | — | ✅ PASS |

---

## 8. Recommendations (Priority Order)

### P0 — Critical

1. **Upgrade 4 candidate endpoints to `VerifiedCandidate`:**
   - `candidate_resumes.py`: `toggle-active`, `delete`
   - `candidate_applications.py`: `withdraw`
   - `candidate_interviews.py`: `cancel`

2. **Add onboarding check to `ProtectedRoute.tsx`:**
   - Check localStorage onboarding state before rendering child routes
   - Redirect un-onboarded users to their dashboard (which triggers wizard)

### P1 — High Priority

3. **Add server-side `onboarding_completed` tracking:**
   - Backend model field + dependency for enforcement
   - Prevents localStorage manipulation bypass

4. **Make onboarding wizard functional:**
   - Wire wizard steps to actual API calls
   - Wizard should trigger real verification flows

### P2 — Medium Priority

5. **Rename localStorage keys:**
   - `smartonboard_onboarded_candidate_{email}` → `smartonboard_onboarded_candidate_{email}`
   - `smartonboard_onboarded_recruiter_{email}` → `smartonboard_onboarded_recruiter_{email}`
   - Include migration logic for existing users

6. **Add backend onboarding enforcement middleware:**
   - Create `RequireOnboarded` dependency
   - Apply to all workspace endpoints (not just verification-sensitive ones)

---

*End of Report*
