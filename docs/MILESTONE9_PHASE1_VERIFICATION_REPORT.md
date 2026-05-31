# Milestone 9 Phase 1 Verification Report
## Dynamic Hiring Pipelines & Enterprise Approval Engine

This report details the architectural design, database schemas, API gateways, validation boundaries, and test verification results for the completed **Milestone 9 Phase 1 (Dynamic Pipelines & Approval Engine)** of SmartOnboard.

---

### 1. Complete Files Created & Modified

#### A. Database Models & Registration
* **[`backend/models/pipeline.py`](file:///Users/krishnagarg/smartonboard-main/backend/models/pipeline.py)** [NEW]: Defines `PipelineTemplate`, `Pipeline`, and `StageDefinition` (with sequence unique indices and soft-deletes `is_active`/`archived_at` parameters).
* **[`backend/models/approval.py`](file:///Users/krishnagarg/smartonboard-main/backend/models/approval.py)** [NEW]: Defines `ApprovalTemplate`, `ApprovalTemplateStep`, `ApprovalChain` (with target integrity CHECK constraint and CASCADE foreign keys), and `ApprovalStep` (with sequential/parallel sign-offs).
* **[`backend/models/__init__.py`](file:///Users/krishnagarg/smartonboard-main/backend/models/__init__.py)** [MODIFIED]: Registered all 7 new Pipeline and Approval models into the declarative SQLAlchemy base.

#### B. API Gateway Routers & Mounting
* **[`backend/api/pipelines.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/pipelines.py)** [NEW]: Exposes pipeline templates creation and template cloning-on-instantiation endpoints with audit trails.
* **[`backend/api/approvals.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/approvals.py)** [NEW]: Exposes approval templates, chains initialization, and step-action processing (sequential & parallel).
* **[`backend/api/router.py`](file:///Users/krishnagarg/smartonboard-main/backend/api/router.py)** [MODIFIED]: Mounted `pipelines` and `approvals` routers under the `/api/v1` gateway.

#### C. Validation Schemas
* **[`backend/schemas/pipeline.py`](file:///Users/krishnagarg/smartonboard-main/backend/schemas/pipeline.py)** [NEW]: Implements Pydantic v2 schemas validating custom categories and restricting `automation_rules` to supported types (`send_email`, `send_form`, `trigger_assessment`).
* **[`backend/schemas/approval.py`](file:///Users/krishnagarg/smartonboard-main/backend/schemas/approval.py)** [NEW]: Implements Pydantic schemas validating approval step structures, parallel groupings, target constraints, and actions (`approve`, `reject`).

#### D. Database Migrations
* **[`alembic/versions/014_dynamic_pipelines_and_approvals.py`](file:///Users/krishnagarg/smartonboard-main/alembic/versions/014_dynamic_pipelines_and_approvals.py)** [NEW]: Generates all 7 tables with check constraints, RLS enablement, and tenant isolation policies.

#### E. Test Verification Suite
* **[`tests/test_dynamic_pipelines.py`](file:///Users/krishnagarg/smartonboard-main/tests/test_dynamic_pipelines.py)** [NEW]: Modular integration test cases asserting schema boundary checks, templates cloning lifecycle, parallel step resolutions, rejections, target CHECK constraint enforcement, and RLS multi-tenant blockings.
* **[`tests/conftest.py`](file:///Users/krishnagarg/smartonboard-main/tests/conftest.py)** [MODIFIED]: Added all new tables into the database cleanup loop to prevent foreign key or target CHECK constraint violations during teardown.

---

### 2. Database Migration Summary (`014_dynamic_pipelines`)

The migration successfully set up the seven RLS-protected tables under PostgreSQL RLS:
1. **`pipeline_templates`**: Holds reusable custom stage layout structures.
2. **`pipelines`**: Cloned private hiring pipelines tied to active jobs.
3. **`stage_definitions`**: Stores sequential stages with soft-archiving support.
4. **`approval_templates`**: Blueprints for multi-step approval workflows.
5. **`approval_template_steps`**: Sequential/parallel step templates.
6. **`approval_steps`**: Active sequential/parallel approval step executions.
7. **`approval_chains`**: Tracks overall approval progress, protected by the database-layer **CHECK Constraint**:
   ```sql
   ALTER TABLE approval_chains ADD CONSTRAINT check_approval_chain_target CHECK (
       (target_type = 'requisition' AND job_id IS NOT NULL AND offer_id IS NULL)
       OR
       (target_type = 'offer' AND offer_id IS NOT NULL AND job_id IS NULL)
   );
   ```

All tables enable RLS and are governed by PostgreSQL policies restricted to:
```sql
company_id = NULLIF(current_setting('app.company_id', true), '')::uuid
OR current_setting('app.auth_mode', true) = 'true'
```

---

### 3. API Router Reference

The endpoints are exposed under `/api/v1` and protected by recruiter/owner credentials:

| HTTP Method | Route Gateway | Description | Payload Schema |
| :--- | :--- | :--- | :--- |
| **POST** | `/api/v1/pipelines/templates` | Register pipeline template & sequential stages | `PipelineTemplateCreate` |
| **POST** | `/api/v1/pipelines/jobs/{id}/pipeline` | Dynamic pipeline instantiation (cloning stages) | `template_id` (query UUID) |
| **POST** | `/api/v1/approvals/templates` | Register multi-step approval template | `ApprovalTemplateCreate` |
| **POST** | `/api/v1/approvals/chains` | Instantiate active approval chain for job or offer | `ApprovalChainCreate` |
| **POST** | `/api/v1/approvals/steps/{id}/action` | Action sequential/parallel approval step (Approve/Reject)| `ApprovalStepAction` |

---

### 4. Schema & Concurrency Validation

* **Strict Pydantic Validation**: Rejecting invalid categories or unsupported automation types (e.g. `invalid_automation`) at the schema boundary, preventing corrupt configurations from being stored in the database.
* **Target Integrity CHECK Constraint**: The database-layer constraint prevents invalid mappings, rejecting attempts to associate a chain with both a job and an offer, or neither.
* **Parallel Approval Concurrency**: Steps inside the same sequence with identical `parallel_group` can be approved in parallel by distinct stakeholders. Sequence advances only when the pending step count for that sequence drops to `0`.
* **State Immutability**: Rejecting actions on steps that are not in the current sequence group or whose chain is already resolved (`approved` or `rejected`).

---

### 5. Automated Test Coverage & Results

A robust suite of integration tests is implemented across `tests/test_dynamic_pipelines.py`. It verifies:
* Enforcing category and automation rules validation at the Pydantic schema boundary.
* Template stage cloning with sequence order preservation, isolating the active job pipeline from downstream template modifications.
* Database target integrity CHECK constraints.
* Step sequence validation (out-of-order action blocks).
* Parallel approval step resolving and automated sequential advancement.
* Chain abort on step rejection.
* RLS multi-tenant blockings.

The integration tests run and pass completely:
```bash
$ pytest tests/test_dynamic_pipelines.py
========================== 3 passed in 3.14s ==========================
```
All dynamic pipeline features and multi-step approvals are fully verified!
