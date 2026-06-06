# Route Audit Report - Phase 13J

This report outlines the complete route audit for both client-side and server-side routes, identifying active, deprecated, duplicated, and legacy features.

---

## 1. Client-Side Routes (Frontend)

| Existing Route | Workspace | Classification | Action Details |
| :--- | :--- | :---: | :--- |
| `/` | Guest | **Keep** | Retain as the unified landing page gateway, separating recruiter and candidate paths. |
| `/login` | Guest | **Remove** | Delete unified login. Split into `/recruiter/login` and `/candidate/login`. |
| `/register` | Guest | **Remove** | Delete unified register. Split into `/recruiter/register` and `/candidate/register`. |
| `/dashboard` | Recruiter | **Redirect** | Move to `/recruiter/dashboard` with direct role guard. |
| `/candidates` | Recruiter | **Redirect** | Move to `/recruiter/candidates` with direct role guard. |
| `/pipeline` | Recruiter | **Redirect** | Move to `/recruiter/pipeline` with direct role guard. |
| `/employees` | Recruiter | **Keep (Hidden)** | Legacy HRIS onboarding. Kept in codebase but hidden from all navigation menus. |
| `/analytics` | Recruiter | **Redirect** | Move to `/recruiter/analytics` with direct role guard. |
| `/results` | Recruiter | **Redirect** | Sync results/DLQ logs. Redirect `/results` to `/recruiter/analytics` (embed Sync DLQ as a tab). |
| `/candidate` | Candidate | **Remove** | Obsolete portal redirection path. Remove entirely. |
| `/candidate/dashboard` | Candidate | **Keep** | Retain under candidate workspace. |
| `/candidate/resumes` | Candidate | **Keep** | Retain under candidate workspace. |
| `/candidate/jobs` | Candidate | **Keep** | Retain under candidate workspace. |
| `/candidate/applications` | Candidate | **Keep** | Retain under candidate workspace. |
| `/candidate/interviews` | Candidate | **Keep** | Retain under candidate workspace. |
| `/candidate/profile` | Candidate | **Keep** | Retain under candidate workspace. |
| *None (New)* | Recruiter | **Keep (New)** | Add `/recruiter/jobs` to manage company job posts. |
| *None (New)* | Recruiter | **Keep (New)** | Add `/recruiter/interviews` to manage interview events. |
| *None (New)* | Recruiter | **Keep (New)** | Add `/recruiter/settings` for recruiter configuration. |
| *None (New)* | Candidate | **Keep (New)** | Add `/candidate/settings` for candidate configuration. |

---

## 2. Server-Side Routes (Backend API)

| Existing API Endpoint | Role Scope | Classification | Action Details |
| :--- | :--- | :---: | :--- |
| `/api/v1/auth/login` | Recruiter | **Keep** | Enforce recruiter login scopes only. |
| `/api/v1/auth/register` | Recruiter | **Keep** | Enforce recruiter registration scopes only. |
| `/api/v1/auth/login/candidate` | Candidate | **Keep** | Enforce candidate login scopes only. |
| `/api/v1/auth/register/candidate` | Candidate | **Keep** | Enforce candidate registration scopes only. |
| `/api/v1/jobs/*` | Mixed | **Keep** | Recruiter read/write, Candidate read-only. Protected by RLS. |
| `/api/v1/applications/*` | Mixed | **Keep** | Recruiter read/update, Candidate read/create. Protected by RLS. |
| `/api/v1/candidates/*` | Recruiter | **Keep** | Recruiter master listing access. Locked from candidate logins. |
| `/api/v1/employees/*` | Recruiter | **Keep (Hidden)** | Kept for legacy compatibility. Restrict from menus. |
| `/api/v1/enterprise/*` | Recruiter | **Redirect/Mock** | Block billing endpoints. Replace response with Coming Soon states. |
| `/api/v1/dlq/*` | Recruiter | **Keep** | RLS logs access. Accessible under Recruiter Analytics. |

---

## 3. Decisions & Actions Summary

1. **Strict Path Role Segmentation**:
   - Recruiters are strictly isolated to `/recruiter/*`.
   - Candidates are strictly isolated to `/candidate/*`.
   - Unauthenticated visitors see only the root page `/` and independent role-based login/signup flows.
2. **Legacy Cleanup**:
   - Employee directory navigation is hidden.
   - Sync logs and metrics are consolidated under `/recruiter/analytics`.
   - Obsolete, redundant redirects (`/candidate` portal) are removed.
