# Candidate Onboarding Verification Audit Report
**Verified Hiring Ecosystem & AI Hiring Operating System**

This report documents the security audit, architectural design, and verification outcomes for the Candidate Onboarding Verification Flow (Phase 14D) implemented in SmartOnboard.

---

## 1. Executive Summary

In accordance with the verified hiring core principles (maximizing recruiter trust and hiring quality), the candidate authentication flow has been completely restructured to prevent unverified candidate access to the platform. 

All candidate accounts are now blocked from accessing any workspace routes or performing any actions (resume uploads, applications, interview bookings) until they have successfully completed **both** email and phone verifications.

---

## 2. Target Candidate Flows & Architecture

### Option A: Google Sign In Flow
1. **Initiation:** Candidate clicks "Continue with Google".
2. **Authentication:** Google OAuth succeeds. Because Google is a trusted identity provider, the candidate's email is considered verified immediately (`email_verified = True`).
3. **Redirection:** The frontend detects that the email is verified but the phone is unverified. It redirects the candidate to `/candidate/verify` which automatically renders a **phone-only verification layout**.
4. **Phone Entry:** The candidate enters their mobile phone number.
5. **SMS OTP:** Twilio Verify API (or mock fallback) delivers a 6-digit SMS OTP.
6. **Session Activation:** Only after successful phone OTP verification does the backend issue the JWT access/refresh tokens, create a user session, and grant access to `/candidate/dashboard`.

### Option B: Email Registration Flow
1. **Registration:** Candidate registers with Name, Email, Phone Number, and Password.
2. **Token Withholding:** The backend creates the account but **withholds the JWT tokens** (returns `access_token = None`), preventing immediate session creation.
3. **Delivery:** The backend immediately sends an Email OTP (via Resend) and a Phone OTP (via Twilio Verify).
4. **Verification Page:** The candidate is redirected to a premium **dual-panel verification interface** rendering both email and phone panels side-by-side.
5. **Independent Verification:** The candidate verifies both independently. The frontend can call the verification endpoints separately.
6. **Session Activation:** Only when both `email_verified == True` and `phone_verified == True` does the backend atomically issue the JWT access/refresh tokens, log in the user, and redirect them to the dashboard.

---

## 3. Core Security & Enforcement Controls

### 3.1 Backend API-Level Protection
All candidate workspace routes (resumes, applications, interviews, settings) are strictly protected by the `VerifiedCandidate` dependency in FastAPI:
* If a candidate attempts to access a protected route with an unverified account, the backend raises a `403 Forbidden` response: `"Candidate profile must be email and phone verified before performing this action"`.
* This blocks bypass attempts even if a malicious user manually crafts a JWT.

### 3.2 Blocked Login Attempts
If an unverified candidate attempts to log in using email/password:
1. The backend rejects the login with a `403 Forbidden` status.
2. The response body carries structured verification status metadata:
   ```json
   {
     "detail": {
       "message": "Verification required",
       "verification_required": true,
       "email": "candidate@domain.com",
       "email_verified": false,
       "phone_verified": false,
       "phone_number": "+15550199202"
     }
   }
   ```
3. The frontend captures this response, saves the email in `localStorage` to preserve progress, and redirects the user to the verification page to complete onboarding.

### 3.3 Stable JWT Lifecycle & Silent Refresh
A robust silent token refresh interceptor is implemented in the frontend (`frontend/src/api.ts`):
* Automatically intercepts `401 Unauthorized` responses.
* Transparently calls `/api/v1/auth/refresh` using the secure `HTTPOnly` refresh token.
* Retries the original failed request with the new access token.
* This resolves the "Signature has expired" / `401 Unauthorized` bugs, ensuring seamless session persistence.

---

## 4. Twilio Verify API & Mock Fallback

The platform leverages **Twilio's dedicated Verify API** to offload OTP storage, lockouts, and rate limiting.

### 4.1 Production Twilio Verify Flow
* **OTP Delivery:** Calls `client.verify.v2.services(verify_sid).verifications.create()` to send an SMS.
* **OTP Verification:** Calls `client.verify.v2.services(verify_sid).verification_checks.create()`.
* **Lockouts:** Twilio automatically handles lockouts (e.g. error `60200` for max check attempts reached), which the backend catches and raises as a `403 Forbidden` lockout.

