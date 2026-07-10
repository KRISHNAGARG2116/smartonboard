import uuid
import json
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func

from api.deps import TenantDb, RequireRecruiter
from models.ai_recruiter_models import RecruiterChatSession, RecruiterChatMessage, AICopilotCallLog, AgentPlannerTemplate
from core.ai_recruiter import AgentPlanningService
from core.ai_comparison import CandidateComparisonService
from core.ai_drafting import AIDraftingService
from core.ai_tool_framework import ToolRegistry

router = APIRouter(prefix="/ai-recruiter", tags=["ai_recruiter"])


# --- Schemas ---

class CreateSessionRequest(BaseModel):
    session_name: str


class SessionResponse(BaseModel):
    id: uuid.UUID
    session_name: str
    current_job_id: uuid.UUID | None
    current_pool_id: uuid.UUID | None
    current_filters: dict
    selected_candidate_ids: list
    context_version: int
    created_at: datetime


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    message: str
    execution_graph: dict | None
    plan_confidence: float | None
    plan_confidence_reason: str | None
    plan_approved: bool
    tool_calls: list
    created_at: datetime


class PlanRequest(BaseModel):
    session_id: uuid.UUID
    message: str


class ExecuteRequest(BaseModel):
    message_id: uuid.UUID


class CompareRequest(BaseModel):
    candidate_ids: list[uuid.UUID]
    job_id: uuid.UUID | None = None


class DraftRequest(BaseModel):
    template_type: str
    candidate_name: str
    job_title: str
    recruiter_name: str


class FeedbackRequest(BaseModel):
    feedback: str  # helpful, incorrect, incomplete, hallucinated, too_slow, permission_error


# --- Endpoints ---

