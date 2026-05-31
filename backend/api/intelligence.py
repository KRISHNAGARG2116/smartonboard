import uuid
import json
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Query, status, Body
from fastapi.responses import JSONResponse
from sqlalchemy import select

from api.deps import RequireRecruiter, TenantDb
from models import Application, Candidate, CandidateEmbedding, Scorecard
from models.recruiter_insight import AIRecruiterInsight
from celery_worker import generate_recruiter_insight_async

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

STANDARD_TYPES = {"candidate_summary", "scorecard_consensus", "hiring_recommendation"}


def compute_insight_checksum(db, application_id: uuid.UUID, insight_type: str) -> str:
    """
    Computes a deterministic SHA256 checksum of the underlying raw source data
    to automatically invalidate cached insights if data changes.
    """
    # 1. Fetch Application context
    app = db.scalar(select(Application).where(Application.id == application_id))
    if not app:
        return ""

    text_str = ""
    raw_sc_str = ""

    # 2. Candidate embeddings hash
    if insight_type in {"candidate_summary", "hiring_recommendation"}:
        embeddings = db.scalars(
            select(CandidateEmbedding)
            .where(CandidateEmbedding.candidate_id == app.candidate_id)
            .order_by(CandidateEmbedding.chunk_index.asc())
        ).all()
        text_str = "".join([emb.chunk_text for emb in embeddings])

    # 3. Scorecard metadata hash
    if insight_type in {"scorecard_consensus", "hiring_recommendation"}:
        scorecards = db.scalars(
            select(Scorecard)
            .where(Scorecard.application_id == application_id)
            .order_by(Scorecard.submitted_at.asc())
        ).all()
        raw_sc_str = "".join([
            f"{sc.id}-{sc.grader_id}-{sc.overall_recommendation}-{json.dumps(sc.criteria_scores)}"
            for sc in scorecards
        ])

    # 4. Return combined SHA256
    combo = text_str + raw_sc_str
    if not combo:
        return "empty_source_invalidation"
    return hashlib.sha256(combo.encode("utf-8")).hexdigest()


@router.get("/applications/{id}/candidate-summary")
def get_candidate_summary(id: uuid.UUID, db: TenantDb, current_user: RequireRecruiter):
    """
    Returns candidate summary if completed, 202 if pending/processing, or 500 if failed.
    Automatically enqueues generation on cache miss or TTL expiration.
    """
    return process_insight_request(id, "candidate_summary", db, current_user)


@router.get("/applications/{id}/scorecard-consensus")
def get_scorecard_consensus(id: uuid.UUID, db: TenantDb, current_user: RequireRecruiter):
    """
    Returns scorecard consensus if completed, 202 if pending/processing, or 500 if failed.
    """
    return process_insight_request(id, "scorecard_consensus", db, current_user)


@router.get("/applications/{id}/hiring-recommendation")
def get_hiring_recommendation(id: uuid.UUID, db: TenantDb, current_user: RequireRecruiter):
    """
    Returns final hiring recommendation if completed, 202 if pending/processing, or 500 if failed.
    """
    return process_insight_request(id, "hiring_recommendation", db, current_user)


