# Billing & Subscription Audit Report - Phase 13J

This report audits billing, subscription, pricing, and monetization features in the SmartOnboard platform. It distinguishes between fully implemented features and placeholders, and details the strategy to remove fake billing content from the active product UI.

---

## 1. Feature Audit & Classification Matrix

| Feature / UI Element | Scope | Classification | Current State Details | Action Required for Phase 13J |
| :--- | :--- | :---: | :--- | :--- |
| **Monetization Landing Copy** | Guest | **Placeholder** | Stat block displaying "$49/month per active job" as the plan's cost. | Keep as planned product pricing information; add "Planned pricing model" caption. |
| **Recruiter Subscription Panel** | Recruiter Settings | **Placeholder** | Currently, no billing settings page exists in the frontend client. | Create Settings page with placeholder "Subscription & Billing (Coming Soon)". |
| **Monetization API Schemas** | Backend | **Mocked / Unused** | Database schemas for plan responses and usage ledgers exist. | Keep backend schemas for future milestones; do not call or mock fake values in UI. |
| **Billing Tasks** | Backend | **Unused** | Background Celery task structures for periodic billing routines. | Keep task skeleton in backend; no UI triggers. |
| **Monetization Charts / Widgets** | Recruiter | **Remove** | No active billing graphs exist in the client. | Ensure no simulated billing or revenue metrics are added during dashboard overhaul. |

---

## 2. Incomplete Feature Strategy (Option B)

We will implement **Option B**:
- For any billing controls, we will render a clean, SmartOnboard-styled card indicating:
  > **Subscription & Billing (Coming Soon)**
  > 
  > The platform is currently in a pre-release phase. Subscription controls, active invoice management, and plan configurations will become available in the next release cycle.
- This card will be located under the new Recruiter Settings page (`/recruiter/settings`).
- We will completely avoid fake invoices, hardcoded revenue counters, or simulated checkout processes.
