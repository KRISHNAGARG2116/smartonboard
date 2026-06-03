# SmartOnboard Risk Matrix

## Security Risks

### RSK-SEC-01

Title:

Fake Recruiter Signups

Severity:

Critical

Risk:

Bad actors create fake companies.

Mitigation:

* Domain Validation
* DNS Checks
* MX Checks
* Recruiter Verification States

---

### RSK-SEC-02

Title:

OTP Abuse

Severity:

High

Risk:

Automated verification attacks.

Mitigation:

* Rate Limiting
* Expiration Windows
* Abuse Monitoring

---

## Product Risks

### RSK-PRO-01

Title:

Internal Score Leakage

Severity:

High

Risk:

Candidates discover Risk Scores, Authenticity Scores, or Internal Rankings.

Mitigation:

* Separate API Schemas
* Role-Based Responses
* Automated Tests

---

### RSK-PRO-02

Title:

Applicability Gaming

Severity:

Medium

Risk:

Candidates tailor resumes purely to maximize scores.

Mitigation:

* Authenticity Analysis
* Evidence Validation
* Recruiter Review

---

## Technical Risks

### RSK-TEC-01

Title:

LLM Cost Explosion

Severity:

High

Mitigation:

* Vector Filtering
* Top Candidate Analysis
* Queue-Based Processing

---

### RSK-TEC-02

Title:

Thread Blocking

Severity:

High

Mitigation:

* Celery
* Async Processing
* Queue Architecture

---

## Operational Risks

### RSK-OPS-01

Title:

Legacy System Interference

Severity:

Medium

Mitigation:

* Preserve Legacy Modules
* Hide From Primary Navigation
* Isolate Routes

---

## Business Risks

### RSK-BUS-01

Title:

Trust Layer Failure

Severity:

Critical

Risk:

Users stop trusting platform verification.

Mitigation:

* Verification Audits
* Recruiter Verification
* Transparent Trust Signals

---

### RSK-BUS-02

Title:

Billing Desynchronization

Severity:

Medium

Risk:

Mismatch between Stripe and active jobs.

Mitigation:

* Webhooks
* Reconciliation Jobs
* Active Job Audits