@router.post("/applications/{id}/regenerate")
def regenerate_insight(
    id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter,
    body: dict = Body(..., example={"insight_type": "candidate_summary"})
):
    """
    Explicitly invalidates cache (by setting to PENDING/expired without deleting)
    and enqueues the Celery worker task, returning a processing state.
    """
    insight_type = body.get("insight_type")
    if insight_type not in STANDARD_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid insight_type. Must be one of: {list(STANDARD_TYPES)}"
        )

    # 1. Enforce strict Python company boundary
    app = db.scalar(
        select(Application).where(
            Application.id == id,
            Application.company_id == current_user.company_id
        )
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # 2. Compute current invalidation checksum
    computed_checksum = compute_insight_checksum(db, id, insight_type)

    # 3. Soft-invalidate insight record
    epoch = datetime.fromtimestamp(0, tz=timezone.utc)
    stmt = select(AIRecruiterInsight).where(
        AIRecruiterInsight.application_id == id,
        AIRecruiterInsight.insight_type == insight_type
    )
    insight = db.scalar(stmt)
    if not insight:
        insight = AIRecruiterInsight(
            company_id=current_user.company_id,
            application_id=id,
            insight_type=insight_type,
            checksum=computed_checksum,
            expires_at=epoch,
            model_version="llama-3.3-70b-versatile"
        )
        db.add(insight)
        db.flush()

    insight.generation_status = "PENDING"
    insight.content = None
    insight.last_error = None
    insight.checksum = computed_checksum
    insight.generated_at = None
    insight.expires_at = epoch
    db.commit()

    # 4. Dispatch async worker task
    task = generate_recruiter_insight_async.delay(
        str(current_user.company_id),
        str(id),
        insight_type,
        computed_checksum
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "PENDING",
            "message": "Recruiter intelligence summary has been queued for regeneration asynchronously. Please poll status.",
            "task_id": task.id
        }
    )


def process_insight_request(
    id: uuid.UUID,
    insight_type: str,
    db: TenantDb,
    current_user: RequireRecruiter
):
    """
    Common handler checking database cache availability, enqueuing Celery tasks on miss or expiration,
    and outputting structured status responses.
    """
    # 1. Enforce strict Python company boundary
    app = db.scalar(
        select(Application).where(
            Application.id == id,
            Application.company_id == current_user.company_id
        )
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # 2. Compute current invalidation checksum
    computed_checksum = compute_insight_checksum(db, id, insight_type)

    # 3. Query existing insight
    stmt = select(AIRecruiterInsight).where(
        AIRecruiterInsight.application_id == id,
        AIRecruiterInsight.insight_type == insight_type
    )
    insight = db.scalar(stmt)

    now = datetime.now(timezone.utc)
    cache_miss = False

    if not insight:
        cache_miss = True
    elif insight.expires_at < now:
        cache_miss = True
    elif insight.checksum != computed_checksum:
        cache_miss = True
    elif insight.generation_status == "PENDING":
        cache_miss = True

    # 4. Trigger background task on cache miss
    if cache_miss:
        epoch = datetime.fromtimestamp(0, tz=timezone.utc)
        if not insight:
            insight = AIRecruiterInsight(
                company_id=current_user.company_id,
                application_id=id,
                insight_type=insight_type,
                checksum=computed_checksum,
                expires_at=epoch,
                model_version="llama-3.3-70b-versatile"
            )
            db.add(insight)
            db.flush()

        insight.generation_status = "PENDING"
        insight.content = None
        insight.last_error = None
        insight.checksum = computed_checksum
        insight.generated_at = None
        insight.expires_at = epoch
        db.commit()

        task = generate_recruiter_insight_async.delay(
            str(current_user.company_id),
            str(id),
            insight_type,
            computed_checksum
        )

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "PENDING",
                "message": "Recruiter intelligence summary is currently generating asynchronously. Please poll status.",
                "task_id": task.id
            }
        )

    # 5. Return processing state
    if insight.generation_status == "PROCESSING":
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "PROCESSING",
                "message": "Recruiter intelligence summary is currently generating asynchronously. Please poll status."
            }
        )

    # 6. Return failure state
    if insight.generation_status == "FAILED":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "FAILED",
                "last_error": insight.last_error,
                "message": "Asynchronous recruiter intelligence task failed. You can re-trigger regeneration by resubmitting the request."
            }
        )

    # 7. Return completed cache hit
    # Auto-log a VIEWED interaction
    try:
        from models.insight_interaction import AIInsightInteraction
        interaction = AIInsightInteraction(
            company_id=current_user.company_id,
            user_id=current_user.id,
            application_id=id,
            insight_type=insight_type,
            interaction_type="VIEWED",
            recommendation_snapshot=None
        )
        db.add(interaction)
        db.commit()
    except Exception:
        db.rollback()

    return {
        "status": "COMPLETED",
        "application_id": str(insight.application_id),
        "insight_type": insight.insight_type,
        "confidence_score": insight.confidence_score,
        "confidence_reason": insight.confidence_reason,
        "expires_at": insight.expires_at.isoformat(),
        "generated_at": insight.generated_at.isoformat() if insight.generated_at else None,
        "candidate_embedding_ids": insight.candidate_embedding_ids,
        "scorecard_ids": insight.scorecard_ids,
        "content": insight.content
    }


