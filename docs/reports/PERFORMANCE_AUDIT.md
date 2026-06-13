# SmartOnboard Performance Audit Report

This report presents a comprehensive performance audit of all API endpoints across the SmartOnboard hiring ecosystem.

## Performance Classifications
* **FAST (<500ms):** Light database operations, no external network dependencies, no heavy crypto.
* **MEDIUM (500ms–2s):** Cryptographic operations (BCrypt), external SMTP or SMS API calls, complex database queries/aggregations, or small file I/O.
* **SLOW (>2s):** Generative AI LLM calls, synchronous malware/ClamAV file scans, semantic matching calculations, or bulk processing.

---

## 1. Top 20 Endpoints Most Likely to Cause Latency Under Load

The following table lists the top 20 endpoints ordered by their potential to cause degradation or high latency under concurrent load:

| Rank | Route | Method | Primary Latency Drivers | Classification | Background Worker? |
|---|---|---|---|---|---|
| 1 | `/api/recruit` | POST | PDF text extraction, ClamAV scan, LangGraph pipeline, LLM decisioning | **SLOW (>2s)** | Yes (CRITICAL) |
| 2 | `/api/v1/jobs/{job_id}/candidate-matches` | POST | Generates search vector, computes cosine similarity in python over all candidate resumes | **SLOW (>2s)** | Yes |
| 3 | `/api/onboard` | POST | Synchrounous AI Agent training plan generation and document draft | **SLOW (>2s)** | Yes (CRITICAL) |
| 4 | `/api/screen` | POST | Synchrounous LLM call to screen resume text | **SLOW (>2s)** | Yes (CRITICAL) |
| 5 | `/api/v1/intelligence/applications/{id}/candidate-summary` | GET | Groq/Gemini LLM call (if cache is cold or invalidated) | **SLOW (>2s)** | Yes (Runs via Celery) |
| 6 | `/api/v1/intelligence/applications/{id}/scorecard-consensus` | GET | Groq/Gemini LLM call (if cache is cold or invalidated) | **SLOW (>2s)** | Yes (Runs via Celery) |
| 7 | `/api/v1/intelligence/applications/{id}/hiring-recommendation` | GET | Groq/Gemini LLM call (if cache is cold or invalidated) | **SLOW (>2s)** | Yes (Runs via Celery) |
| 8 | `/api/v1/intelligence/applications/{id}/regenerate` | POST | Invalidates cache and triggers LLM call | **SLOW (>2s)** | Yes (Runs via Celery) |
| 9 | `/api/screen/upload` | POST | Synchronous EICAR malware scan and signature validation | **MEDIUM (500ms–2s)** | Yes (Scans in Celery) |
| 10 | `/api/v1/candidate/resumes/upload` | POST | Reads file, verifies signature, saves quarantine, enqueues task | **MEDIUM (500ms–2s)** | Yes (Saves to worker) |
| 11 | `/api/v1/auth/register` | POST | Performs DNS validation (resolve A/AAAA/MX) and BCrypt hashing | **MEDIUM (500ms–2s)** | No |
| 12 | `/api/v1/auth/candidate/phone/send-otp` | POST | External Twilio API call to dispatch SMS | **MEDIUM (500ms–2s)** | Yes |
| 13 | `/api/v1/auth/candidate/email/send-otp` | POST | External SMTP connection for OTP email delivery | **MEDIUM (500ms–2s)** | Yes |
| 14 | `/api/v1/applications/apply` | POST | Calculates candidate-job match score synchronously | **MEDIUM (500ms–2s)** | No |
| 15 | `/api/v1/auth/sso/acs` | POST | IdP network handshake, SAML signature validation | **MEDIUM (500ms–2s)** | No |
| 16 | `/api/v1/auth/oidc/callback` | POST | Handshake with OIDC endpoints for token exchange | **MEDIUM (500ms–2s)** | No |
| 17 | `/api/v1/auth/calendars/{credential_id}/sync` | POST | Connects and pulls delta sync from Google/Outlook | **SLOW (>2s)** | Yes (Celery enqueued) |
| 18 | `/api/v1/auth/register/candidate` | POST | BCrypt password hashing | **MEDIUM (500ms–2s)** | No |
| 19 | `/api/v1/auth/login` | POST | BCrypt password verification | **MEDIUM (500ms–2s)** | No |
| 20 | `/api/v1/auth/login/candidate` | POST | BCrypt password verification | **MEDIUM (500ms–2s)** | No |

---

## 2. Comprehensive Endpoint Audit

### 2.1 Server Core Routes (`backend/server.py`)

#### POST `/api/onboard`
* **Average DB Queries:** None.
* **External APIs Called:** Yes (LangChain Groq/Gemini).
* **AI Processing:** Yes (Training plan, email draft).
* **Emails Sent:** No (draft returned).
* **SMS Sent:** No.
* **File Processing:** No.
* **Worker Recommendation:** Should be moved to a background worker. This endpoint executes LLM chains synchronously in the request thread, blocking the event loop.
* **Latency Class:** **SLOW (>2s)**

