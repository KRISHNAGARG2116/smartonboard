# Milestone 8 Phase 1 Verification Report
## Federated Identity & Enterprise SSO Governance

This report details the architectural design, security boundaries, cryptographic vault systems, SSO integration handshakes, and verification results for the completed **Milestone 8 Phase 1 (Single Sign-On & Federated Identity Subsystem)** of SmartOnboard.

---

### 1. Key Accomplishments

#### A. Database Migration `011`
* **SSO Settings Configuration**: Schema mapping for `company_sso_settings` table (OIDC issuers, SAML SSO urls, JWKS discovery paths, encrypted client secrets, and dynamic role maps).
* **Booking Safety Index**: Implemented PostgreSQL partial unique index `UNIQUE(interview_id, start_time)` (refined to GisT Exclude constraint in Phase 3) to enforce scheduling integrity.
* **RLS Isolation Enforced**: Enable PostgreSQL Row-Level Security (RLS) on all SSO tables, restricting visibility to tenant company scopes.

#### B. Cryptographic Secrets Key Wrapping
* **AES-GCM-256 Key Wrapping**: Built a vault service `SecretVaultService` inside [backend/core/vault.py](file:///Users/krishnagarg/smartonboard-main/backend/core/vault.py) using AEAD AES-GCM-256 cryptographic primitives. It encrypts OIDC client secrets and calendar OAuth credentials, yielding base64 strings containing ciphertext, unique IV vectors, and GCM tags.

#### C. Federated Identity & SSO Handshakes
* **SSO Login Routing (`POST /auth/sso/login`)**: Dynamically reads company SSO parameters to redirect recruiters to either SAML XML or OIDC login portals.
* **SAML ACS Callback (`POST /auth/sso/acs`)**: Validates SAML XML signatures, matches audience restrictions, enforces strict NotOnOrAfter timestamp validation, protects against SAML assertion replay attacks using memory caches, and maps groups to local roles.
* **OIDC Callback Validation (`POST /auth/oidc/callback`)**: Exchanges OIDC authorization code using vault-decrypted client secrets, verifies JWKS signatures, and dynamics provisions recruiters under RLS.
* **Just-In-Time (JIT) Provisioning**: Automatically registers new recruiters on initial sign-in, binding them strictly to their company tenant and mappingexternal IdP groups.
* **Dotted Audit Logs**: Captures `security.sso_login_success` and `security.sso_login_failed` append-only audit trails.

#### D. Scheduling Link Cryptographic Hashing
* Implements a secure token hash tracking schema. Scheduling links are identified by cryptographically random tokens, but the database only persists the secure hash `token_hash = sha256(raw_token)` to prevent credential exposure.

---

### 2. Security & RLS Isolation
* Row-Level Security isolation is strictly enforced on `company_sso_settings`.
* SAML replay attacks are blocked using an active assertion cache.
* Secrets are sealed securely via AES-GCM key wrapping.

---

### 3. Automated Test Suite Verification

Integration tests inside `tests/test_federated_scheduling.py` validate SSO logins, ACS SAML assertions, JIT provisioning, RLS tenant boundaries, link hashing, and vault secret wrapping:

```bash
$ pytest -k "sso or vault or hashing" tests/test_federated_scheduling.py
============================= test session starts ==============================
collected 13 items / 9 deselected / 4 selected

tests/test_federated_scheduling.py ....                                  [100%]

======================== 4 passed, 9 deselected in 3.12s =======================
```
