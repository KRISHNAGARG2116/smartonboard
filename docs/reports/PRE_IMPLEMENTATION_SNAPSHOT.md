# Pre-Implementation Snapshot - Phase 13N

This snapshot records the state of all routes, dashboard widgets, onboarding steps, and APIs in the SmartOnboard frontend prior to making any changes for Phase 13N.

---

## 1. Existing Frontend Routes

The following active routes are defined in [App.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/App.tsx):

| Route Path | Associated React Component | Description |
|---|---|---|
| `/` | `Landing` | Main landing and entry portal |
| `/login` | `Login` | Unified login entry role-selection gateway |
| `/register` | `Register` | Unified register entry role-selection gateway |
| `/recruiter/login` | `RecruiterLogin` | Recruiter-specific authentication |
| `/recruiter/register` | `RecruiterRegister` | Recruiter-specific onboarding registration |
| `/candidate/login` | `CandidateLogin` | Candidate-specific authentication |
| `/candidate/register` | `CandidateRegister` | Candidate-specific profile registration |
| `/recruiter/dashboard` | `RecruiterDashboard` | Recruiter "Hiring Command Center" |
| `/recruiter/jobs` | `RecruiterJobs` | Recruiter job listings manager |
| `/recruiter/candidates` | `CandidateDirectory` | Recruiter candidate talent pool directory |
| `/recruiter/pipeline` | `PipelineBoard` | Recruiter Kanban applicant pipeline |
| `/recruiter/interviews` | `RecruiterInterviews` | Recruiter interview scheduling panel |
| `/recruiter/analytics` | `AnalyticsDashboard` | Recruiter metrics and sync graphs |
| `/recruiter/settings` | `RecruiterSettings` | Recruiter settings, subscription, and DNS checks |
| `/candidate/dashboard` | `CandidateDashboard` | Candidate "Career Hub" |
| `/candidate/resumes` | `ResumeLibrary` | Candidate resume management and uploads |
| `/candidate/jobs` | `CandidateJobFeed` | Candidate job recommendation feed |
| `/candidate/applications` | `CandidateApplications` | Candidate application tracking status |
| `/candidate/interviews` | `CandidateInterviews` | Candidate interview schedules and booking |
| `/candidate/profile` | `CandidateProfilePage` | Candidate profile details and verification OTP forms |
| `/candidate/settings` | `CandidateSettings` | Candidate preference configuration |

---

## 2. Dashboard Widgets Inventory

### 2.1 Recruiter Dashboard Widgets (`RecruiterDashboard.tsx`)
- **Metric Counter Cards**:
  - Open Job Openings
  - Total Candidate Records
  - Active Pipeline funnels
  - Upcoming Scheduled Interviews
- **AI Resume Processing Queue**: Real-time screening pipeline list.
- **AI Command Center (AI Matching Details)**: Selected candidate overview showcasing suitability index, missing skills, match breakdown, and brief generators.
- **Action Center**: Warnings for DNS/MX settings, billing errors, and unverified credentials.
- **Active Open Job list**: Table displaying active job profiles.
- **Active Candidate pool**: Table displaying applications with suitability scores.
- **Interviews list**: Upcoming calendar slots.

### 2.2 Candidate Dashboard Widgets (`CandidateDashboard.tsx`)
- **Profile Completion Gauge**: Conic percentage meter tracking email, phone, resume, and bio setup.
- **Profile Setup Checklist**: Actionable tasks to verify credentials, upload resumes, and update bio.
- **Identity & Verification Badges**: SMS OTP / Email OTP status indicators.
- **Active Resumes Widget**: Grid displaying current uploaded documents and status.
- **Recommended Openings Feed**: Matching job listings filtered by skills and score.
- **Active Applications Tracker**: Application status cards (Applied, Under Review, Interview, Decided).
- **Upcoming Interviews Widget**: Scheduled interview calls.

---

## 3. Onboarding Steps Inventory

### 3.1 Recruiter Onboarding Wizard (`RecruiterOnboardingWizard.tsx`)
1. **Create Company Space**: Set up company name and website domains.
2. **Post Your First Job**: Define job title, department, description, and start date.
3. **Configure Hiring Pipeline**: Select stages (Screening, Technical Interview, Offer).
4. **Invite Team Members**: Add co-recruiters.
5. **Setup Complete**: Onboarding finalize confirmation.

### 3.2 Candidate Onboarding Wizard (`CandidateOnboardingWizard.tsx`)
1. **Profile Biography**: Input profile biography summary.
2. **Upload Primary Resume**: Upload pdf/doc files.
3. **Verify Email OTP**: Request and enter validation OTP.
4. **Verify Phone OTP**: Request and enter validation SMS OTP.
5. **Confirm Primary Skills**: Check and add skills tags.
6. **Setup Complete**: Candidate dashboard redirect.

---

## 4. API Endpoints Currently Used by Dashboards

The following endpoints in [api.ts](file:///Users/krishnagarg/smartonboard-main/frontend/src/api.ts) support dashboard operations:

- **Recruiter Workspace**:
  - `GET /v1/companies/me` (`fetchCompany`)
  - `GET /v1/jobs` (`fetchJobs`)
  - `GET /v1/applications` (`fetchApplications`)
  - `POST /v1/jobs` (`createJob`)
  - `POST /v1/applications` (`createApplication`)
  - `POST /v1/applications/{id}/interviews` (Quick interview scheduling)
  - `POST /v1/applications/recruit` (`recruitCandidate`)
- **Candidate Workspace**:
  - `GET /v1/auth/candidate/resumes` (`fetchCandidateResumes`)
  - `GET /v1/auth/candidate/me` (`fetchCandidateProfile`)
  - `GET /v1/applications/me` (`fetchMyApplications`)
  - `GET /v1/candidate/interviews` (`fetchMyInterviews`)
  - `PUT /v1/auth/candidate/profile` (`updateCandidateProfile`)
  - `GET /v1/jobs/feed` (`fetchJobFeed`)
