# Milestone 9 Phase 3 Verification Report: Hiring Committee Reviews & Weighted Evaluations

We have successfully completed the implementation of **Milestone 9 Phase 3 (Hiring Committee Reviews & Weighted Evaluations)**. This implementation introduces secure, multi-tenant hiring committee reviews, weighted scorecards, structured consensus scoring, standard deviation-based dispute routing, configurable skill-based veto checks, dispute reconciliation by authorized personnel (Chairs/Owners), and automated offer approval pipeline handoffs.

---

## 1. Executive Summary

Milestone 9 Phase 3 establishes a robust, enterprise-ready candidate evaluation system that guarantees hiring consistency. By snapshotting the committee membership at review initiation, the system protects active review cycles against global membership changes, ensuring full regulatory compliance and process integrity. The core consensus engine dynamically normalizes reviewer weights, calculates custom standard deviations to detect and flag candidate rating divergence, and automatically routes highly polarized candidate evaluations to a `disputed` state for reconciliation. 

---

## 2. Database Design & Migration Summary (`016_hiring_committees`)

A single, clean Alembic migration (`016_hiring_committees`) was executed to construct the backend relational layout:

1. **`scorecard_templates`**: Holds structured criteria layouts per template.
2. **`scorecard_template_skills`**: Stores skill evaluation categories (e.g., Coding, System Design) and their fractional weights (validating that the sum equals exactly `1.0`).
3. **`hiring_committees`**: Registers named committees, quorum percentages, score thresholds, configurable consensus standard deviation thresholds (`consensus_sd_threshold`), array of veto skill keys (`veto_skill_keys`), and veto enabling toggles.
4. **`hiring_committee_members`**: Binds recruiters/interviewers to committees with custom reviewer weightings.
5. **`committee_reviews`**: Manages candidate evaluation cycles, tracking average scores, due dates, statuses (`pending`, `aligned_approve`, `aligned_reject`, `disputed`), and reconciliation logs.
6. **`committee_review_reviewers`**: Immutably snapshots the committee roster, weights, and roles at the moment of review initiation to lock the review group against subsequent changes.

### Multi-Tenant Row-Level Security (RLS)
All six tables are fully equipped with strict PostgreSQL Row-Level Security (RLS) policies:
```sql
ALTER TABLE scorecard_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE scorecard_templates FORCE ROW LEVEL SECURITY;
-- Same for scorecard_template_skills, hiring_committees, hiring_committee_members, committee_reviews, and committee_review_reviewers
```
Tenant isolation is enforced via Company-scoped filters:
```sql
CREATE POLICY tenant_isolation_scorecard_templates ON scorecard_templates
FOR ALL USING (company_id = NULLIF(current_setting('app.company_id', true), '')::uuid OR current_setting('app.auth_mode', true) = 'true');
```

---

## 3. Core Consensus Engine & Workflows

The consensus engine is implemented in **[`backend/core/consensus.py`](file:///Users/krishnagarg/smartonboard-main/backend/core/consensus.py)** and executes dynamically:

1. **Quorum Verification**: Assures that submitted scorecards from snapshotted reviewers satisfy the committee's required `quorum_percentage`.
2. **Reviewer Weights Normalization**: Standardizes non-uniform reviewer weights dynamically so that their sum equals `1.0` to calculate a fair, weighted overall score.
3. **Custom Standard Deviation Computation**: Calculates rating divergence:
   $$\sigma = \sqrt{\frac{\sum (Score_i - OverallScore)^2}{N}}$$
   If the calculated $\sigma \ge \text{consensus\_sd\_threshold}$, the review status automatically routes to `disputed`.
4. **Structured Veto Logic**: If a scorecard assigns a grade of `1` on a veto-enabled skill, consensus is instantly aborted, and the candidate is moved to `disputed`.
5. **Reconciliation Authorization**: Restricts manual override of disputed reviews to **Committee Chair** (snapshotted) or **Tenant Owner**. Standard recruiters receive a `403 Forbidden` response.
6. **Offer Pipeline Handoff**: If consensus aligns on an approval, the candidate application is promoted to the `offer` stage, and the system automatically instantiates a new **Offer Approval Chain** clone from active templates, emitting a `committee.offer_chain_created` event.

---

## 4. API Gateway Routers

FastAPI endpoints are structured in **[`backend/api/committees.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/committees.py)** and integrated into **[`backend/api/router.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/router.py)**:

- `POST /api/v1/scorecards/templates` - Creates scorecard criteria templates (validates sum of weights = 1.0).
- `POST /api/v1/committees` - Registers committees, members, custom reviewer weights, standard deviation thresholds, and veto policies.
- `POST /api/v1/applications/{application_id}/reviews/initiate` - Starts a review cycle and snapshots the roster.
- `POST /api/v1/reviews/{review_id}/reconcile` - Reconciles disputed reviews (restricted to Chair/Owner).
- `GET /api/v1/reviews/{review_id}` - Fetches review details, status, and scores.

---

## 5. Security & Verification Strategy

### Multi-Tenant Isolation Protection
Verification tests proved that Company B cannot query, view, or modify any committee templates, committee memberships, review cycles, or scorecards created by Company A. RLS filters securely drop all queries originating outside the tenant context, returning clean `404 Not Found` API responses.

### Dynamic Scoped Authorization
Manual dispute overrides are protected by role-verification queries that check if the acting recruiter is the snapshotted Committee Chair or a registered Company Owner. Recruiters attempting unauthorized manual reconciliations are instantly blocked with `403 Forbidden` exceptions.

---

## 6. Test Suite & Validation Results

### Local Hiring Committee Tests
A dedicated and comprehensive suite of integration tests in **[`tests/test_hiring_committees.py`](file:///Users/krishnagarg/smartonboard-main/tests/test_hiring_committees.py)** validates every aspect of the engine:

1. **`test_scorecard_template_weight_sum_validation`**: Confirms that weight sums must equal exactly `1.0` or fail validation.
2. **`test_committee_membership_snapshotting`**: Proves roster immutability; adding members globally does not affect an ongoing review.
3. **`test_configurable_sd_threshold`**: Confirms standard deviation-based dispute state transitions.
4. **`test_configurable_veto_logic`**: Validates that veto-enabled skills set to `1` trigger instant dispute state transitions.
5. **`test_reconciliation_authorization`**: Verifies that only snapshotted Chairs or Tenant Owners can reconcile disputes (and regular Recruiters are rejected with 403).
6. **`test_committee_review_consensus_weighted_normalization_and_handoff`**: Ensures weights are normalized correctly, consensus calculated, application transitioned, and Offer Approval Chain automatically spawned with a `committee.offer_chain_created` audit event.
7. **`test_multi_tenant_rls_isolation`**: Enforces strict multi-tenant boundary checks.

#### Execution Output:
```text
tests/test_hiring_committees.py .......                                  [100%]
======================== 7 passed, 4 warnings in 8.23s =========================
```

### Global Test Suite Validation
All 103 system-wide integration tests pass cleanly, ensuring zero regressions:
```text
======================= 103 passed, 8 warnings in 71.40s =======================
```

All hiring committee, weighted evaluation, and automated pipeline integration goals for Milestone 9 Phase 3 have been met with zero regressions and production-grade reliability.
