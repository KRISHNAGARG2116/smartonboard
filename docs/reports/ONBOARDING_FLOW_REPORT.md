# First-Time User Onboarding Flow Report - Phase 13J

This report defines the guided, step-by-step onboarding journeys for new Recruiters and Candidates, preventing them from being dropped into a blank dashboard.

---

## 1. Onboarding Detection and State Tracking

1. **Detection Flag**: We will use a state attribute in the user profile model (or local persistent storage metadata `oryzo_onboarded_v1`) to track whether a user has finished their onboarding wizard.
2. **Workflow Guard**: If `has_onboarded` is false, the user dashboard will render a full-screen, focused stepper wizard. Standard navigation links in the sidebar are disabled/locked during this flow to prevent users from escaping the onboarding sequence.

---

## 2. Recruiter Onboarding Journey

A recruiter's dashboard experience starts with configuring their company workspace.

```mermaid
graph LR
    Start([Register]) --> Company[1. Create Company]
    Company --> Verify[2. Verify Organization]
    Verify --> Job[3. Create First Job]
    Job --> Pipeline[4. Configure Pipeline]
    Pipeline --> Ready([Start Recruiting])
```

### Flow Steps
1. **Create Company**: Recruiter inputs basic organization details (Company name, headquarters location, website, scale).
2. **Verify Organization**: Recruiter configures DNS/MX verification domains to establish recruiter verification status.
3. **Create First Job**: Recruiter adds their first job opening (Title, Department, Job Description).
4. **Configure Hiring Pipeline**: Recruiter chooses pipeline milestones (e.g., screening, technical exam, culture check, executive interview).
5. **Start Recruiting**: Saves states, toggles `has_onboarded` to true, and drops them into the active Recruiter Dashboard.

---

## 3. Candidate Onboarding Journey

A candidate's dashboard experience focuses on establishing identity verification and loading credentials.

```mermaid
graph LR
    Start([Register]) --> Profile[1. Create Profile]
    Profile --> Resume[2. Upload Resume]
    Resume --> Email[3. Verify Email]
    Email --> Phone[4. Verify Phone]
    Phone --> Skills[5. Complete Skills]
    Skills --> Ready([Browse Jobs])
```

### Flow Steps
1. **Create Profile**: Candidate inputs core bio details and job search preferences.
2. **Upload Resume**: Uploads a primary resume document (triggering background parsing to populate basic profile skills).
3. **Verify Email**: Candidate inputs the OTP verification code sent to their registered email address.
4. **Verify Phone**: Candidate inputs the SMS OTP verification code sent to their phone number.
5. **Complete Skills**: Candidate confirms extracted skills list and updates missing keywords.
6. **Browse Jobs**: Saves state, unlocks applicability matching percentages, and launches Candidate Job Feed.
