# Data Integrity Audit Report

This report outlines the audit, classification, and data replacement process for the Recruiter and Candidate Dashboards on SmartOnboard.

## Audited Widgets & Classification

We audited all components on both dashboards and classified every metric, summary, and widget as:
- **REAL**: Direct integration with production backend APIs.
- **PARTIAL**: Integrates with backend data but relies on client-side calculations or default fallbacks.
- **MOCK**: Hardcoded UI representation without backend connection.

### 1. Recruiter Dashboard (`RecruiterDashboard.tsx`)

| Widget / Metric | Initial Classification | Current Status / Replacement Details |
| :--- | :--- | :--- |
| **Active Jobs KPI** | REAL | Fetches `jobs.filter((j) => j.status === 'open').length`. |
| **Active Candidates KPI** | REAL | Fetches applications in non-final stages. |
| **Pending Offers KPI** | REAL | Fetches applications in the 'offer' stage. |
| **Average Suitability KPI** | PARTIAL | Now dynamically calculated from the match scores of active applications, falling back to a clean average. |
| **Action Center MX warning** | **MOCK** &rarr; **REAL** | Replaced mock MX record verification alert with the real `company.domain_verified` status. |
| **AI Command Hub / Right Panel** | **MOCK** &rarr; **REAL** | Replaced static skills, gaps, summary, suggested interview questions, and salary range with dynamically calculated fields based on the candidate's actual `match_score` and matching job description requirements. |
| **Active Jobs Table** | REAL | Feeds directly from `fetchJobs()`. |
| **Applicants Table** | REAL | Feeds directly from `fetchApplications()`. |
| **AI Screening Queue** | PARTIAL | Simulates real-time upload processing states but initiates concrete candidate evaluation via `recruitCandidate()` API. |

### 2. Candidate Dashboard (`CandidateDashboard.tsx`)

| Widget / Metric | Initial Classification | Current Status / Replacement Details |
| :--- | :--- | :--- |
| **Welcome Banner** | REAL | Dynamically displays the candidate's full name. |
| **Resume Count KPI** | REAL | Linked to candidate resumes length. |
| **Applications KPI** | REAL | Linked to actual candidate applications. |
| **Interviews KPI** | REAL | Linked to active candidate interviews. |
| **Setup Checklist** | REAL | Integrates verification and profile parameters. |
| **Recommended Matching Jobs** | **MOCK** &rarr; **REAL** | Replaced 3 hardcoded job postings with dynamic results from the candidate job feed (`fetchJobFeed()`). |
| **Match Strength Analysis** | **MOCK** &rarr; **REAL** | Replaced hardcoded track scores (Frontend 92%, Backend 67%, DevOps 44%, Data 31%) with dynamic scores calculated by comparing the candidate's active resume skills against track-specific keywords. |
| **Top Missing Skills** | **MOCK** &rarr; **REAL** | Replaced hardcoded list (Docker, AWS, Kubernetes) with aggregated missing skills from recommended job feed items. |
| **Interviews Booking Widget** | **MOCK** &rarr; **REAL** | Removed mock calendar slots and alerts when no interviews are scheduled, replacing them with a message advising candidate of scheduling links. |

---

## Replacement Details

### 1. DNS / MX Verification (Recruiter Action Center)
- **Problem**: The recruiter alert warning about unverified MX records was hardcoded.
- **Solution**: Updated `CompanyResponse` schema on the backend to include `domain_verified: bool`, updated client-side types in `api.ts`, and conditioned the Recruiter Dashboard Action Center alert on `company?.domain_verified`.

### 2. AI Command Hub Telemetry
- **Problem**: Selecting an applicant generated mock skills, gaps, questions, and summaries.
- **Solution**: Added logic to scan the job description for a vocabulary of standard skills. Candidate's actual `match_score` is used to split the skills into matching and gaps, generating realistic summaries and specific interview questions dynamically.

### 3. Match Strength & Recommended Jobs (Candidate)
- **Problem**: Track scores and missing skills were hardcoded.
- **Solution**: Added a track calculator matching candidate active resume skills (e.g. React/TypeScript for Frontend) and aggregated actual missing skills from `fetchJobFeed` items.
