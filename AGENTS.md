# SmartOnboard - AI Agent Instructions

## Project Overview

SmartOnboard is a Verified Hiring Ecosystem and AI Hiring Operating System.

The platform is designed to maximize recruiter trust and hiring quality.

This is NOT a traditional job board.

This is NOT primarily an employee onboarding platform.

This is NOT an ATS focused on application volume.

The primary objective is:

Better Applicants.
Better Hiring Decisions.
Trusted Signals.

---

# Product Mission

Help recruiters discover and hire qualified candidates through a trusted and verified ecosystem.

Help candidates discover jobs they are genuinely qualified for.

Optimize for hiring quality, not application quantity.

---

# Core Principles

## Trust Over Volume

The platform should prioritize:

* Trust
* Verification
* Signal Quality
* Recruiter Confidence

The platform should NOT optimize for:

* Application Spam
* Application Volume
* Vanity Metrics

---

## AI Is A Copilot

AI assists.

AI does not decide.

AI may:

* Rank candidates
* Summarize applicants
* Highlight risks
* Identify strengths
* Recommend interview pools

AI must never:

* Auto-hire
* Auto-reject
* Auto-schedule interviews
* Make final hiring decisions

Recruiters always retain final authority.

---

## Closed Ecosystem

Candidates must be verified.

Recruiters must be verified.

Unverified participants should not gain full access.

---

# Candidate Rules

Candidates are free.

Candidates may:

* Upload up to 3 resumes
* View applicability percentages
* Apply to jobs
* View application status
* View interview schedules

Candidates must never see:

* Risk Scores
* Authenticity Scores
* Evidence Scores
* Internal Rankings
* Recruiter Notes
* Hiring Committee Notes

---

# Recruiter Rules

Recruiters pay:

$49 per month per active job.

Recruiters may:

* Publish jobs
* Import jobs
* Review candidates
* Schedule interviews
* Manage hiring workflows

Recruiters always see the complete applicant pool.

---

# Product Boundaries

Current MVP ends at:

Offer Accepted

Employee onboarding exists as a legacy system.

Do not delete onboarding functionality.

Do not delete HRIS integrations.

Do not delete employee modules.

Legacy systems should remain hidden from primary navigation but preserved in the codebase.

---

# Current Status

Completed:

* Milestone 11.5 Security Foundation
* Milestone 12 Identity Layer

Current Milestone:

* Milestone 13 Candidate Workspace

---

# Documentation Priority

Always read:

1. AGENTS.md
2. AI_HANDOFF.md
3. CURRENT_STATUS.md
4. PRODUCT_VISION.md
5. PRD.md
6. TRD.md

before making architectural decisions.

---

# Founder Decisions

Candidates:

* Free forever

Recruiters:

* $49/month per active job

Verification:

* Twilio SMS OTP
* Email OTP
* DNS/MX validation for recruiters

Matching:

* Applicability Percentage visible to candidates

Candidate Visibility:

* Matching Skills
* Missing Skills
* Best Matching Resume

Recruiter Visibility:

* Risk Score
* Authenticity Score
* Evidence Score
* Ranking Information

---

# Important Rule

When documentation and code disagree:

1. Document the discrepancy.
2. Do not silently change architecture.
3. Generate a recommendation.
4. Await approval before major architectural changes.
