# Verification Report: Milestone 6 Phase 2 — Redis + Celery Async Task Queue

This document provides complete engineering and compliance verification for **Milestone 6: AI Semantic Search & Background Queue (Phase 2)**.

---

## 1. Executive Summary

We have successfully migrated the slow, blocking LangGraph AI resume parsing and semantic embedding processing pipeline to a fully asynchronous background task model using **Redis + Celery**. 

Key capabilities established:
- **Redis Service**: Defined as a service in `docker-compose.yml` on port `6379`.
- **In-Memory Eager Test Routing**: Configured the test suite to route broker and backend dispatches entirely in-memory (`memory://` and `cache+memory://`) using Celery's `task_always_eager` and `task_store_eager_result` flags, eliminating external system dependencies during tests.
- **Idempotency Guarantee**: Configured check-before-insert lookups for `Candidate` and `Application` entities, and delete-before-insert wipes for `CandidateEmbedding` indexes inside Celery tasks to ensure retries or duplicate dispatches never create duplicate records.
- **24-Hour Result Retention**: Set Celery results expiration `result_expires = 86400` to prevent memory growth inside the Redis store.
- **Failed Compliance Event**: Integrated retry exhaustion hooks and terminal failure catch blocks to emit the `ai.evaluation_failed` event containing `evaluation_id`, `error_type`, and `retry_count`.
- **FastAPI Endpoints**: Exposed `/applications/async` and `/applications/async/status/{task_id}` for recruiters under strict RLS.

All Phase 2 goals have been implemented and verified through the automated test suite.

---

## 2. Component Layout & Idempotent Tasks

### 2.1 Celery Setup (`backend/core/celery_app.py`)
Configures the Celery app connection URLs and binds the 24-hour expiration policy:
```python
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    result_expires=86400, # 24 hours result retention
    task_always_eager=os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true",
    task_store_eager_result=True
)
```

### 2.2 Idempotent Task (`backend/celery_worker.py`)
Performs the parsing, LangGraph invoke, and vector chunks indexing. Wraps operations within the database `tenant_context` context manager scoped to the `company_id`.

Enforces idempotency:
- Candidate: Scopes lookup by `company_id` and `email` before inserting.
- Application: Checks if job-to-candidate application already exists before creating.
- Embeddings: Calls a clean delete-before-insert on the candidate's existing indexes to completely prevent unique constraint failures (`uq_candidate_embeddings_company_candidate_chunk`) on rerun or retry dispatches.

---

## 3. Failure Recovery & Retry Strategy

Transient failures (such as Groq rate limits, HTTP 429s, or database locks) are caught and automatically retried with exponential backoff and randomized jitter inside `@celery_app.task(bind=True, max_retries=5)`.

If the task fails permanently (due to a terminal error or retries exhausted):
- Cleans up database transaction boundaries.
- Emits the `ai.evaluation_failed` audit event into `audit_logs` capturing:
  * `evaluation_id`
  * `error_type`
  * `retry_count`
  - While adhering strictly to the recursive key-masking PII sanitization filters.

---

## 4. Verification Test Suite

We authored 5 comprehensive, self-contained integration tests inside `tests/test_async_processing.py`:

1. **`test_celery_config_result_retention`**: Asserts result retention is capped at 24 hours (`86400` seconds) and eager settings bind correctly.
2. **`test_async_task_dispatch_and_polling`**: Verifies file promotional checks, secure uploads, Celery task scheduling, poller status returns (`202 Accepted` $\rightarrow$ `COMPLETED`), and multi-tenant RLS isolation blocks cross-tenant leakage.
3. **`test_celery_task_idempotency`**: Enqueues and runs the task twice for the same candidate and verifies that only a single Candidate, a single Application, and exactly two BGE embeddings (from `\n\n` split chunks) exist without constraint violations.
4. **`test_celery_task_failures_and_failed_audit_event`**: Simulates a permanent exception inside the task execution and verifies it logs the `ai.evaluation_failed` event containing the exact metadata parameters.
5. **`test_celery_retry_backoff_trigger`**: Simulates Groq `429` rate limits and verifies task invokes `retry()` with the appropriate backoff delay.

---

## 5. Test Results

### Isolated Integration Tests:
```text
tests/test_async_processing.py .....                                     [100%]

======================== 5 passed, 3 warnings in 14.07s ========================
```
All background queue, task, and endpoint tests are completely green.
