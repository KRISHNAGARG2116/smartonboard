# JWT Payload Audit

This document audits the structure, design constraints, and security of JWT payloads issued by SmartOnboard (Phase 14B).

---

## 1. Preserved Standard Claims Architecture

To ensure backwards compatibility and prevent payload bloat, the existing JWT access and refresh token claims remain completely unchanged. Specifically:
- **NO Google OAuth claims** (such as `google_subject_id`, `google_hosted_domain`, or Google credentials) are written to the JWT token.
- **NO `auth_provider` claim** is written to the JWT token.
- Once a user is authenticated (whether via Google or standard credentials), the issued JWT contains only the standard, necessary session claims.

---

## 2. JWT Access Token Payload Structure

A decoded Access Token contains the following claims:

```json
{
  "sub": "ad9f11da-a03e-42b3-994f-535bb902bde3",
  "company_id": null,
  "role": "owner",
  "email": "recruiter_visual_1781297667176@oryzo.ai",
  "session_id": "9d048bed-a7ed-4ccc-8e2f-24952a30c358",
  "exp": 1781299467
}
```

### Claim Descriptions:
- `sub`: The internal UUID of the user in the database (used for tenant and RLS context).
- `company_id`: The database UUID of the company (or `null` if a Google recruiter who hasn't completed Setup Company yet, or a candidate).
- `role`: The role of the user (`owner`, `recruiter`, or `candidate`).
- `email`: Lowercase, verified email of the user.
- `session_id`: Unique identifier tracking the user session in `user_sessions`.
- `exp`: Unix timestamp indicating token expiration.

---

## 3. JWT Refresh Token Payload Structure

A decoded Refresh Token contains:

```json
{
  "sub": "ad9f11da-a03e-42b3-994f-535bb902bde3",
  "company_id": null,
  "role": "owner",
  "email": "recruiter_visual_1781297667176@oryzo.ai",
  "session_id": "9d048bed-a7ed-4ccc-8e2f-24952a30c358",
  "exp": 1783889067
}
```

### Session Lifecycle Management:
- During token refresh, the database is queried to ensure that the session (`session_id`) has not been revoked and that the refresh token hash matches the stored hash in `user_sessions`.
- This ensures that logging out or revoking a session instantly invalidates both refresh tokens and any requests made with them.
- Auth provider details are stored exclusively in the persistent database layer (`users.auth_provider`), separating transient session tokens from permanent profile records.
