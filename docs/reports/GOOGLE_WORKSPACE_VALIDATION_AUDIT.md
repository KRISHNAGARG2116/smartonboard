# Google Workspace Validation Audit

This document audits the domain and hosted domain (`hd` claim) verification rules for Google Workspace-authenticated recruiters in SmartOnboard (Phase 14B.1).

---

## 1. Domain Match Constraints

When a recruiter registers or signs in using Google, their domain information is extracted from two claims:
- **Email Address**: `user@domain.com` -> extracted email domain: `domain.com`.
- **Google Workspace Hosted Domain (`hd` claim)**: If the Google Account belongs to a Google Workspace organization, Google includes the verified hosted domain in the `hd` claim (e.g. `domain.com`).

---

## 2. Hardened Verification in Setup Company

To prevent domain spoofing and workspace pollution:
1. **Email Domain Match**: During the company setup wizard `/auth/setup-company`, the recruiter's email domain must match the requested company domain exactly.
2. **Hosted Domain Claim Enforcement**: If the user's Google token contains a hosted domain (`hd`) claim (indicating a verified Google Workspace account), the company domain and the email domain must match this `hd` claim exactly.

### Backend Enforcement Code:
```python
# backend/api/auth.py
# Google Workspace Hosted Domain check
if current_user.google_hosted_domain:
    google_hd = current_user.google_hosted_domain.lower().strip()
    if google_hd != company_domain or google_hd != email_domain:
        log_audit_event(
            db=db,
            action="auth.setup_company_failed",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            metadata={
                "email": current_user.email,
                "google_hd": google_hd,
                "requested_domain": company_domain,
                "reason": "Google Workspace hosted domain mismatch"
            }
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company domain must match authenticated email domain"
        )
```

This ensures that a recruiter signing in with `user@acme.com` (verified Workspace account `acme.com`) cannot attempt to create or set up a company for `microsoft.com` or any other domain. Every failure logs a security audit event (`auth.setup_company_failed`).