from pydantic import BaseModel

class DecisionOutcomeBody(BaseModel):
    insight_type: str
    decision: str # 'ACCEPTED', 'DISMISSED', 'OVERRIDDEN'
    recruiter_decision: str | None = None # 'HIRE', 'NO_HIRE'


@router.post("/applications/{id}/decide-outcome")
def decide_outcome(
    id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter,
    body: DecisionOutcomeBody
):
    """
    Submits a recruiter outcome decision (ACCEPTED, DISMISSED, OVERRIDDEN)
    for a completed AI insight, snapshotting the model recommendation.
    """
    if body.decision not in {"ACCEPTED", "DISMISSED", "OVERRIDDEN"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid decision. Must be one of: ACCEPTED, DISMISSED, OVERRIDDEN"
        )

    # 1. Enforce strict Python company boundary
    app = db.scalar(
        select(Application).where(
            Application.id == id,
            Application.company_id == current_user.company_id
        )
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # 2. Query completed insight
    insight = db.scalar(
        select(AIRecruiterInsight).where(
            AIRecruiterInsight.application_id == id,
            AIRecruiterInsight.insight_type == body.insight_type,
            AIRecruiterInsight.generation_status == "COMPLETED"
        )
    )
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No completed insight of type '{body.insight_type}' found for this application."
        )

    # 3. Determine recommendation snapshot
    snapshot = "NO_HIRE"
    if body.insight_type == "hiring_recommendation":
        content_upper = (insight.content or "").upper()
        if "HIRE" in content_upper and "NO-HIRE" not in content_upper and "NO HIRE" not in content_upper:
            snapshot = "HIRE"
        elif "NO-HIRE" in content_upper or "NO HIRE" in content_upper:
            snapshot = "NO_HIRE"
        elif "HIRE" in content_upper:
            # Fallback if both present or complex structure
            snapshot = "HIRE"

    # 4. Record interaction outcome
    from models.insight_interaction import AIInsightInteraction
    interaction = AIInsightInteraction(
        company_id=current_user.company_id,
        user_id=current_user.id,
        application_id=id,
        insight_type=body.insight_type,
        interaction_type=body.decision,
        recommendation_snapshot=snapshot,
        recruiter_decision=body.recruiter_decision or (snapshot if body.decision != "OVERRIDDEN" else ("NO_HIRE" if snapshot == "HIRE" else "HIRE"))
    )
    db.add(interaction)
    db.commit()

    # 5. Log audit events
    from core.audit import log_audit_event
    if body.decision == "DISMISSED":
        log_audit_event(
            db=db,
            action="ai.insight_dismissed",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            metadata={
                "application_id": str(id),
                "insight_type": body.insight_type,
                "prompt_version": insight.prompt_version,
                "dismissed_reason": "Manual review mismatch"
            }
        )
    else:
        # ACCEPTED or OVERRIDDEN both indicate adoption review completed
        log_audit_event(
            db=db,
            action="ai.insight_adopted",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            metadata={
                "application_id": str(id),
                "insight_type": body.insight_type,
                "prompt_version": insight.prompt_version,
                "decision_type": body.decision
            }
        )

    return {
        "success": True,
        "message": f"Outcome decision '{body.decision}' successfully recorded for insight '{body.insight_type}'."
    }
