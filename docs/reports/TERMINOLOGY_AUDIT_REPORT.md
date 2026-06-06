# Terminology Audit Report - Phase 13J

This report documents the translation of technical, database-oriented, and system-level jargon into recruiter and candidate-friendly terminology across all workspaces, navigation headers, and documents.

---

## 1. Terminology Translation Reference Table

| Legacy/Technical Term | Area | Target Product Term | Design Rationale |
| :--- | :--- | :--- | :--- |
| **Candidate Directory** | Recruiter Nav/Page | **Candidates** | Simple, clean, instantly communicates the applicant list. |
| **User Directory** | Settings/Nav | **Users** | More natural term for teammates/recruiter profiles. |
| **Applicant Repository** | Dashboards/Tables | **Candidates** | Eliminates cold database jargon; aligns with talent pools. |
| **Match Score** | Candidate Portal | **Applicability Match** | Friendlier candidate-facing term that implies fit rather than raw grade. |
| **Match Score** | Recruiter Portal | **Match Score** | Standard recruiting terminology indicating AI-driven parsing score. |
| **Tenant** | App Shell / Dropdowns | **Workspace** | Translates technical multi-tenancy concept into a collaboration space. |
| **DLQ sync records** | Recruiter Logs / Admin | **System Sync Logs** | Simplifies technical queue terminology for support operations. |
| **Command Palette** | Navigation Shell | **Quick Command** | Easier to understand search / command bar terminology. |

---

## 2. Enforcement Standards

1. **Navigation Menu Labels**: Sidebar menus must use the target term (e.g. `Candidates` instead of `Candidate Directory`).
2. **Dashboard Headers**: Card widgets and overview panels must display the simplified wording.
3. **Database Column Alignments**: Underneath, schemas use `match_score`, but the frontend parses and formats it as `Match Score` (for recruiters) and `Applicability Match` (for candidates).