#### POST `/api/screen`
* **Average DB Queries:** None.
* **External APIs Called:** Yes (LangChain Groq/Gemini).
* **AI Processing:** Yes (Resume screening).
* **Emails/SMS Sent:** No.
* **File Processing:** No.
* **Worker Recommendation:** Yes, move to background Celery task.
* **Latency Class:** **SLOW (>2s)**

#### POST `/api/screen/upload`
* **Average DB Queries:** 2 (Lookup company, save quarantined file).
* **External APIs Called:** None (Synchronous static signature check, background Celery enqueued for ClamAV).
* **AI Processing:** None in HTTP thread.
* **Emails/SMS Sent:** No.
* **File Processing:** Yes (Magic bytes validation, shared storage write).
* **Worker Recommendation:** Already enqueues Celery task. The initial file upload and static checks remain in-thread.
* **Latency Class:** **MEDIUM (500ms–2s)**

#### POST `/api/recruit`
* **Average DB Queries:** 5 (Lookups, audits, company verification).
* **External APIs Called:** Yes (LangChain LLM).
* **AI Processing:** Yes (Full parsing, screening, scoring, deciding, email drafting).
* **Emails/SMS Sent:** No.
* **File Processing:** Yes (Saves to quarantine, ClamAV scan, PDF text extraction, promotes to uploads).
* **Worker Recommendation:** Yes, this massive end-to-end flow is completely synchronous and should be queued to run asynchronously.
* **Latency Class:** **SLOW (>2s)**

---

### 2.2 Authentication & Verification (`backend/api/auth.py` & `backend/api/candidate_auth.py`)

#### POST `/api/v1/auth/register`
* **Average DB Queries:** 4 (Select existing users, insert company, insert user, insert audit log).
* **External APIs Called:** Yes (DNS resolver queries).
* **AI Processing:** No.
* **Emails/SMS Sent:** No.
* **File Processing:** No.
* **Worker Recommendation:** Keep in request thread, but DNS timeouts should be set aggressively.
* **Latency Class:** **MEDIUM (500ms–2s)**

#### POST `/api/v1/auth/login`
* **Average DB Queries:** 3 (Select user, insert session, update activity).
* **External APIs Called:** None.
* **AI Processing:** No.
* **Emails/SMS Sent:** No.
* **File Processing:** No.
* **Worker Recommendation:** No. BCrypt verify is CPU-bound but must block.
* **Latency Class:** **MEDIUM (500ms–2s)** (Takes ~100ms for CPU BCrypt block).

#### POST `/api/v1/auth/register/candidate`
* **Average DB Queries:** 3 (Check existing, insert user, insert profile).
* **External APIs Called:** None.
* **AI Processing:** No.
* **Emails/SMS Sent:** No.
* **File Processing:** No.
* **Worker Recommendation:** No.
* **Latency Class:** **MEDIUM (500ms–2s)** (BCrypt hashing).

#### POST `/api/v1/auth/login/candidate`
* **Average DB Queries:** 3 (Select user, insert session).
* **External APIs Called:** None.
* **AI Processing:** No.
* **Emails/SMS/Files:** No.
* **Worker Recommendation:** No.
* **Latency Class:** **MEDIUM (500ms–2s)**.

#### POST `/api/v1/auth/candidate/email/send-otp`
* **Average DB Queries:** 2 (Select user, insert token).
* **External APIs Called:** Yes (SMTP mail provider).
* **AI Processing:** No.
* **Emails Sent:** Yes (Verification OTP).
* **SMS Sent:** No.
* **File Processing:** No.
* **Worker Recommendation:** Yes, moving SMTP connection to a background worker would speed up HTTP response.
* **Latency Class:** **MEDIUM (500ms–2s)**

#### POST `/api/v1/auth/candidate/phone/send-otp`
* **Average DB Queries:** 2.
* **External APIs Called:** Yes (Twilio SMS API).
* **AI Processing:** No.
* **Emails Sent:** No.
* **SMS Sent:** Yes.
* **File Processing:** No.
* **Worker Recommendation:** Yes, Twilio delivery should be queued.
* **Latency Class:** **MEDIUM (500ms–2s)**

#### POST `/api/v1/auth/candidate/email/verify-otp` & `/phone/verify-otp`
* **Average DB Queries:** 3 (Verify token, update status).
* **External/AI/Emails/SMS/Files:** None.
* **Worker Recommendation:** No.
* **Latency Class:** **FAST (<500ms)**

---

### 2.3 Candidate Resumes & Applications (`backend/api/candidate_resumes.py` & `backend/api/candidate_applications.py`)

#### POST `/api/v1/candidate/resumes/upload`
* **Average DB Queries:** 3 (Check count, insert quarantined file).
* **External APIs Called:** None.
* **AI Processing:** None in HTTP thread (background enqueued).
* **Emails/SMS Sent:** No.
* **File Processing:** Yes (Reads file, checks signatures, saves locally).
* **Worker Recommendation:** Already enqueues Celery task.
* **Latency Class:** **MEDIUM (500ms–2s)**

