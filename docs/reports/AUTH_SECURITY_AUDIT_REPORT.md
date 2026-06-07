# AUTH_SECURITY_AUDIT_REPORT.md
# Candidate Verification Guard Status Audit

**Audited By:** SmartOnboard Security Subagent  
**Audit Date:** 2026-06-07  
**Scope:** Backend API candidate endpoints — verification guard enforcement  
**Overall Status:** ⚠️ PARTIAL

---

## 1. Executive Summary

The `VerifiedCandidate` dependency exists in [`deps.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/deps.py#L245-L261) and correctly enforces that both `email_verified` and `phone_verified` are `True` on the `CandidateProfile` before allowing access.

However, **not all sensitive candidate endpoints use `VerifiedCandidate`**. Several endpoints that perform state-changing operations (resume deletion, resume toggling, application withdrawal, interview cancellation) only require `CurrentCandidate` (authenticated but **not verified**).

---

## 2. VerifiedCandidate Dependency Analysis

### Definition (PASS ✅)

| Property | Value |
|---|---|
| Location | [`deps.py:245-261`](file:///Users/krishnagarg/smartonboard-main/backend/api/deps.py#L245-L261) |
| Checks | `email_verified == True` AND `phone_verified == True` on `CandidateProfile` |
| Error Code | `403 Forbidden` |
| Error Message | *"Email and phone number must be verified before performing this action."* |

The dependency is well-implemented, checks the `CandidateProfile` model under `auth_mode="true"` tenant context bypass, and returns a clear error message.

---

## 3. Endpoint-by-Endpoint Audit

### 3.1 candidate_resumes.py

| Endpoint | Method | Guard Used | Status |
|---|---|---|---|
| `/auth/candidate/resumes/upload` | POST | `VerifiedCandidate` ✅ | **PASS** |
| `/auth/candidate/resumes` | GET | `CurrentCandidate` ⚠️ | **PARTIAL** — listing resumes is a read operation; acceptable but inconsistent |
| `/auth/candidate/resumes/{id}/toggle-active` | POST | `CurrentCandidate` ❌ | **FAIL** — state-changing operation lacks verification |
| `/auth/candidate/resumes/{id}` | DELETE | `CurrentCandidate` ❌ | **FAIL** — destructive operation lacks verification |

**Findings:**
- Resume **upload** correctly requires `VerifiedCandidate`
- Resume **list** uses `CurrentCandidate` — acceptable for read-only data
- Resume **toggle-active** and **delete** are state-changing but use only `CurrentCandidate` — **security gap**

### 3.2 candidate_applications.py

| Endpoint | Method | Guard Used | Status |
|---|---|---|---|
| `/applications/apply` | POST | `VerifiedCandidate` ✅ | **PASS** |
| `/applications/me` | GET | `CurrentCandidate` ✅ | **PASS** — read-only |
| `/applications/{id}/withdraw` | POST | `CurrentCandidate` ❌ | **FAIL** — state-changing operation lacks verification |

**Findings:**
- Job **application** correctly requires `VerifiedCandidate`
- Application **withdrawal** uses only `CurrentCandidate` — an unverified candidate could withdraw active applications — **security gap**

### 3.3 candidate_interviews.py

| Endpoint | Method | Guard Used | Status |
|---|---|---|---|
| `/candidate/interviews` | GET | `CurrentCandidate` ✅ | **PASS** — read-only |
| `/candidate/bookings/{id}/cancel` | POST | `CurrentCandidate` ❌ | **FAIL** — cancels external calendar events without verification |
| `/candidate/bookings/{id}/reschedule` | POST | `VerifiedCandidate` ✅ | **PASS** |

**Findings:**
- Interview **listing** uses `CurrentCandidate` — acceptable for read-only
- Booking **cancellation** uses only `CurrentCandidate` — triggers external calendar API calls — **security gap**
- Booking **reschedule** correctly requires `VerifiedCandidate`

### 3.4 candidate_jobs.py

| Endpoint | Method | Guard Used | Status |
|---|---|---|---|
| `/jobs/feed` | GET | `CurrentCandidate` ✅ | **PASS** — read-only public job listings |

**Findings:**
- Read-only endpoint, appropriate guard level

### 3.5 candidate_auth.py

| Endpoint | Method | Guard Used | Status |
|---|---|---|---|
| `/auth/register/candidate` | POST | None (unauthenticated) ✅ | **PASS** — registration is pre-auth |
| `/auth/login/candidate` | POST | None (unauthenticated) ✅ | **PASS** — login is pre-auth |
| `/auth/candidate/email/send-otp` | POST | None (unauthenticated) ✅ | **PASS** — part of verification flow |
| `/auth/candidate/email/verify-otp` | POST | None (unauthenticated) ✅ | **PASS** — part of verification flow |
| `/auth/candidate/me` | GET | `CurrentCandidate` ✅ | **PASS** — read-only profile |
| `/auth/candidate/phone/send-otp` | POST | `CurrentCandidate` ✅ | **PASS** — part of verification flow |
| `/auth/candidate/phone/verify-otp` | POST | `CurrentCandidate` ✅ | **PASS** — part of verification flow |
| `/auth/candidate/profile` | PUT | `CurrentCandidate` ⚠️ | **PARTIAL** — profile update resets phone_verified on phone change, but doesn't require prior verification |

**Findings:**
- Auth endpoints are appropriately protected
- Profile update endpoint allows an unverified candidate to modify their profile, including phone number changes that reset verification — this could be acceptable as part of the verification flow but is worth noting

---

## 4. Summary Matrix

| Endpoint | File | Guard | Verdict |
|---|---|---|---|
| Resume Upload | `candidate_resumes.py` | `VerifiedCandidate` | ✅ PASS |
| Resume List | `candidate_resumes.py` | `CurrentCandidate` | ✅ PASS (read-only) |
| Resume Toggle Active | `candidate_resumes.py` | `CurrentCandidate` | ❌ FAIL |
| Resume Delete | `candidate_resumes.py` | `CurrentCandidate` | ❌ FAIL |
| Apply to Job | `candidate_applications.py` | `VerifiedCandidate` | ✅ PASS |
| List My Applications | `candidate_applications.py` | `CurrentCandidate` | ✅ PASS (read-only) |
| Withdraw Application | `candidate_applications.py` | `CurrentCandidate` | ❌ FAIL |
| List Interviews | `candidate_interviews.py` | `CurrentCandidate` | ✅ PASS (read-only) |
| Cancel Booking | `candidate_interviews.py` | `CurrentCandidate` | ❌ FAIL |
| Reschedule Booking | `candidate_interviews.py` | `VerifiedCandidate` | ✅ PASS |
| Job Feed | `candidate_jobs.py` | `CurrentCandidate` | ✅ PASS (read-only) |
| Candidate /me | `candidate_auth.py` | `CurrentCandidate` | ✅ PASS (read-only) |
| Profile Update | `candidate_auth.py` | `CurrentCandidate` | ⚠️ PARTIAL |

---

## 5. Recommendations

### Critical (Must Fix)

1. **Resume Toggle Active** (`candidate_resumes.py:146`): Change `CurrentCandidate` → `VerifiedCandidate`
   - This modifies active resume state and synchronizes profile skills/summary

2. **Resume Delete** (`candidate_resumes.py:191`): Change `CurrentCandidate` → `VerifiedCandidate`
   - This permanently deletes files from disk and database records

3. **Withdraw Application** (`candidate_applications.py:208`): Change `CurrentCandidate` → `VerifiedCandidate`
   - This changes application status and triggers recruiter notification drafts

4. **Cancel Booking** (`candidate_interviews.py:108`): Change `CurrentCandidate` → `VerifiedCandidate`
   - This triggers external calendar API cancellation calls via Twilio/Google/Microsoft

### Advisory (Consider)

5. **Profile Update** (`candidate_auth.py:515`): Consider requiring `VerifiedCandidate` or adding re-verification triggers when phone numbers change

---

## 6. Recruiter-Side Guard Analysis (PASS ✅)

All recruiter endpoints use either `RequireRecruiter`, `CurrentUser`, or `TenantDb` (which chains through `get_current_user`). The `get_current_user` dependency in `deps.py` explicitly rejects candidates via role check (line 29-33). Multi-tenant RLS is enforced via `set_tenant_context`. All recruiter endpoints are properly protected.

---

*End of Report*
