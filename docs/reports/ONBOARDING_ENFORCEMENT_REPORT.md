# ONBOARDING_ENFORCEMENT_REPORT.md
# Onboarding Wizard Enforcement Status Audit

**Audited By:** SmartOnboard Security Subagent  
**Audit Date:** 2026-06-07  
**Scope:** Candidate and Recruiter onboarding wizard enforcement — frontend and backend  
**Overall Status:** ❌ FAIL

---

## 1. Executive Summary

The onboarding wizard system has **critical enforcement gaps**:

1. **Onboarding state is localStorage-only** — there is **no backend enforcement** of onboarding completion
2. **Only the Dashboard pages** check onboarding state — all other workspace pages are accessible without completing onboarding
3. **The localStorage keys still use the legacy `smartonboard_` prefix** instead of `smartonboard_`
4. **The wizard is cosmetic** — it does not actually perform the operations it describes (e.g., resume upload, email/phone OTP verification)

---

## 2. Candidate Onboarding Wizard

### Location
- Component: [`CandidateOnboardingWizard.tsx`](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/CandidateOnboardingWizard.tsx)
- Invocation: [`CandidateDashboard.tsx:69-76`](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/candidate/CandidateDashboard.tsx#L69-L76)

### State Storage
```javascript
// READ (line 20)
localStorage.getItem(`smartonboard_onboarded_candidate_${user?.email}`)
// WRITE (line 73)
localStorage.setItem(`smartonboard_onboarded_candidate_${user?.email}`, 'true')
```

### Wizard Steps (6 total)
| Step | Description | Actually Performs Action? |
|---|---|---|
| 1 | Create Profile Bio | ❌ No — input not sent to API |
| 2 | Upload Primary Resume | ❌ No — only captures filename text, no actual upload |
| 3 | Verify Email OTP | ❌ No — input not validated against backend |
| 4 | Verify Phone SMS OTP | ❌ No — input not validated against backend |
| 5 | Confirm Primary Skills | ❌ No — input not sent to API |
| 6 | Setup Complete | ❌ No API call — just sets localStorage |

### Findings

| Check | Status |
|---|---|
| Wizard blocks dashboard access until complete | ✅ PASS (dashboard only) |
| Wizard blocks other candidate pages | ❌ FAIL |
| Wizard actually performs verification | ❌ FAIL — cosmetic only |
| Backend enforces onboarding completion | ❌ FAIL — no backend check |
| localStorage key uses correct prefix | ❌ FAIL — uses `smartonboard_` prefix |

---

## 3. Recruiter Onboarding Wizard

### Location
- Component: [`RecruiterOnboardingWizard.tsx`](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/RecruiterOnboardingWizard.tsx)
- Invocation: [`RecruiterDashboard.tsx:400-406`](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/recruiter/RecruiterDashboard.tsx#L400-L406)

### State Storage
```javascript
// READ (line 41)
localStorage.getItem(`smartonboard_onboarded_recruiter_${user?.email}`)
// WRITE (line 404)
localStorage.setItem(`smartonboard_onboarded_recruiter_${user?.email}`, 'true')
```

### Wizard Steps (5 total)
| Step | Description | Actually Performs Action? |
|---|---|---|
| 1 | Create Company Space | ❌ No — input not sent to API |
| 2 | Post Your First Job | ❌ No — input not sent to API |
| 3 | Configure Hiring Pipeline | ❌ No — selection not persisted |
| 4 | Invite Team Members | ❌ No — email not sent |
| 5 | Onboarding Completed | ❌ No API call — just sets localStorage |

### Findings

| Check | Status |
|---|---|
| Wizard blocks dashboard access until complete | ✅ PASS (dashboard only) |
| Wizard blocks other recruiter pages | ❌ FAIL |
| Wizard actually performs actions | ❌ FAIL — cosmetic only |
| Backend enforces onboarding completion | ❌ FAIL — no backend check |
| localStorage key uses correct prefix | ❌ FAIL — uses `smartonboard_` prefix |

---

## 4. Backend Enforcement Analysis

### Candidate Backend
- **No backend field** exists to track onboarding completion status
- The `CandidateProfile.profile_status` field exists but is not used for onboarding enforcement
- The `VerifiedCandidate` dependency checks `email_verified` and `phone_verified`, but this is **independent** of the onboarding wizard flow
- The wizard doesn't actually trigger the real verification endpoints

### Recruiter Backend
- **No backend field** exists for recruiter onboarding completion
- No middleware or dependency checks onboarding state
- Recruiter endpoints use `RequireRecruiter` which checks role but not onboarding completion
- Job creation, pipeline management, and candidate review are all accessible without completing onboarding

---

## 5. Bypass Vulnerability Assessment

### Can onboarding be bypassed?

| Vector | Exploitable? | Severity |
|---|---|---|
| Direct URL navigation to `/candidate/resumes` | ✅ YES | HIGH |
| Direct URL navigation to `/candidate/jobs` | ✅ YES | HIGH |
| Direct URL navigation to `/candidate/applications` | ✅ YES | HIGH |
| Direct URL navigation to `/candidate/interviews` | ✅ YES | HIGH |
| Direct URL navigation to `/candidate/profile` | ✅ YES | HIGH |
| Direct URL navigation to `/recruiter/jobs` | ✅ YES | HIGH |
| Direct URL navigation to `/recruiter/candidates` | ✅ YES | HIGH |
| Direct URL navigation to `/recruiter/pipeline` | ✅ YES | HIGH |
| Direct URL navigation to `/recruiter/interviews` | ✅ YES | HIGH |
| Direct URL navigation to `/recruiter/analytics` | ✅ YES | HIGH |
| Direct URL navigation to `/recruiter/settings` | ✅ YES | HIGH |
| Browser DevTools `localStorage.setItem(...)` | ✅ YES | MEDIUM |
| API calls without frontend | ✅ YES | HIGH |

### Root Cause
The onboarding check only exists in `CandidateDashboard.tsx` and `RecruiterDashboard.tsx`. The [`ProtectedRoute.tsx`](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/ProtectedRoute.tsx) component checks authentication and role but **does not check onboarding state**.

---

## 6. Recommendations

### Critical (Must Fix)

1. **Add onboarding check to `ProtectedRoute.tsx`**
   - Check `localStorage` onboarding state for all protected routes
   - Redirect to dashboard (which shows wizard) if onboarding not complete
   - This prevents bypass via direct URL navigation

2. **Rename localStorage keys from `smartonboard_` to `smartonboard_`**
   - Current keys: `smartonboard_onboarded_candidate_{email}`, `smartonboard_onboarded_recruiter_{email}`
   - Target keys: `smartonboard_onboarded_candidate_{email}`, `smartonboard_onboarded_recruiter_{email}`
   - Add migration logic to read old keys and write new keys

3. **Make wizard functional**
   - Wire wizard steps to actual backend API calls
   - Step 2 (Resume Upload) should call `/api/v1/auth/candidate/resumes/upload`
   - Step 3 (Email OTP) should call `/api/v1/auth/candidate/email/send-otp` and `verify-otp`
   - Step 4 (Phone OTP) should call `/api/v1/auth/candidate/phone/send-otp` and `verify-otp`

### High Priority

4. **Add backend `onboarding_completed` field**
   - Add `onboarding_completed: bool` to `CandidateProfile` and recruiter `User` model
   - Create a backend dependency `RequireOnboarded` that checks this field
   - Apply to sensitive endpoints alongside `VerifiedCandidate`

5. **Server-side validation of onboarding**
   - Frontend localStorage can always be manipulated
   - Backend should be the source of truth for onboarding state

---

*End of Report*
