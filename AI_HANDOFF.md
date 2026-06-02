# SmartOnboard AI Hand-Off Document

## Project Summary

SmartOnboard is a Verified Hiring Ecosystem and AI Hiring Operating System.

The platform focuses on recruiter trust, candidate verification, and high-quality hiring outcomes.

The project originally began as an onboarding and employee management platform but has since pivoted into a hiring-focused ecosystem.

Legacy onboarding systems remain in the codebase and may become a future SmartOnboard Onboard product.

---

# Current Repository State

Status:

Active Development

Current Phase:

MVP Construction

Current Milestone:

Milestone 13 - Candidate Workspace

---

# Completed Milestones

## Milestone 11.5

Production Security & Reliability Foundation

Implemented:

* Rate limiting
* Secret validation
* File upload validation
* Malware scanning integration
* Security audits
* Security roadmap

---

## Milestone 12

Identity Layer

Implemented:

* Candidate identity architecture
* Candidate authentication
* Candidate authorization
* Candidate profile infrastructure
* Verification token infrastructure
* Recruiter verification foundation
* Company trust layer foundation
* Application snapshot foundation

Status:

Completed

Tests:

35/35 Passing

---

# Current Product Gap

The backend has been largely realigned to the Verified Hiring Ecosystem.

However, the frontend still primarily reflects the legacy onboarding and HRIS product.

Examples:

Current UI contains:

* Employees
* Performance
* HRIS
* Onboarding

Current UI does not yet contain:

* Candidate dashboard
* Resume library
* Applicability percentages
* Candidate job feed
* Candidate interview dashboard

This gap is expected to be addressed during Milestone 13.

---

# Immediate Next Objective

Milestone 13

Candidate Workspace & Frontend Strategic Realignment

Deliverables:

* Candidate Dashboard
* Resume Library
* Job Feed
* Applications Page
* Interviews Page
* Profile Page
* Applicability Percentage UI
* Resume Selection During Application

---

# Critical Product Decisions

## Candidate Pricing

Free forever.

---

## Recruiter Pricing

$49/month per active job.

Closed jobs are not billed.

No feature gating.

---

## Candidate Visibility

Allowed:

* Applicability Percentage
* Matching Skills
* Missing Skills
* Best Matching Resume

Restricted:

* Risk Score
* Authenticity Score
* Evidence Score
* Recruiter Rankings
* Recruiter Notes

---

## Recruiter Visibility

Recruiters may view:

* Candidate Rankings
* Risk Scores
* Authenticity Scores
* Evidence Scores
* AI Hiring Briefs

Recruiters always retain final hiring authority.

---

# Verification Decisions

Candidate Verification:

* Email OTP
* SMS OTP

Recruiter Verification:

* Domain Validation
* DNS Validation
* MX Validation

Provider:

* Twilio (SMS)

---

# AI System Principles

AI is a copilot.

AI assists decision making.

AI never:

* Auto-hires
* Auto-rejects
* Auto-schedules interviews

---

# Future Roadmap

Potential future products:

* Candidate Trust Layer
* SmartOnboard Onboard
* SmartOnboard HR
* Employment Verification
* Identity Verification

Not part of current MVP.

---

# Instructions For Future AI Agents

Before making architectural decisions:

Read:

1. AGENTS.md
2. CURRENT_STATUS.md
3. PRODUCT_VISION.md
4. PRD.md
5. TRD.md

Do not assume the current frontend reflects the current vision.

The documentation is considered the source of truth.
