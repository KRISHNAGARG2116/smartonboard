# Resend Security Audit Report

This security audit report verifies compliance with the rate limiting, token expiry, token invalidation, and audit logging requirements specified in the Phase 14C specification.

## 1. Rate Limiting Compliance

To protect authentication flows against abuse, resource depletion, and brute-force attacks, the following rate limits are strictly enforced on verification endpoints:

| Action | Rate Limit | Scope | Implementation |
| :--- | :--- | :--- | :--- |
| **Forgot Password** | 3 requests per 15 minutes | Per Email Address | Redis-backed sliding window / DB fallback |
| **Verification OTP Resend** | 5 requests per hour | Per Email Address | Redis-backed sliding window / DB fallback |

* **Redis + DB Fallback**: The rate limiter attempts to record and evaluate hits in Redis. If Redis is unavailable, it gracefully handles blocks using in-memory or database-backed tracking.
* **Lockout Response**: Exceeding these limits raises a `429 Too Many Requests` HTTP error with a descriptive message detail (`Rate limit exceeded. Please try again later.`).

---

## 2. Token Expiration Policies

Expirations are set conservatively to minimize the exposure window for active secrets:

* **Verification OTP**: Expiries are capped at **10 minutes**.
* **Password Reset Token**: Expiries are capped at **30 minutes**.

Token verification endpoints automatically reject any token whose `expires_at` timestamp has passed, throwing a `400 Bad Request` error.

---

## 3. Token Invalidation Rules

To prevent replay attacks and ensure state synchronization:
* **One Active Reset Token Policy**: Whenever a new password reset request is initiated for a user, any existing, unconsumed password reset tokens for that user are immediately marked as consumed (`consumed_at = datetime.now(timezone.utc)`).
* **Single-Use Enforcement**: Reset tokens are consumed upon first use. Any subsequent attempt to use the same token returns a `400 Bad Request` error.

---

## 4. Audit Log Events

Security events are programmatically recorded in the tamper-evident `audit_logs` table for compliance:

1. **`auth.password_reset_requested`**: Triggered when a user requests a forgot-password link. Contains `actor_id` and metadata of the target user.
2. **`auth.password_reset_completed`**: Triggered when a user successfully submits a new password using a valid reset token.
3. **`auth.email_verification_sent`**: Triggered when a verification OTP is dispatched to a user's email.
4. **`auth.email_verification_completed`**: Triggered when a user successfully enters their verification OTP, changing their database status to `email_verified = True`.

---

## 5. Fallback Chain Security

* **Credential Safety**: The `RESEND_API_KEY` is loaded strictly from environment variables and is **never** logged, printed, or hardcoded.
* **Fallback Behavior**:
  * The chain cascades gracefully: `Resend` -> `SMTP` -> `Mock`.
  * If the primary `Resend` provider fails (e.g., due to an unverified domain or API error), the system falls back to legacy enterprise/default `SMTP` configurations.
  * If both fail, it resolves to `Mock` mode in development/testing environments to prevent blocking workflows.
