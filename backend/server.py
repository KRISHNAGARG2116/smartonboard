from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Allow `from pipeline import …` when started as `uvicorn backend.server:app` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Initialize structured logging configuration
from core.logging_config import setup_logging
setup_logging()

# Initialize Sentry Error Monitoring if DSN is configured
import sentry_sdk

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
    print("Sentry SDK initialized successfully for API server")

from api.router import v1_router
from db.session import SessionLocal, engine, tenant_id_var
from pipeline import onboard_employee, process_candidate
from agents.screening_agent import screen_resume_text as _screen_text

from core.malware import scan_file_for_malware
from core.signature import validate_file_signature, extract_text_from_file_bytes
from core.storage import LocalStorageService

# Initialize secure storage abstraction layer
STORAGE_BASE_DIR = Path(__file__).resolve().parent.parent / "storage"
storage_service = LocalStorageService(STORAGE_BASE_DIR)


from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from core.limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify ClamAV daemon connection on startup
    from core.malware import verify_clamav_connection
    verify_clamav_connection()

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection OK")
    except Exception as exc:
        print(f"WARNING: Database unavailable: {exc}")
    yield


app = FastAPI(title="SmartOnboard API", version="2.1.0", lifespan=lifespan)
app.state.limiter = limiter

from fastapi.responses import JSONResponse

async def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    try:
        from core.audit import log_audit_event
        from db.session import SessionLocal
        
        with SessionLocal() as db:
            log_audit_event(
                db=db,
                action="security.rate_limit_violation",
                actor_type="UNAUTHENTICATED",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={"path": request.url.path, "detail": str(exc)}
            )
    except Exception as e:
        print(f"Failed to log rate limit violation audit event: {e}")
        
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"}
    )

app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

from core.middleware import IPWhitelistMiddleware, ContentSecurityPolicyMiddleware, RequestSanitizationMiddleware, CorrelationIDMiddleware

app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(IPWhitelistMiddleware)
app.add_middleware(ContentSecurityPolicyMiddleware)
app.add_middleware(RequestSanitizationMiddleware)

