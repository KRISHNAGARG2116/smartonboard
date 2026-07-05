import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from langchain_groq import ChatGroq

from api.deps import TenantDb, RequireRecruiter
from models import Application, Job, Candidate, CandidateEmbedding, Scorecard, CandidateNote
from core.limiter import limiter
from core.anonymization import AnonymizationService
from core.audit import log_audit_event

router = APIRouter(prefix="/ai", tags=["ai_copilot"])


class AICopilotRequest(BaseModel):
    application_id: uuid.UUID


class AICopilotResponse(BaseModel):
    success: bool
    cached: bool
    generated_at: str
    content: str
    model: str
    provider: str


def _get_anonymized_candidate_context(db: TenantDb, current_user: RequireRecruiter, application_id: uuid.UUID):
    app = db.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.company_id == current_user.company_id
        )
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    job = db.get(Job, app.job_id)
    job_desc = job.description if job else "No job description available"
    job_title = job.title if job else "Unknown Position"

    candidate = db.get(Candidate, app.candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    alias = AnonymizationService.generate_candidate_alias(candidate.id)

    chunks = db.scalars(
        select(CandidateEmbedding)
        .where(CandidateEmbedding.candidate_id == app.candidate_id)
        .order_by(CandidateEmbedding.chunk_index)
    ).all()
    
    resume_text = "\n".join([c.chunk_text for c in chunks]) if chunks else "No resume content uploaded"
    anonymized_resume = AnonymizationService.anonymize_text(
        text=resume_text,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        candidate_alias=alias
    )

    notes = db.scalars(
        select(CandidateNote).where(CandidateNote.application_id == app.id)
    ).all()
    notes_text = "\n".join([f"- {n.content}" for n in notes]) if notes else "No notes available"
    anonymized_notes = AnonymizationService.anonymize_text(
        text=notes_text,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        candidate_alias=alias
    )

    scorecards = db.scalars(
        select(Scorecard).where(Scorecard.application_id == app.id, Scorecard.is_draft == False)
    ).all()
    scorecards_text = ""
    if scorecards:
        for idx, s in enumerate(scorecards):
            scorecards_text += f"\n[Scorecard {idx+1}]\nRecommendation: {s.overall_recommendation}\nNotes: {s.notes or 'None'}\nScores: {json.dumps(s.criteria_scores)}\n"
    else:
        scorecards_text = "No scorecards submitted yet"
    anonymized_scorecards = AnonymizationService.anonymize_text(
        text=scorecards_text,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        candidate_alias=alias
    )

    return {
        "app": app,
        "job_title": job_title,
        "job_desc": job_desc,
        "alias": alias,
        "resume": anonymized_resume,
        "notes": anonymized_notes,
        "scorecards": anonymized_scorecards
    }


@router.post("/interview-questions", response_model=AICopilotResponse)
@limiter.limit("10/minute")
def generate_interview_questions(
    request: Request,
    payload: AICopilotRequest,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Generates 5 customized interview questions and evaluator rubric guidelines
    tailored to the candidate's resume, previous interview scorecards, and recruiter notes.
    """
    ctx = _get_anonymized_candidate_context(db, current_user, payload.application_id)

    prompt = f"""You are an advanced recruitment coordinator and hiring copilot.
Generate 5 tailored, highly specific interview questions for the candidate based on:
1. Job description and title.
2. Candidate's resume details (experience, skills, projects).
3. Recruiter notes (observations, potential concerns, follow-ups).
4. Previous interview scorecard feedback.

Avoid generic questions. Instead, address gaps, strengths, or specific projects mentioned.
Also include a short reason why each question is asked.

Job Title: {ctx['job_title']}
Job Description:
{ctx['job_desc']}

Candidate Resume:
{ctx['resume'][:4000]}

Recruiter Notes:
{ctx['notes']}

Scorecard History:
{ctx['scorecards']}

Format the response in beautiful, readable markdown. Ensure there is a section called 'Tailored Questions' and 'Grader Guidelines' (evaluation criteria for the answers)."""

    llm = ChatGroq(model_name="llama-3.3-70b-versatile")
    result = llm.invoke(prompt)
    output = result.content.strip()

    log_audit_event(
        db=db,
        action="ai.interview_questions_generated",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="applications",
        resource_id=str(ctx['app'].id),
        metadata={
            "application_id": str(ctx['app'].id),
            "model_version": "llama-3.3-70b-versatile",
            "usage_type": "interview_questions"
        }
    )

    return AICopilotResponse(
        success=True,
        cached=False,
        generated_at=datetime.now(timezone.utc).isoformat(),
        content=output,
        model="llama-3.3-70b-versatile",
        provider="groq"
    )


@router.post("/candidate-summary", response_model=AICopilotResponse)
@limiter.limit("10/minute")
def generate_candidate_summary(
    request: Request,
    payload: AICopilotRequest,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Generates a concise professional summary of the candidate.
    """
    ctx = _get_anonymized_candidate_context(db, current_user, payload.application_id)

    prompt = f"""You are a professional recruiting assistant. Generate a high-level candidate summary based on the candidate's resume:
Candidate Alias: {ctx['alias']}

Candidate Resume:
{ctx['resume'][:4000]}

Please write a structured Candidate Summary covering:
- Professional Persona
- Core Areas of Expertise
- Notable Work History
- Educational Background & Certification Highlights

Mitigate bias: do not mention gender, race, age, graduation years, or institutional prestige."""

    llm = ChatGroq(model_name="llama-3.3-70b-versatile")
    result = llm.invoke(prompt)
    output = result.content.strip()

    log_audit_event(
        db=db,
        action="ai.summary_generated",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="applications",
        resource_id=str(ctx['app'].id),
        metadata={
            "application_id": str(ctx['app'].id),
            "model_version": "llama-3.3-70b-versatile",
            "usage_type": "candidate_summary"
        }
    )

    return AICopilotResponse(
        success=True,
        cached=False,
        generated_at=datetime.now(timezone.utc).isoformat(),
        content=output,
        model="llama-3.3-70b-versatile",
        provider="groq"
    )


@router.post("/resume-highlights", response_model=AICopilotResponse)
@limiter.limit("10/minute")
def generate_resume_highlights(
    request: Request,
    payload: AICopilotRequest,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Highlights the candidate's key achievements and notable accomplishments.
    """
    ctx = _get_anonymized_candidate_context(db, current_user, payload.application_id)

    prompt = f"""You are an advanced recruitment assistant. Analyze the candidate's resume and extract the top 3-5 key achievements and highlights.
Focus on quantifiable achievements, leadership examples, and notable projects.

Candidate Alias: {ctx['alias']}
Candidate Resume:
{ctx['resume'][:4000]}

Format as a bulleted list with clear explanations of why each item is a standout achievement."""

    llm = ChatGroq(model_name="llama-3.3-70b-versatile")
    result = llm.invoke(prompt)
    output = result.content.strip()

    log_audit_event(
        db=db,
        action="ai.highlights_generated",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="applications",
        resource_id=str(ctx['app'].id),
        metadata={
            "application_id": str(ctx['app'].id),
            "model_version": "llama-3.3-70b-versatile",
            "usage_type": "resume_highlights"
        }
    )

    return AICopilotResponse(
        success=True,
        cached=False,
        generated_at=datetime.now(timezone.utc).isoformat(),
        content=output,
        model="llama-3.3-70b-versatile",
        provider="groq"
    )


@router.post("/missing-skills", response_model=AICopilotResponse)
@limiter.limit("10/minute")
def generate_missing_skills(
    request: Request,
    payload: AICopilotRequest,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Identifies missing skills/competency gaps comparing candidate resume to the Job Description.
    """
    ctx = _get_anonymized_candidate_context(db, current_user, payload.application_id)

    prompt = f"""You are a technical recruiter. Compare the candidate's resume against the Job Description requirements.
Identify critical skill gaps, missing technologies, or lack of matching experience.

Job Title: {ctx['job_title']}
Job Description:
{ctx['job_desc']}

Candidate Resume:
{ctx['resume'][:4000]}

Format as a structured analysis listing:
1. Missing Required Skills
2. Missing Preferred Skills / Tools
3. Recommendations for what to probe during the interview to verify their familiarity with these topics."""

    llm = ChatGroq(model_name="llama-3.3-70b-versatile")
    result = llm.invoke(prompt)
    output = result.content.strip()

    log_audit_event(
        db=db,
        action="ai.missing_skills_generated",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="applications",
        resource_id=str(ctx['app'].id),
        metadata={
            "application_id": str(ctx['app'].id),
            "model_version": "llama-3.3-70b-versatile",
            "usage_type": "missing_skills"
        }
    )

    return AICopilotResponse(
        success=True,
        cached=False,
        generated_at=datetime.now(timezone.utc).isoformat(),
        content=output,
        model="llama-3.3-70b-versatile",
        provider="groq"
    )


@router.post("/risk-factors", response_model=AICopilotResponse)
@limiter.limit("10/minute")
def generate_risk_factors(
    request: Request,
    payload: AICopilotRequest,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Highlights potential candidate risk factors like employment gaps, short tenures, or qualifications discrepancy.
    """
    ctx = _get_anonymized_candidate_context(db, current_user, payload.application_id)

    prompt = f"""You are a senior hiring manager. Analyze the candidate's resume for any structural risks or concerns.
Specifically check for:
- Unexplained career gaps
- Job hopping / short tenures
- Discrepancy between job requirements and resume qualifications
- Domain or industry experience mismatches

Candidate Alias: {ctx['alias']}
Job Description:
{ctx['job_desc']}

Candidate Resume:
{ctx['resume'][:4000]}

Provide an objective assessment listing risks and how to discuss them constructively during interviews. Mitigate age/prestige bias."""

    llm = ChatGroq(model_name="llama-3.3-70b-versatile")
    result = llm.invoke(prompt)
    output = result.content.strip()

    log_audit_event(
        db=db,
        action="ai.risk_factors_generated",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="applications",
        resource_id=str(ctx['app'].id),
        metadata={
            "application_id": str(ctx['app'].id),
            "model_version": "llama-3.3-70b-versatile",
            "usage_type": "risk_factors"
        }
    )

    return AICopilotResponse(
        success=True,
        cached=False,
        generated_at=datetime.now(timezone.utc).isoformat(),
        content=output,
        model="llama-3.3-70b-versatile",
        provider="groq"
    )


@router.post("/interview-preparation", response_model=AICopilotResponse)
@limiter.limit("10/minute")
def generate_interview_prep(
    request: Request,
    payload: AICopilotRequest,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Generates a comprehensive interview preparation guide for the interviewer.
    """
    ctx = _get_anonymized_candidate_context(db, current_user, payload.application_id)

    prompt = f"""You are the head of talent development. Create a comprehensive interview preparation guide for the interviewer.
Include:
- Focus competencies for this job role
- Tailored question recommendations based on resume analysis
- Specific grading rubric guidelines
- Red flags and watchouts to note

Job Title: {ctx['job_title']}
Job Description:
{ctx['job_desc']}

Candidate Resume:
{ctx['resume'][:4000]}

Candidate Alias: {ctx['alias']}
Format as a beautiful prep guide in markdown."""

    llm = ChatGroq(model_name="llama-3.3-70b-versatile")
    result = llm.invoke(prompt)
    output = result.content.strip()

    log_audit_event(
        db=db,
        action="ai.interview_prep_generated",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="applications",
        resource_id=str(ctx['app'].id),
        metadata={
            "application_id": str(ctx['app'].id),
            "model_version": "llama-3.3-70b-versatile",
            "usage_type": "interview_prep"
        }
    )

    return AICopilotResponse(
        success=True,
        cached=False,
        generated_at=datetime.now(timezone.utc).isoformat(),
        content=output,
        model="llama-3.3-70b-versatile",
        provider="groq"
    )