### 4.2 Development Mock Fallback
When Twilio environment variables are not configured, a feature-complete **Mock verification fallback** is active:
* **Storage:** In-memory tracking of active OTP codes, expiration, and failed attempts.
* **Code Expiry:** Mock OTPs hard-expire after **10 minutes**.
* **Rate Limiting:** Enforces a maximum of **5 OTP sends per hour per phone number**, returning `429 Too Many Requests` on violation.
* **Lockout:** Enforces a maximum of **5 failed verification attempts**, locking out the phone number for **15 minutes** and returning `403 Forbidden`.

---

## 5. State Preservation & Phone Number Change Flow

### 5.1 Verification Progress Preservation
If a candidate registers, closes their browser, or refreshes the page:
* The frontend stores the email in `localStorage` under `smartonboard_verify_email`.
* On mount, the `/candidate/verify` page calls `GET /auth/verification-status?email=...` to retrieve the exact verification status.
* The page automatically restores the correct layout (dual-panel vs. phone-only) and verification progress.

### 5.2 Phone Number Change Flow
To prevent candidates from getting stuck if they entered a typo during registration:
1. The candidate clicks **"Change Number"** directly in the verification panel.
2. An in-place input allows them to type a new phone number.
3. Submitting the new number updates their profile, invalidates the previous OTP attempt, and delivers a fresh SMS OTP.
4. This logs an `auth.phone_number_changed` audit event.

---

## 6. Automated & Manual E2E Testing Verification

### 6.1 Automated Pytest Suite
A robust automated test suite in `tests/test_candidate_verification.py` verifies all aspects of the verification flow:
1. `test_candidate_registration_withholds_jwt_and_requires_phone` (Passed)
2. `test_candidate_login_unverified_blocked_with_403` (Passed)
3. `test_verification_status_endpoint` (Passed)
4. `test_independent_verification_and_automatic_jwt_issuance` (Passed)
5. `test_google_candidate_flow_phone_verification` (Passed)
6. `test_phone_number_change_flow` (Passed)
7. `test_backend_enforced_route_protection_by_verified_candidate` (Passed)
8. `test_twilio_verify_mock_lockout_and_rate_limiting` (Passed)

Additionally, all legacy candidate tests have been successfully aligned and pass **100%**.

### 6.2 Manual E2E Verification
Manual E2E testing was performed via a Puppeteer script (`e2e_verify.js`) running on Brave Browser. The script successfully navigated both flows and generated 13 screenshots in `docs/reports/ui-after/` proving correctness:
* **Email Flow Screenshots:**
  * `1_email_register_page.png` — Empty candidate registration form showing Name, Email, Password, and Phone inputs.
  * `2_email_register_filled.png` — Registration form filled with unique email and valid phone.
  * `3_email_verify_page_loaded.png` — Direct redirect to the dual-panel verification page with both panels unverified.
  * `4_email_otp_typed.png` — Email OTP typed into the input field.
  * `5_email_verified.png` — Email panel showing green success checkmark and "Verified" badge.
  * `6_phone_otp_typed.png` — Phone OTP typed into the SMS input field.
  * `7_candidate_dashboard_email_flow.png` — Automatic redirect to candidate dashboard showing successful onboarding.
* **Google Flow Screenshots:**
  * `8_google_login_page.png` — Login page showing Google Sign In button.
  * `9_google_phone_verify_page_loaded.png` — Redirect to the phone-only verification page (email verification skipped).
  * `10_google_phone_entered.png` — Phone number entered for the first time.
  * `11_google_phone_otp_sent.png` — Verification SMS OTP successfully dispatched to the candidate's phone.
  * `12_google_phone_otp_typed.png` — SMS OTP typed into the input field.
  * `13_candidate_dashboard_google_flow.png` — Successful automatic redirect to the career dashboard.

---

## 7. Audit Events Logged
The following audit events are registered in the database:
* `auth.candidate_registered` — Emitted upon candidate registration.
* `auth.email_verification_sent` — Emitted when an email verification OTP is dispatched.
* `auth.email_verification_completed` — Emitted when email OTP is verified.
* `auth.phone_number_changed` — Emitted when a candidate updates their phone number.
* `auth.phone_verification_sent` — Emitted when a phone verification SMS is dispatched.
* `auth.phone_verification_completed` — Emitted when phone OTP is verified.
* `auth.candidate_login` — Emitted when a verified candidate successfully signs in.
* `auth.candidate_login_failed` — Emitted on invalid credentials.
