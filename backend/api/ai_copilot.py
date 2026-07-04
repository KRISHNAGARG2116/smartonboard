import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from api.deps import TenantDb, RequireRecruiter
from models import Application, Job, Candidate, CandidateEmbedding, Scorecard, CandidateNote

router = APIRouter(prefix="/ai", tags=["ai_copilot"])


class InterviewQuestionsRequest(BaseModel):
    application_id: uuid.UUID


@router.post("/interview-questions")
def generate_interview_questions(
    payload: InterviewQuestionsRequest,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Generates 5 customized interview questions and evaluator rubric guidelines
    tailored to the candidate's resume, previous interview scorecards, and recruiter notes.
    """
    app = db.scalar(
        select(Application).where(
            Application.id == payload.application_id,
            Application.company_id == current_user.company_id
        )
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    job = db.get(Job, app.job_id)
    job_desc = job.description if job else "No job description available"
    job_title = job.title if job else "Unknown Position"

    chunks = db.scalars(
        select(CandidateEmbedding).where(CandidateEmbedding.candidate_id == app.candidate_id).order_by(CandidateEmbedding.chunk_index)
    ).all()
    resume_text = "\n".join([c.chunk_text for c in chunks]) if chunks else "No resume content uploaded"

    notes = db.scalars(
        select(CandidateNote).where(CandidateNote.application_id == app.id)
    ).all()
    notes_text = "\n".join([f"- {n.content}" for n in notes]) if notes else "No notes available"

    scorecards = db.scalars(
        select(Scorecard).where(Scorecard.application_id == app.id, Scorecard.is_draft == False)
    ).all()
    scorecards_text = ""
    if scorecards:
        for idx, s in enumerate(scorecards):
            scorecards_text += f"\n[Scorecard {idx+1}]\nRecommendation: {s.overall_recommendation}\nNotes: {s.notes or 'None'}\nScores: {json.dumps(s.criteria_scores)}\n"
    else:
        scorecards_text = "No scorecards submitted yet"

    prompt = f"""You are an advanced recruitment coordinator and hiring copilot.
Generate 5 tailored, highly specific interview questions for the candidate based on:
1. Job description and title.
2. Candidate's resume details (experience, skills, projects).
3. Recruiter notes (observations, potential concerns, follow-ups).
4. Previous interview scorecard feedback.

Avoid generic questions. Instead, address gaps, strengths, or specific projects mentioned.
Also include a short reason why each question is asked.

Job Title: {job_title}
Job Description:
{job_desc}

Candidate Resume:
{resume_text[:4000]}

Recruiter Notes:
{notes_text}

Scorecard History:
{scorecards_text}

Format the response in beautiful, readable markdown. Ensure there is a section called 'Tailored Questions' and 'Grader Guidelines' (evaluation criteria for the answers)."""

    from langchain_groq import ChatGroq
    from core.audit import log_audit_event

    llm = ChatGroq(model_name="llama-3.3-70b-versatile")
    result = llm.invoke(prompt)
    output = result.content.strip()

    # Track AI Usage Analytics per recruiter
    log_audit_event(
        db=db,
        action="ai.interview_questions_generated",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="applications",
        resource_id=str(app.id),
        metadata={
            "application_id": str(app.id),
            "model_version": "llama-3.3-70b-versatile",
            "usage_type": "interview_questions"
        }
    )

    return {"questions_guide": output}
