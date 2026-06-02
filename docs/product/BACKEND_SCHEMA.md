# SmartOnboard Backend Schema

## Core Tables

### users

Stores:

* Recruiters
* Candidates

---

### companies

Stores:

* Organization Information
* Verification Status
* Billing Information

---

### candidate_profiles

Stores:

* Candidate Metadata
* Skills
* Experience
* Profile Information

---

### verification_tokens

Stores:

* Email OTP
* SMS OTP
* Verification State

---

### jobs

Stores:

* Job Listings
* Requirements
* Status
* Deadlines

---

### applications

Stores:

* Candidate Applications

---

### application_snapshots

Stores immutable resume copies used during application submission.

---

### company_trust_metrics

Stores:

* Recruiter Trust Signals
* Verification States
* Employer Metrics

---

## Future Tables

Potential:

* Candidate Trust Metrics
* Employment Verification
* Identity Verification
