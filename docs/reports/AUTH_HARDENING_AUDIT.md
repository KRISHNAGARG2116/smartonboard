# SmartOnboard Authentication & Verification Hardening Audit (Phase 14A)

## 1. Executive Summary

This audit evaluates the registration, email/phone verification, login, protected routes, and onboarding flow of candidates and recruiters on SmartOnboard. It identifies critical vulnerabilities that allow recruiter and candidate accounts to be registered with invalid or disposable email addresses, login without verification, and bypass essential onboarding and verification steps via client-side controls.

---

## 2. Component Audits & Investigations

### 2.1 Recruiter Registration Flow
* **Current Implementation:** Receives company name, email, password, and full name. It restricts signup to non-public domains using `is_public_mail_host()` and performs a basic DNS/MX query via `validate_domain_dns()`.
* **Vulnerabilities Identified:**
  1. No server-side validation of email format using strict regex (beyond Pydantic's basic email check).
  2. No check for disposable email hosts (e.g. `mailinator.com`), allowing recruiters to bypass corporate email checks using temporary addresses.
  3. No email verification challenge is issued at registration; recruiters are logged in immediately and issued valid access/refresh tokens.
  4. There is no `email_verified` state stored on the `User` model for recruiters.

### 2.2 Candidate Registration Flow
* **Current Implementation:** Receives email, password, and full name. Creates a `User` row (role = candidate) and a `CandidateProfile` row (with `email_verified = False` and `phone_verified = False`).
* **Vulnerabilities Identified:**
  1. No validation against disposable email providers.
  2. Candidate is immediately logged in upon signup and issued a fully valid access token, bypassing verification.
  3. Strict server-side verification checks are missing on several state-changing candidate endpoints.

### 2.3 Email Verification Flow
* **Current Implementation:**
  * Candidates can request an OTP via `/api/v1/auth/candidate/email/send-otp` and verify it via `/api/v1/auth/candidate/email/verify-otp`.
  * Recruiters have no email verification flow whatsoever.
* **Vulnerabilities Identified:**
  * Since recruiter emails are never verified, accounts can easily be registered using non-existent/fake emails, allowing fake companies to be created in the system.

### 2.4 Phone Verification Flow
* **Current Implementation:**
  * Candidates verify phone number via `/api/v1/auth/candidate/phone/send-otp` and `/api/v1/auth/candidate/phone/verify-otp`.
  * Enforces a Redis-backed rate limit (1 OTP request per phone number per minute).
* **Vulnerabilities Identified:**
  * State-changing candidate operations (e.g., deleting resumes, rescheduling, withdrawing applications) do not enforce that both email and phone are verified.

### 2.5 Login Flow
* **Current Implementation:**
  * Recruiter Login: POST `/api/v1/auth/login` checks company status is active, checks password hash, and issues tokens.
  * Candidate Login: POST `/api/v1/auth/login/candidate` checks candidate user, password hash, and issues tokens.
* **Vulnerabilities Identified:**
  * No check exists at login to block unverified recruiter or candidate users. Unverified users can log in repeatedly.

### 2.6 ProtectedRoute Enforcement
* **Current Implementation:** Client-side React route protection in `ProtectedRoute.tsx`. It handles redirection based on role and checks local storage to see if the user is onboarded.
* **Vulnerabilities Identified:**
  1. No check for verification status (email/phone verified) on the frontend router.
  2. Onboarding check relies entirely on `localStorage.getItem("smartonboard_onboarded_...")`. A user can easily bypass company onboarding by setting these keys manually in the browser console.
  3. Client-side route blocking is easily bypassed by manipulating routing states or directly invoking API endpoints that lack server-side validation.

### 2.7 Onboarding Enforcement
* **Current Implementation:**
  * Recruiter onboarding wizard (`RecruiterOnboardingWizard.tsx`) is triggered if `smartonboard_onboarded_recruiter_${user.email}` is not set in `localStorage`.
* **Vulnerabilities Identified:**
  * Bypassing is trivial since no server-side onboarding status flag is checked on critical recruiter endpoints.

---

## 3. Remediation Plan

To address these vulnerabilities and harden the authentication and verification layer, the following fixes are required:

### 3.1 Recruiter Accounts
* **Strict Email Validation:** Validate email format server-side using a strict regex pattern. Block disposable domains.
* **Verification Token:** Send a verification email containing a 6-digit OTP upon recruiter registration.
* **Block Login/Access:** Require email verification before allowing successful login or dashboard/onboarding access.
* **Company Onboarding Guard:** Block company onboarding wizard and settings updates until the recruiter's email is verified.

### 3.2 Candidate Accounts
* **Strict Verification Checks:** Update state-changing candidate endpoints on the backend to require both email and phone verification:
  - Block resume activation and deletion until verified.
  - Block job applications until verified.
  - Block interview scheduling/cancellation until verified.
* **Disposable Domain Checks:** Block disposable email signup for candidates.

### 3.3 Protected Routes
* **URL Manipulation Mitigation:** Ensure that backend routes enforce verification and onboarding state server-side.
* **Frontend Guards:** Update `ProtectedRoute.tsx` to check user verification state from the user context rather than relying solely on local storage.
