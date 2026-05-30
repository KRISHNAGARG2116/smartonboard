# Milestone 3B Phase 2 Verification Report: Production-Grade Document Upload Security

This engineering report verifies the successful implementation of production-grade document upload security for SmartOnboard. We have implemented magic-number file signature validation, dynamic and static malware scanning (integrating ClamAV), a secure quarantined upload pipeline, and a modular storage abstraction layer with execution prevention and UUID-hashed storage.

---

## Summary of Changes

We introduced four new security modules and updated two existing files to establish a defense-in-depth upload protection scheme:

1. **File Signature (Magic Number) Validation**:
   - Integrated `puremagic` to identify the actual file types (by inspecting headers/magic bytes) instead of trusting user-provided file extensions or MIME-types.
   - Enforced a strict whitelist of allowed formats: **PDF**, **DOCX**, and **TXT** (TXT is verified by successful UTF-8 decoding fallback).
   - Dynamic ZIP/DOCX mapping resolves OOXML structures seamlessly.

2. **Malware Scanning Layer (ClamAV)**:
   - Integrated `clamd` to dynamically stream uploads to a ClamAV socket daemon (`localhost:3310` by default).
   - Designed a secure and resilient hybrid check:
     - **Static Scan**: Searches file bytes for the standard industry `EICAR` antivirus test signature in all environments (zero-socket dependency for safe local/CI/CD offline testing).
     - **Dynamic ClamAV Scan**: Streams file contents directly to ClamAV.
     - **Startup Verification**: On server lifespan startup, pings the ClamAV daemon. If unreachable:
       - In **production mode**, it crashes the startup immediately (`SystemExit`), preventing unsafe server operations.
       - In **development/testing mode**, it logs a critical warning and enables a fallback (relying on static EICAR checks) to prevent local development blockers.

3. **Secure Storage Abstraction Layer**:
   - Authored an abstract `StorageService` interface and a concrete `LocalStorageService` implementation to prepare the platform for future S3-compatible cloud storage.
   - **Execution Prevention**: Writes files with strict `0o644` permissions (read/write only, no execution rights).
   - **UUID Randomization & Traversal Defense**: Saves files in randomized UUID formats (`{uuid4}.dat`) inside tenant-specific directories, hiding original names and blocking path-traversal attacks. Resolution of paths is strictly validated against the base directory root.

4. **Quarantined Processing Pipeline**:
   - Structured the upload routes `/api/screen/upload` and `/api/recruit` in `backend/server.py` to enforce a strict lifecycle:
     - **Quarantine Stage**: Uploaded files are written directly into a separate quarantined folder inside the local storage base directory.
     - **Validation & Scan Stage**: Files are dynamically scanned for malware and validated for magic bytes in quarantine.
     - **Cleanup on Error**: If any scanner, signature, or size check fails, the file is immediately and securely deleted from quarantine, and a `400 Bad Request` or `413 Payload Too Large` is returned with detailed security alerts.
     - **Promotion Stage**: Safe files are promoted from quarantine to secure tenant storage.
     - **AI Pipeline Feed**: Scanned and verified files are passed to a secure text-extractor before entering the AI evaluation pipeline.

5. **Safe Pure-Python DOCX Text Extractor**:
   - Implemented a dependency-free, high-performance XML parser to extract paragraph texts from OOXML structures (`word/document.xml`), ensuring 100% portability.

---

## Files Modified & Created

* **[NEW]** [backend/core/malware.py](file:///Users/krishnagarg/smartonboard-main/backend/core/malware.py) — Dynamic/Static malware scanner & startup validator.
* **[NEW]** [backend/core/storage.py](file:///Users/krishnagarg/smartonboard-main/backend/core/storage.py) — Storage abstraction & secure LocalStorage implementation.
* **[MODIFY]** [backend/core/signature.py](file:///Users/krishnagarg/smartonboard-main/backend/core/signature.py) — Extended with DOCX XML extraction and unified text parser.
* **[MODIFY]** [backend/server.py](file:///Users/krishnagarg/smartonboard-main/backend/server.py) — Configured ClamAV startup hook, storage instance, and refactored upload routes with quarantine lifecycles.
* **[MODIFY]** [backend/agents/resume_parser.py](file:///Users/krishnagarg/smartonboard-main/backend/agents/resume_parser.py) — Refactored to support parsing PDF, DOCX, and TXT using magic signature validation.
* **[NEW]** [tests/test_upload_security.py](file:///Users/krishnagarg/smartonboard-main/tests/test_upload_security.py) — Automated test suite covering the entire upload threat model.

---

## Vulnerability Remediation Analysis

### Previous State (The Threat)
Previously, the system trusted user-provided filenames and extensions. A malicious user could:
- Upload an executable script disguised with a `.pdf` extension (e.g., `payload.pdf`), allowing a local file inclusion/execution attack.
- Upload an infected file containing active malware or trojans, risking infrastructure compromise.
- Cause a service crash or file leak by attempting path traversal (e.g., `/../../etc/passwd`).

### Remediation (The Solution)
With the new production-grade security controls:
- **Disguised payloads are blocked**: A file's signature is checked using binary headers. If a text or binary script is renamed to `.pdf`, it fails validation and is instantly discarded.
- **Malware is blocked**: ClamAV scans the files, and the system statically checks for standard EICAR patterns.
- **No Direct Execution / Path Traversal**: Files are randomized, placed in UUID subfolders, and written with non-executable permissions (`0o644`). Path deletion is strictly bounded to the storage directory root.
- **Strict Isolation**: Files are quarantined first; only scanned, verified files can enter the permanent storage and AI evaluation systems.

---

## Test Results

The entire automated test suite (including registration, RLS policies, rate limiting, and all new upload security tests) was executed. All 24 tests passed successfully in 10.75 seconds.

### Test Execution Output

```
============================= test session starts ==============================
platform darwin -- Python 3.11.5, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/krishnagarg/smartonboard-main
configfile: pyproject.toml
plugins: asyncio-1.4.0, langsmith-0.8.7, anyio-4.13.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 24 items

tests/test_auth_registration.py .....                                    [ 20%]
tests/test_auth_security.py ....                                         [ 37%]
tests/test_ingress_security.py ....                                      [ 54%]
tests/test_tenant_rls.py ....                                            [ 70%]
tests/test_upload_security.py .......                                    [100%]

======================= 24 passed, 5 warnings in 10.75s ========================
```

---

## Remaining Risks & Mitigations

1. **Local Disk Space Exhaustion**:
   - *Risk*: A denial-of-service (DoS) attack where a large number of rapid 4.9MB uploads fill up local storage.
   - *Mitigation*: Combine existing slowapi rate limiters (which are tenant-aware and endpoint-aware) with disk quotas or automated garbage collection on the temporary quarantined/promoted upload directories.

2. **Network Latency during ClamAV Scans**:
   - *Risk*: Dynamic network socket scans to ClamAV add latency to HTTP upload responses.
   - *Mitigation*: Ensure the ClamAV daemon is co-located on a high-speed local network or Unix socket, or transition the scan to an asynchronous background worker task using a fast message broker (e.g. Celery/Redis).

---

## Recommended Next Milestone
- **Milestone 4: Cloud Storage Migration & Asynchronous Security Pipelines**:
  - Migrate the storage service implementation from `LocalStorageService` to a cloud-native `S3StorageService` (using AWS S3, Cloudflare R2, or Google Cloud Storage).
  - Offload malware scanning and AI processing from the request-response thread into async background worker jobs.
