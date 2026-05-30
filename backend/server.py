from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Bridge GEMINI_API_KEY → GOOGLE_API_KEY so langchain-google-genai auto-detects it
_gemini_key = os.getenv("GEMINI_API_KEY")
if _gemini_key and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = _gemini_key

from pipeline import onboard_employee, process_candidate
from agents.screening_agent import screen_resume_text as _screen_text

app = FastAPI(title="SmartOnboard API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return {"status": "ok", "service": "SmartOnboard API", "version": "2.0.0"}


@app.post("/api/onboard")
async def onboard(request: OnboardRequest):
    try:
        result = onboard_employee(
            name=request.name,
            role=request.role,
            department=request.department,
            start_date=request.start_date,
            email=request.email
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
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/screen")
async def screen_text(request: ScreenRequest):
    try:
        result = _screen_text(
            resume_text=request.resume_text,
            job_role=request.job_role,
            job_description=request.job_description or ""
        )
        return {"success": True, "analysis": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/screen/upload")
async def screen_upload(
    file: UploadFile = File(...),
    job_role: str = Form(...),
    job_description: str = Form("")
):
    try:
        import io
        from pypdf import PdfReader
        content = await file.read()

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
            job_description=job_description
        )
        return {"success": True, "analysis": result, "filename": file.filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recruit")
async def recruit(
    file: UploadFile = File(...),
    job_role: str = Form(...),
    department: str = Form("Engineering"),
    start_date: str = Form(""),
    job_description: str = Form("")
):
    """Full recruitment pipeline: parse PDF -> screen -> score -> decide -> communicate -> onboard if HIRE."""
    try:
        pdf_bytes = await file.read()

        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        result = process_candidate(
            pdf_bytes=pdf_bytes,
            job_description=job_description,
            role=job_role,
            department=department,
            start_date=start_date
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
        raise HTTPException(status_code=500, detail=str(e))
