from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from api.deps import RequireCandidate, CandidateDb
from models import CandidateChatSession, CandidateAIChatHistory, Candidate, CandidateEmbedding, Offer, Application
from models.job import Job
from core.intelligence import GenerativeIntelligenceService
from core.limiter import limiter
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/candidate/ai", tags=["candidate-ai"])

class ChatRequestSchema(BaseModel):
    message: str
    session_id: uuid.UUID | None = None

class ResumeFeedbackRequestSchema(BaseModel):
    pass

class InterviewPrepRequestSchema(BaseModel):
    application_id: uuid.UUID

class OfferExplanationRequestSchema(BaseModel):
    offer_id: uuid.UUID

@router.post("/chat")
@limiter.limit("30/minute")
def ai_chat(
    request: Request,
    body: ChatRequestSchema,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    # Retrieve or create session
    session_id = body.session_id
    session = None
    if session_id:
        session = db.scalar(
            select(CandidateChatSession).where(
                CandidateChatSession.id == session_id,
                CandidateChatSession.candidate_id == current_candidate.id
            )
        )

    if not session:
        session = CandidateChatSession(
            candidate_id=current_candidate.id
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

    # Retrieve last 15 messages for this session
    messages = db.scalars(
        select(CandidateAIChatHistory)
        .where(CandidateAIChatHistory.session_id == session_id)
        .order_by(CandidateAIChatHistory.created_at.asc())
    ).all()

    # If count > 15, generate summary and update session
    if len(messages) > 15:
        history_context = [
            {"role": msg.role, "message": msg.message}
            for msg in messages[:-15]
        ]
        # Generate summary of old messages
        summary_prompt = f"Please summarize the following conversation history: {history_context}"
        try:
            # Simple summary generation using candidate_chat or just LLM
            session.summary = GenerativeIntelligenceService.candidate_chat(
                message=summary_prompt, history=[]
            )
        except Exception:
            session.summary = "Conversation continued."
        
        # Keep only the last 15 messages in memory context
        messages = messages[-15:]

    # Build history list for LLM
    history = []
    if session.summary:
        history.append({"role": "assistant", "message": f"[Summary of earlier conversation: {session.summary}]"})
    
    for msg in messages:
        history.append({"role": msg.role, "message": msg.message})

    # Call AI
    reply = GenerativeIntelligenceService.candidate_chat(body.message, history)

    # Save to history
    user_msg = CandidateAIChatHistory(
        session_id=session_id,
        role="user",
        message=body.message
    )
    assistant_msg = CandidateAIChatHistory(
        session_id=session_id,
        role="assistant",
        message=reply
    )
    db.add(user_msg)
    db.add(assistant_msg)
    
    session.last_activity_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()

    return {
        "reply": reply,
        "session_id": str(session_id),
        "summary": session.summary
    }

@router.post("/resume-feedback")
@limiter.limit("5/hour")
def get_resume_feedback(
    request: Request,
    body: ResumeFeedbackRequestSchema,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    # Find matching Candidates in the recruiter workspace
    candidates = db.scalars(
        select(Candidate).where(Candidate.email == current_candidate.email)
    ).all()
    c_ids = [c.id for c in candidates]

    resume_text = ""
    if c_ids:
        chunks = db.scalars(
            select(CandidateEmbedding)
            .where(CandidateEmbedding.candidate_id.in_(c_ids))
            .order_by(CandidateEmbedding.chunk_index)
        ).all()
        resume_text = "\n".join([chunk.chunk_text for chunk in chunks])

    if not resume_text:
        raise HTTPException(
            status_code=400,
            detail="No uploaded resume found for feedback. Please submit a resume to a job application first."
        )

    feedback = GenerativeIntelligenceService.resume_feedback(resume_text[:8000])
    return {"feedback": feedback}

@router.post("/interview-prep")
@limiter.limit("10/hour")
def get_interview_prep(
    request: Request,
    body: InterviewPrepRequestSchema,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    # Fetch recruiter Candidate record IDs matching this user's email
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    # Verify candidate owns application
    app = None
    if candidate_ids:
        app = db.scalar(
            select(Application).where(
                Application.id == body.application_id,
                Application.candidate_id.in_(candidate_ids)
            )
        )
    if not app:
        raise HTTPException(status_code=403, detail="Access denied: Application not owned by candidate")

    job = db.scalar(select(Job).where(Job.id == app.job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found")

    # Call AI
    prep_guide = GenerativeIntelligenceService.interview_preparation(
        role_title=job.title,
        job_description=job.description or "No job description available."
    )
    return {"guide": prep_guide}

@router.post("/offer-explanation")
@limiter.limit("10/hour")
def get_offer_explanation(
    request: Request,
    body: OfferExplanationRequestSchema,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    # Fetch recruiter Candidate record IDs matching this user's email
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    # Verify candidate owns offer
    offer = None
    if candidate_ids:
        offer = db.scalar(
            select(Offer).join(
                Application, Offer.application_id == Application.id
            ).where(
                Offer.id == body.offer_id,
                Application.candidate_id.in_(candidate_ids)
            )
        )
    if not offer:
        raise HTTPException(status_code=403, detail="Access denied: Offer not owned by candidate")

    explanation = GenerativeIntelligenceService.offer_explanation(
        salary=float(offer.salary),
        equity=offer.equity_grant,
        benefits="Standard company healthcare and retirement options"
    )
    return {"explanation": explanation}