cors_origins_str = os.getenv("ALLOWED_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
if cors_origins_str == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


class OnboardRequest(BaseModel):
    name: str
    role: str
    department: str
    start_date: str
    email: str


class ScreenRequest(BaseModel):
    job_role: str
    job_description: Optional[str] = ""
    resume_text: str


@app.get("/api/health")
def health_check():
    has_key = bool(os.getenv("GROQ_API_KEY"))
    db_ok = False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    status = "ok" if db_ok else "degraded"
    if not has_key:
        status = "degraded"

    return {
        "status": status,
        "service": "SmartOnboard API",
        "version": "2.1.0",
        "database_connected": db_ok,
        "groq_api_key_configured": has_key,
    }


MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@app.post("/api/onboard")
@limiter.limit("5/minute")
async def onboard(request: Request, body: OnboardRequest):
    try:
        result = onboard_employee(
            name=body.name,
            role=body.role,
            department=body.department,
            start_date=body.start_date,
            email=body.email,
        )
        return {
            "success": True,
            "employee_name": result["employee_name"],
            "role": result["role"],
            "department": result["department"],
            "documents_generated": result["documents_generated"],
            "training_plan": result["training_plan"],
            "email_draft": result["email_draft"],
            "qa_context": result["qa_context"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/api/screen")
@limiter.limit("5/minute")
async def screen_text(request: Request, body: ScreenRequest):
    try:
        result = _screen_text(
            resume_text=body.resume_text,
            job_role=body.job_role,
            job_description=body.job_description or "",
        )
        return {"success": True, "analysis": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


def get_or_create_sandbox_company(db) -> uuid.UUID:
    from models.company import Company
    from models.enums import CompanyStatus
    from sqlalchemy import select
    
    # Query for any company
    company = db.scalar(select(Company).limit(1))
    if company:
        return company.id
        
    # Create default sandbox company
    sandbox = Company(
        name="Sandbox Company",
        slug="sandbox",
        status=CompanyStatus.ACTIVE,
        settings={}
    )
    db.add(sandbox)
    db.flush()
    return sandbox.id


@app.post("/api/screen/upload", status_code=202)
@limiter.limit("5/minute")
async def screen_upload(
    request: Request,
    file: UploadFile = File(...),
    job_role: str = Form(...),
    job_description: str = Form(""),
):
    # 1. Early Content-Length check
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 5 MB.")

    try:
        content = await file.read()
        # 2. Strict read length check
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 5 MB.")

        if not content:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # 3. Magic Bytes Signature & Static Malware Validation in Request Thread
        from core.malware import EICAR_SIGNATURE
        if EICAR_SIGNATURE in content:
            print(f"SECURITY EVENT: Malware detected in uploaded file '{file.filename}' via EICAR static signature")
            from core.audit import log_audit_event
            with SessionLocal() as db:
                log_audit_event(
                    db=db,
                    action="file.scan_failure",
                    actor_type="UNAUTHENTICATED",
                    resource_type="quarantine",
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    metadata={"filename": file.filename, "error": "Malware detected: EICAR test signature found.", "event": "malware_detected"}
                )
                db.commit()
            raise HTTPException(status_code=400, detail="Malware detected: EICAR test signature found.")

        try:
            validate_file_signature(content, file.filename or "")
        except ValueError as sig_err:
            print(f"SECURITY EVENT: Invalid file signature in uploaded file '{file.filename}': {sig_err}")
            from core.audit import log_audit_event
            with SessionLocal() as db:
                log_audit_event(
                    db=db,
                    action="file.signature_failure",
                    actor_type="UNAUTHENTICATED",
                    resource_type="quarantine",
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    metadata={"filename": file.filename, "error": str(sig_err), "event": "invalid_signature"}
                )
                db.commit()
            raise HTTPException(status_code=400, detail=str(sig_err))

        # 4. Save to quarantine staging directory
        quarantine_path = storage_service.save_quarantine(content, file.filename or "file.dat")

        # 5. Write record in quarantined_files database table
        from models.quarantine import QuarantinedFile
        with SessionLocal() as db:
            company_id = get_or_create_sandbox_company(db)
            q_rec = QuarantinedFile(
                company_id=company_id,
                filename=file.filename or "file.dat",
                quarantine_path=str(quarantine_path),
                is_safe=None  # Pending
            )
            db.add(q_rec)
            db.flush()
            q_file_id = q_rec.id
            db.commit()

        # 6. Trigger background Celery task
        from celery_worker import scan_and_promote_resume_task
        task = scan_and_promote_resume_task.delay(
            quarantine_file_id=str(q_file_id),
            job_role=job_role,
            job_description=job_description
        )

        return {
            "task_id": task.id,
            "quarantine_file_id": str(q_file_id),
            "status": "PENDING"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/api/recruit")
@limiter.limit("5/minute")
async def recruit(
    request: Request,
    file: UploadFile = File(...),
    job_role: str = Form(...),
    department: str = Form("Engineering"),
    start_date: str = Form(""),
    job_description: str = Form(""),
):
    """Full recruitment pipeline: parse PDF -> screen -> score -> decide -> communicate -> onboard if HIRE."""
    # 1. Early Content-Length check
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 5 MB.")

    try:
        pdf_bytes = await file.read()
        # 2. Strict read length check
        if len(pdf_bytes) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 5 MB.")

        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # 3. Quarantine Phase
        quarantine_path = storage_service.save_quarantine(pdf_bytes, file.filename or "file.dat")

        try:
            # 4. Malware Dynamic & Static Scan
            try:
                scan_file_for_malware(pdf_bytes)
            except ValueError as val_err:
                print(f"SECURITY EVENT: Malware detected in uploaded file '{file.filename}': {val_err}")
                from core.audit import log_audit_event
                from db.session import SessionLocal
                with SessionLocal() as db:
                    log_audit_event(
                        db=db,
                        action="file.scan_failure",
                        actor_type="UNAUTHENTICATED",
                        resource_type="quarantine",
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent"),
                        metadata={"filename": file.filename, "error": str(val_err), "event": "malware_detected"}
                    )
                raise HTTPException(status_code=400, detail=str(val_err))
            except RuntimeError as run_err:
                print(f"SECURITY EVENT: Malware scanner failure in production: {run_err}")
                raise HTTPException(status_code=500, detail="Security scanning service failure")

            # 5. File Signature Verification
            try:
                validate_file_signature(pdf_bytes, file.filename or "")
            except ValueError as sig_err:
                print(f"SECURITY EVENT: Invalid file signature in uploaded file '{file.filename}': {sig_err}")
                from core.audit import log_audit_event
                from db.session import SessionLocal
                with SessionLocal() as db:
                    log_audit_event(
                        db=db,
                        action="file.signature_failure",
                        actor_type="UNAUTHENTICATED",
                        resource_type="quarantine",
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent"),
                        metadata={"filename": file.filename, "error": str(sig_err), "event": "invalid_signature"}
                    )
                raise HTTPException(status_code=400, detail=str(sig_err))

            # 6. Promotion Phase
            tenant_id = tenant_id_var.get() or "unauthenticated"
            permanent_path = storage_service.promote_file(quarantine_path, tenant_id)
            
            from core.audit import log_audit_event
            from db.session import SessionLocal
            with SessionLocal() as db:
                log_audit_event(
                    db=db,
                    action="file.promoted",
                    actor_type="UNAUTHENTICATED",
                    company_id=tenant_id if tenant_id != "unauthenticated" else None,
                    resource_type="uploads",
                    resource_id=permanent_path.name,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    metadata={"filename": file.filename, "size": len(pdf_bytes)}
                )
                db.commit()

        except Exception:
            # Clean up quarantine if any step fails
            storage_service.delete_file(quarantine_path)
            raise

        evaluation_id = str(uuid.uuid4())
        
        # 1. Audit log evaluation started
        from core.audit import log_audit_event
        from db.session import SessionLocal
        with SessionLocal() as db:
            log_audit_event(
                db=db,
                action="ai.evaluation_started",
                actor_type="UNAUTHENTICATED",
                company_id=tenant_id if tenant_id != "unauthenticated" else None,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={
                    "evaluation_id": evaluation_id,
                    "job_role": job_role,
                    "department": department,
                    "filename": file.filename
                }
            )
            db.commit()

        result = process_candidate(
            pdf_bytes=pdf_bytes,
            job_description=job_description,
            role=job_role,
            department=department,
            start_date=start_date,
        )

        decision = result.get("decision_result", {}).get("decision", "REJECT")
        score = result.get("scoring_result", {}).get("total_score", 0)
        
        # 2. Audit log match score generated
        with SessionLocal() as db:
            log_audit_event(
                db=db,
                action="ai.match_score_generated",
                actor_type="UNAUTHENTICATED",
                company_id=tenant_id if tenant_id != "unauthenticated" else None,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={"evaluation_id": evaluation_id, "score": score}
            )
            db.commit()
            
        # 3. Audit log evaluation completed (compact storage constraint)
        with SessionLocal() as db:
            log_audit_event(
                db=db,
                action="ai.evaluation_completed",
                actor_type="UNAUTHENTICATED",
                company_id=tenant_id if tenant_id != "unauthenticated" else None,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={
                    "evaluation_id": evaluation_id,
                    "score": score,
                    "recommendation": decision,
                    "model_version": "gemini-1.5-pro",
                    "summary": f"Candidate processed for {job_role} in {department}. Fit: {result.get('scoring_result', {}).get('overall_fit', 'N/A')}"
                }
            )
            db.commit()

        response = {
            "success": True,
            "candidate": result.get("candidate_data", {}),
            "screening": result.get("screening_result", {}),
            "scoring": result.get("scoring_result", {}),
            "decision": result.get("decision_result", {}),
            "communication": result.get("communication_result", {}),
        }

        if decision == "HIRE":
            response["onboarding"] = {
                "documents_generated": result.get("documents_generated", []),
                "training_plan": result.get("training_plan", ""),
                "email_draft": result.get("email_draft", ""),
            }

        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e
