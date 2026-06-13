# Google OAuth Security Audit

This document presents a comprehensive security audit of the Google Sign-In and OAuth integration implemented in SmartOnboard (Phase 14B).

---

## 1. Google OAuth Token Verification Flow

All client-side Google OAuth logins must send the resulting ID Token (`credential`) to the backend at `POST /api/v1/auth/google`. The backend verifies the token directly with Google APIs to prevent client-side spoofing.

### Step-by-Step Backend Verification
1. **Audience Check (`aud`)**: The token's client ID claim must match the backend's configured `GOOGLE_CLIENT_ID` environment variable.
2. **Signature Verification**: Google's public certificates (fetched and cached from `https://www.googleapis.com/oauth2/v3/certs`) are used to verify the cryptographic signature of the token.
3. **Expiration check (`exp`)**: The token must not be expired.
4. **Hosted Domain Check (`hd`)**: For recruiters, the `hd` claim (G-Suite/Workspace hosted domain) is verified if available.

### Implementation Verification
The token is decoded and verified using Google's official verification library:
```python
# backend/core/auth_providers/google.py
from google.oauth2 import id_token
from google.auth.transport import requests

def verify_google_id_token(token: str, client_id: str) -> dict:
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)
        return idinfo
    except ValueError as e:
        raise ValueError(f"Invalid Google ID Token: {str(e)}")
```

---

## 2. Role Separation & Identity Protection

A core security risk is role crossing (e.g. a candidate attempting to log in as a recruiter using their candidate email, or vice-versa).

### Prevention Mechanism
- During login/registration, the client specifies the requested `role` (`candidate` or `recruiter`).
- If a user record matching the verified Google email or `google_subject_id` already exists, the backend verifies that the existing user's role is compatible with the requested role:
  - If existing user is a candidate, and requested role is `recruiter` -> **BLOCKED (400 Bad Request)**
  - If existing user is a recruiter/owner, and requested role is `candidate` -> **BLOCKED (400 Bad Request)**

```python
# backend/api/auth.py
if user:
    # Check role mismatch
    if user.role == UserRole.CANDIDATE and role_requested == "recruiter":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role mismatch: Email already associated with another user type"
        )
    if user.role in [UserRole.OWNER, UserRole.RECRUITER] and role_requested == "candidate":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role mismatch: Email already associated with another user type"
        )
```

---

## 3. Recruiter Domain Validation & Email Policies

To maintain the integrity of recruiter workspaces, public email providers are banned for recruiter registrations.

### Domain Rules:
1. **Public Domain Check**: If a recruiter registers with a Google account using a public email provider (e.g., `gmail.com`, `yahoo.com`, `hotmail.com`), the registration is immediately blocked.
2. **Hosted Domain Alignment**: During the company setup wizard `/auth/setup-company`, if the user has a verified Google Workspace hosted domain claim (`hd` claim), the company domain must match it exactly.

```python
# Recruiter public email rejection
blocked_hosts = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "proton.me", "protonmail.com"}
email_domain = email.split("@")[1]
if email_domain in blocked_hosts or is_public_mail_host(email):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Recruiters must register with a corporate email address."
    )
```

---

## 4. Audit Log Events

Every phase of the Google OAuth flow triggers a structured security audit event for compliance:

| Event Action | Trigger | Actor Type | Metadata Recorded |
| --- | --- | --- | --- |
| `auth.google_login_success_candidate` | Candidate logs in successfully via Google | `CANDIDATE` | `email`, `auth_provider: google` |
| `auth.google_login_success_recruiter` | Recruiter logs in successfully via Google | `RECRUITER` | `email`, `auth_provider: google` |
| `auth.google_login_failed` | Token signature, expiration, or claims validation fails | `UNAUTHENTICATED` | `reason`, `email_or_token` |
| `auth.google_role_mismatch` | Role crossing detected | `UNAUTHENTICATED` | `reason`, `email` |
| `auth.google_public_email_rejected` | Recruiter attempts public email registration | `UNAUTHENTICATED` | `reason`, `email` |
| `auth.google_rate_limit_exceeded` | Lockout threshold exceeded | `UNAUTHENTICATED` | `detail` |