#### POST `/api/v1/applications/apply`
* **Average DB Queries:** 8 (Check job, verify resume ownership, check duplicate app, upsert candidate, insert application, insert snapshot).
* **External APIs Called:** None.
* **AI Processing:** No.
* **Emails/SMS Sent:** No.
* **File Processing:** No.
* **Worker Recommendation:** No. Match score is calculated synchronously via light text metrics, but snapshot DB operations are synchronous.
* **Latency Class:** **MEDIUM (500ms–2s)**

#### POST `/api/v1/applications/{id}/withdraw`
* **Average DB Queries:** 5 (Lookup app/candidate/owner user, update application status).
* **External APIs/AI/Emails/SMS/Files:** None (drafts return in body).
* **Worker Recommendation:** No.
* **Latency Class:** **FAST (<500ms)**

---

### 2.4 Recruiter Jobs & Matching (`backend/api/jobs.py`)

#### POST `/api/v1/jobs/{job_id}/candidate-matches`
* **Average DB Queries:** 3 (Select job, select candidate embeddings).
* **External APIs Called:** None (Generates embedding locally via huggingface service).
* **AI Processing:** Yes (Similarity comparison).
* **Emails/SMS/Files:** No.
* **Worker Recommendation:** Yes. When candidate database size is large, computing cosine similarity for multiple chunks per candidate in Python block memory is SLOW. Should be offloaded or optimized via PGVector.
* **Latency Class:** **SLOW (>2s)** under concurrent load.

---

### 2.5 Recruiter Intelligence (`backend/api/intelligence.py`)

#### GET `/api/v1/intelligence/applications/{id}/candidate-summary`
* **Average DB Queries:** 4 (Lookup application, verify insight checksum, select cached insight).
* **External APIs Called:** Yes, if cache misses (LLM call).
* **AI Processing:** Yes.
* **Emails/SMS/Files:** No.
* **Worker Recommendation:** Already enqueues Celery task.
* **Latency Class:** **FAST (<500ms)** on cache hit; **SLOW (>2s)** on cache miss.

#### GET `/api/v1/intelligence/applications/{id}/scorecard-consensus`
* **Average DB Queries:** 4.
* **External APIs/AI/Emails/SMS/Files:** Same as candidate-summary.
* **Latency Class:** **FAST (<500ms)** on cache hit; **SLOW (>2s)** on cache miss.

#### GET `/api/v1/intelligence/applications/{id}/hiring-recommendation`
* **Average DB Queries:** 4.
* **External APIs/AI/Emails/SMS/Files:** Same as candidate-summary.
* **Latency Class:** **FAST (<500ms)** on cache hit; **SLOW (>2s)** on cache miss.

#### POST `/api/v1/intelligence/applications/{id}/regenerate`
* **Average DB Queries:** 4.
* **External APIs Called:** Yes (Triggers async LLM).
* **AI Processing:** Yes.
* **Emails/SMS/Files:** No.
* **Worker Recommendation:** Already enqueues task.
* **Latency Class:** **MEDIUM (500ms–2s)**

---

### 2.6 Calendar & Scheduling (`backend/api/calendars.py` & `backend/api/scheduling.py`)

#### POST `/api/v1/auth/calendars/{credential_id}/sync`
* **Average DB Queries:** 2 (Lookup credential, enqueues sync task).
* **External APIs Called:** Yes (Google or Outlook api via background Celery sync).
* **AI/Emails/SMS/Files:** No.
* **Worker Recommendation:** Already enqueues.
* **Latency Class:** **FAST (<500ms)**

#### GET `/api/v1/schedule/{raw_token}/availability`
* **Average DB Queries:** 4 (Get link token, switch context, fetch calendar free-busy details).
* **External APIs Called:** Yes (Google or Outlook free-busy API connection).
* **AI/Emails/SMS/Files:** No.
* **Worker Recommendation:** No, must return real-time calendar availability to client.
* **Latency Class:** **MEDIUM/SLOW (500ms–2s)**

#### POST `/api/v1/schedule/{raw_token}/book`
* **Average DB Queries:** 8 (Lookup slots, verify overlap, create interview/slot, save external invite ID).
* **External APIs Called:** Yes (Creates calendar invite via Google/Outlook).
* **AI/Emails/SMS/Files:** No.
* **Worker Recommendation:** No, blocks for real-time calendar invitation receipt.
* **Latency Class:** **MEDIUM/SLOW (500ms–2s)**

---

### 2.7 Other Recruiter Routes (`backend/api/applications.py`, `backend/api/audit.py`, `backend/api/analytics.py`)

#### GET `/api/v1/analytics/export`
* **Average DB Queries:** 2 (Fetches interaction rows).
* **External APIs/AI/Emails/SMS:** None.
* **File Processing:** Yes (Compiles CSV dynamically in memory).
* **Worker Recommendation:** Recommended to use async queue `/export` rather than synchronous fallback.
* **Latency Class:** **MEDIUM (500ms–2s)**

#### GET `/api/v1/audit/logs/export`
* **Average DB Queries:** 2.
* **External APIs/AI/Emails/SMS:** None.
* **File Processing:** Yes (Compiles CSV).
* **Worker Recommendation:** Yes, should be moved to background worker.
* **Latency Class:** **MEDIUM (500ms–2s)**
