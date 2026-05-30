from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Allow `from pipeline import …` when started as `uvicorn backend.server:app` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

if not os.getenv("GROQ_API_KEY"):
    print(
        "WARNING: GROQ_API_KEY is not set. "
        "AI pipeline requests will fail until you add it to a .env file in the project root."
    )

from api.router import v1_router
from db.session import SessionLocal, engine
from pipeline import onboard_employee, process_candidate
from agents.screening_agent import screen_resume_text as _screen_text

from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from core.limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection OK")
    except Exception as exc:
        print(f"WARNING: Database unavailable: {exc}")
    yield


app = FastAPI(title="SmartOnboard API", version="2.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.post("/api/screen/upload")
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
        import io
        from pypdf import PdfReader

        content = await file.read()
        # 2. Strict read length check
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 5 MB.")

        if file.filename and file.filename.lower().endswith(".pdf"):
            reader = PdfReader(io.BytesIO(content))
            resume_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            resume_text = content.decode("utf-8", errors="ignore")

        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from file")

        result = _screen_text(
            resume_text=resume_text,
            job_role=job_role,
            job_description=job_description,
        )
        return {"success": True, "analysis": result, "filename": file.filename}
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

        result = process_candidate(
            pdf_bytes=pdf_bytes,
            job_description=job_description,
            role=job_role,
            department=department,
            start_date=start_date,
        )

        decision = result.get("decision_result", {}).get("decision", "REJECT")

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