@router.post("/sessions", response_model=SessionResponse)
def create_session(
    payload: CreateSessionRequest,
    db: TenantDb,
    current_user: RequireRecruiter
):
    session = RecruiterChatSession(
        company_id=current_user.company_id,
        recruiter_id=current_user.id,
        session_name=payload.session_name
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=list[SessionResponse])
def get_sessions(
    db: TenantDb,
    current_user: RequireRecruiter
):
    sessions = db.scalars(
        select(RecruiterChatSession).where(
            RecruiterChatSession.recruiter_id == current_user.id,
            RecruiterChatSession.company_id == current_user.company_id
        ).order_by(RecruiterChatSession.created_at.desc())
    ).all()
    return list(sessions)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter
):
    session = db.scalar(
        select(RecruiterChatSession).where(
            RecruiterChatSession.id == session_id,
            RecruiterChatSession.company_id == current_user.company_id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    db.delete(session)
    db.commit()
    return


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
def get_messages(
    session_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter
):
    session = db.scalar(
        select(RecruiterChatSession).where(
            RecruiterChatSession.id == session_id,
            RecruiterChatSession.company_id == current_user.company_id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    messages = db.scalars(
        select(RecruiterChatMessage).where(
            RecruiterChatMessage.session_id == session_id
        ).order_by(RecruiterChatMessage.created_at.asc())
    ).all()
    return list(messages)


@router.post("/chat/plan", response_model=MessageResponse)
def prepare_chat_plan(
    payload: PlanRequest,
    db: TenantDb,
    current_user: RequireRecruiter
):
    session = db.scalar(
        select(RecruiterChatSession).where(
            RecruiterChatSession.id == payload.session_id,
            RecruiterChatSession.company_id == current_user.company_id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Check expiration and update last_active
    AgentPlanningService.check_session_expiration(session)
    session.last_active = datetime.now(timezone.utc)
    db.commit()

    # Generate plan
    plan_data = AgentPlanningService.generate_plan(payload.message, session)
    if "error" in plan_data:
        raise HTTPException(status_code=400, detail=plan_data["error"])

    # Create message entry representing user prompt
    user_msg = RecruiterChatMessage(
        session_id=session.id,
        role="user",
        message=payload.message
    )
    db.add(user_msg)
    db.commit()

    # Check clarifying question criteria
    message_content = ""
    graph = None
    if "clarifying_question" in plan_data:
        message_content = plan_data["clarifying_question"]
    else:
        graph = plan_data["execution_graph"]
        message_content = f"Plan generated successfully. Confirm to execute."

    # Create assistant message with planning details
    assistant_msg = RecruiterChatMessage(
        session_id=session.id,
        role="assistant",
        message=message_content,
        execution_graph=graph,
        plan_confidence=plan_data["plan_confidence"],
        plan_confidence_reason=plan_data["plan_confidence_reason"]
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return assistant_msg


@router.post("/chat/execute")
async def execute_chat_plan(
    payload: ExecuteRequest,
    db: TenantDb,
    current_user: RequireRecruiter
):
    msg = db.get(RecruiterChatMessage, payload.message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found.")

    session = db.get(RecruiterChatSession, msg.session_id)
    if not session or session.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Forbidden context.")

    graph = msg.execution_graph
    if not graph:
        raise HTTPException(status_code=400, detail="No execution plan available for this message.")

    # Validation Phase
    # Fetch active recruiter roles & permissions (simulate active permission scope)
    user_permissions = ["VIEW_CANDIDATES", "VIEW_JOBS", "VIEW_TALENT_CRM", "MANAGE_TALENT_POOLS"]
    is_valid, validation_msg = AgentPlanningService.validate_plan(graph, user_permissions)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Planner Validation Failed: {validation_msg}")

    # Stream SSE timeline execution updates
    async def sse_event_generator():
        try:
            # Emit starting pipeline
            yield f"data: {json.dumps({'event': 'start', 'message_id': str(msg.id)})}\n\n"
            await asyncio.sleep(0.1)

            def progress_callback(node_id, status_val, results_data):
                # We can stream intermediate node milestones
                pass

            # Execute graph
            result = await AgentPlanningService.execute_plan(
                session_id=session.id,
                message_id=msg.id,
                user_permissions=user_permissions,
                db=db,
                on_progress=progress_callback
            )

            # Create final response text entry
            reply_msg = RecruiterChatMessage(
                session_id=session.id,
                role="assistant",
                message=result["summary"],
                plan_approved=True
            )
            db.add(reply_msg)
            db.commit()

            yield f"data: {json.dumps({'event': 'done', 'summary': result['summary'], 'suggestions': result['suggestions']})}\n\n"
        except asyncio.CancelledError:
            # Planner Cancellation: terminate gracefully
            yield f"data: {json.dumps({'event': 'cancelled', 'detail': 'Recruiter canceled plan execution.'})}\n\n"
        except Exception as err:
            yield f"data: {json.dumps({'event': 'error', 'detail': str(err)})}\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")


@router.post("/compare")
def compare_candidates(
    payload: CompareRequest,
    db: TenantDb,
    current_user: RequireRecruiter
):
    result = CandidateComparisonService.compare_candidates(
        candidate_ids=payload.candidate_ids,
        job_id=payload.job_id,
        db=db
    )
    return result


@router.post("/draft")
def generate_draft(
    payload: DraftRequest,
    current_user: RequireRecruiter
):
    result = AIDraftingService.generate_outreach_draft(
        template_type=payload.template_type,
        candidate_name=payload.candidate_name,
        job_title=payload.job_title,
        recruiter_name=payload.recruiter_name
    )
    return result


@router.post("/feedback/{log_id}")
def record_feedback(
    log_id: uuid.UUID,
    payload: FeedbackRequest,
    db: TenantDb,
    current_user: RequireRecruiter
):
    log = db.get(AICopilotCallLog, log_id)
    if not log or log.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Log entry not found.")

    log.user_feedback = payload.feedback
    db.commit()
    return {"status": "success", "message": "Feedback recorded."}


@router.get("/observability/stats")
def get_observability_stats(
    db: TenantDb,
    current_user: RequireRecruiter
):
    # Retrieve aggregated stats
    totals = db.execute(
        select(
            func.count(AICopilotCallLog.id).label("total_calls"),
            func.avg(AICopilotCallLog.execution_time_ms).label("avg_execution_time"),
            func.avg(AICopilotCallLog.planning_time_ms).label("avg_planning_time"),
            func.avg(AICopilotCallLog.plan_complexity).label("avg_complexity")
        ).where(AICopilotCallLog.company_id == current_user.company_id)
    ).first()

    feedback_counts = db.execute(
        select(
            AICopilotCallLog.user_feedback,
            func.count(AICopilotCallLog.id)
        ).where(AICopilotCallLog.company_id == current_user.company_id)
        .group_by(AICopilotCallLog.user_feedback)
    ).all()

    feedback_map = {r[0]: r[1] for r in feedback_counts if r[0] is not None}

    return {
        "total_calls": totals.total_calls or 0,
        "avg_execution_time_ms": round(float(totals.avg_execution_time or 0), 1),
        "avg_planning_time_ms": round(float(totals.avg_planning_time or 0), 1),
        "avg_plan_complexity": round(float(totals.avg_complexity or 0), 1),
        "granular_feedback": feedback_map
    }


@router.post("/replay/{message_id}")
def replay_plan_execution(
    message_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter
):
    """Replays an execution graph for debugging purposes."""
    msg = db.get(RecruiterChatMessage, message_id)
    if not msg or not msg.execution_graph:
        raise HTTPException(status_code=404, detail="Message execution graph not found.")

    # Verify context
    session = db.get(RecruiterChatSession, msg.session_id)
    if not session or session.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Forbidden.")

    # Replay graph returns execution logs
    return {
        "status": "success",
        "replay_graph": msg.execution_graph,
        "historical_tool_calls": msg.tool_calls,
        "locked_context": msg.execution_context_snapshot
    }
