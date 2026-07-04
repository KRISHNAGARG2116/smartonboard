import uuid
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models.application import Application
from models.pipeline import StageDefinition
from models.sla import StageSLA, CandidateStageSLATracker
from models.enums import ApplicationStatus
from core.audit import log_audit_event

logger = logging.getLogger(__name__)

MAP_BASE_CATEGORY_TO_STATUS = {
    "applied": ApplicationStatus.SUBMITTED,
    "screening": ApplicationStatus.SCREENING,
    "interviewing": ApplicationStatus.INTERVIEW,
    "offered": ApplicationStatus.OFFER,
    "hired": ApplicationStatus.HIRED,
    "rejected": ApplicationStatus.REJECTED,
}

def get_field_by_path(data: dict, path: str):
    """
    Safely navigates a dictionary via dot notation e.g., 'scorecard.overall_recommendation'
    """
    parts = path.split('.')
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
    return current

def evaluate_structured_rule(rule: dict, evaluation_results: dict) -> bool:
    """
    Evaluates a single structured rule against the unified evaluation results dictionary.
    """
    actual_value = get_field_by_path(evaluation_results, rule["field"])
    if actual_value is None:
        return False
    
    op = rule["operator"]
    expected = rule["value"]
    
    # Try to convert values to identical types for numeric comparisons
    if op in (">", ">=", "<", "<="):
        try:
            actual_value = float(actual_value)
            expected = float(expected)
        except (ValueError, TypeError):
            return False
            
    if op == "==":
        return str(actual_value) == str(expected)
    if op == ">":
        return actual_value > expected
    if op == ">=":
        return actual_value >= expected
    if op == "<":
        return actual_value < expected
    if op == "<=":
        return actual_value <= expected
    if op == "!=":
        return str(actual_value) != str(expected)
    if op == "contains":
        return str(expected) in str(actual_value)
        
    return False

def transition_candidate_stage(
    db: Session,
    company_id: uuid.UUID,
    application_id: uuid.UUID,
    target_stage_id: uuid.UUID,
    actor_id: uuid.UUID | None = None,
    is_auto: bool = False
) -> Application:
    """
    Transitions a candidate's application to a new stage definition.
    - Updates application.current_stage_id and syncs application.status.
    - Marks active in-stage SLA trackers as 'completed'.
    - Instantiates a new SLA tracker for the target stage if defined.
    - Logs audit events.
    """
    # 1. Fetch Application
    application = db.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.company_id == company_id
        )
    )
    if not application:
        raise ValueError("Application not found")
        
    from_stage_id = application.current_stage_id
    if from_stage_id:
        current_stage = db.get(StageDefinition, from_stage_id)
        if current_stage:
            validate_stage_exit_requirements(db, application, current_stage)
    
    # 2. Fetch Target Stage
    target_stage = db.scalar(
        select(StageDefinition).where(
            StageDefinition.id == target_stage_id,
            StageDefinition.company_id == company_id
        )
    )
    if not target_stage:
        raise ValueError("Target stage definition not found")
        
    # 3. Complete existing SLA trackers
    db.execute(
        update(CandidateStageSLATracker)
        .where(
            CandidateStageSLATracker.application_id == application_id,
            CandidateStageSLATracker.status.in_(["active", "breached"])
        )
        .values(status="completed")
    )
    
    # 4. Perform Transition
    application.current_stage_id = target_stage_id
    # Sync status with target stage's base category
    new_status = MAP_BASE_CATEGORY_TO_STATUS.get(target_stage.base_category, ApplicationStatus.SCREENING)
    application.status = new_status
    db.flush()
    
    # 5. Instantiate new SLA tracker if configured
    sla = db.scalar(
        select(StageSLA).where(
            StageSLA.stage_definition_id == target_stage_id,
            StageSLA.company_id == company_id
        )
    )
    if sla:
        now = datetime.now(timezone.utc)
        tracker = CandidateStageSLATracker(
            company_id=company_id,
            application_id=application_id,
            stage_definition_id=target_stage_id,
            entered_at=now,
            expires_at=now + timedelta(seconds=sla.duration_seconds),
            status="active",
            escalation_count=0
        )
        db.add(tracker)
        db.flush()

    # 6. Apply SLA pausing checks
    check_and_update_sla_timers(db, application_id)
        
    # 7. Log Audit Events
    log_audit_event(
        db=db,
        action="pipeline.stage_transitioned",
        actor_type="system" if is_auto else "user",
        company_id=company_id,
        actor_id=actor_id,
        resource_type="application",
        resource_id=str(application_id),
        metadata={
            "from_stage_id": str(from_stage_id) if from_stage_id else None,
            "to_stage_id": str(target_stage_id),
            "is_auto": is_auto
        }
    )
    
    if is_auto:
        log_audit_event(
            db=db,
            action="pipeline.auto_progressed",
            actor_type="system",
            company_id=company_id,
            resource_type="application",
            resource_id=str(application_id),
            metadata={
                "from_stage_id": str(from_stage_id) if from_stage_id else None,
                "to_stage_id": str(target_stage_id),
            }
        )
        
    db.commit()
    db.refresh(application)
    return application


def check_and_update_sla_timers(db: Session, application_id: uuid.UUID):
    """
    Looks up the active SLA tracker for the application, and decides whether
    to pause or resume it based on the application's current state.
    """
    tracker = db.scalar(
        select(CandidateStageSLATracker).where(
            CandidateStageSLATracker.application_id == application_id,
            CandidateStageSLATracker.status.in_(["active", "paused"])
        )
    )
    if not tracker:
        return

    from models.interview import Interview
    from sqlalchemy import func
    scheduled_interviews_count = db.scalar(
        select(func.count(Interview.id)).where(
            Interview.application_id == application_id,
            Interview.status == "scheduled"
        )
    )

    stage = db.get(StageDefinition, tracker.stage_definition_id)
    should_pause = (
        scheduled_interviews_count > 0 or
        (stage and stage.settings.get("pause_sla") is True)
    )

    now = datetime.now(timezone.utc)
    if should_pause and tracker.status == "active":
        tracker.paused_at = now
        tracker.status = "paused"
        db.commit()
    elif not should_pause and tracker.status == "paused" and tracker.paused_at is not None:
        paused_duration = (now - tracker.paused_at.replace(tzinfo=timezone.utc)).total_seconds()
        tracker.total_paused_seconds += int(paused_duration)
        tracker.expires_at = tracker.expires_at.replace(tzinfo=timezone.utc) + timedelta(seconds=paused_duration)
        tracker.paused_at = None
        tracker.status = "active"
        db.commit()


def evaluate_auto_progression_rules(db: Session, application: Application, context: dict | None = None) -> bool:
    """
    Evaluates all auto-progression rules configured on the application's current stage.
    If a rule matches, transitions the candidate to the target stage.
    """
    if not application.current_stage_id:
        return False
        
    # Get current stage definition
    current_stage = db.scalar(
        select(StageDefinition).where(StageDefinition.id == application.current_stage_id)
    )
    if not current_stage:
        return False
        
    # Check if there are auto-progression rules configured in stage.settings
    rules = current_stage.settings.get("auto_progression_rules", [])
    if not rules:
        return False
        
    # Build evaluation context
    eval_results = {
        "status": application.status.value if application.status else None,
        "source": application.source,
        "scorecard": {},
        "assessment": {}
    }
    
    # If there are scorecards associated, load them
    if application.scorecards:
        sorted_scorecards = sorted(application.scorecards, key=lambda s: s.created_at, reverse=True)
        latest_scorecard = sorted_scorecards[0]
        eval_results["scorecard"] = {
            "overall_recommendation": latest_scorecard.overall_recommendation,
            "notes": latest_scorecard.notes,
        }
        
    if context:
        # Merge extra context
        for k, v in context.items():
            if isinstance(v, dict) and k in eval_results and isinstance(eval_results[k], dict):
                eval_results[k].update(v)
            else:
                eval_results[k] = v
                
    # Evaluate rules sequentially
    for rule in rules:
        try:
            # Let's ensure rule has the keys
            if not all(k in rule for k in ("field", "operator", "value", "target_stage_id")):
                continue
                
            if evaluate_structured_rule(rule, eval_results):
                # Transition candidate stage!
                target_stage_id = uuid.UUID(str(rule["target_stage_id"]))
                transition_candidate_stage(
                    db=db,
                    company_id=application.company_id,
                    application_id=application.id,
                    target_stage_id=target_stage_id,
                    actor_id=None,
                    is_auto=True
                )
                return True
        except Exception as e:
            # Log failure audit event: pipeline.auto_progression_failed
            db.rollback()
            log_audit_event(
                db=db,
                action="pipeline.auto_progression_failed",
                actor_type="system",
                company_id=application.company_id,
                resource_type="application",
                resource_id=str(application.id),
                metadata={
                    "rule": rule,
                    "error": str(e),
                    "error_type": e.__class__.__name__
                }
            )
            logger.exception("Auto-progression rule evaluation failed")
            
    return False


def validate_stage_exit_requirements(db: Session, application: Application, current_stage: StageDefinition):
    """
    Validates stage-level exit gate requirements (scorecard, interview, note, or resume)
    before allowing a candidate to transition to the next stage.
    """
    if not current_stage or not current_stage.settings:
        return

    settings = current_stage.settings

    # 1. Scorecard required
    if settings.get("scorecard_required") is True:
        from models.scorecard import Scorecard
        submitted_scorecard = db.scalar(
            select(Scorecard).where(
                Scorecard.application_id == application.id,
                Scorecard.is_draft == False
            )
        )
        if not submitted_scorecard:
            raise ValueError(f"Exit requirement failed: A final scorecard is required for the stage '{current_stage.name}' before moving the candidate.")

    # 2. Interview required
    if settings.get("interview_required") is True:
        from models.interview import Interview
        completed_interview = db.scalar(
            select(Interview).where(
                Interview.application_id == application.id,
                Interview.is_cancelled == False
            )
        )
        if not completed_interview:
            raise ValueError(f"Exit requirement failed: A completed interview is required for the stage '{current_stage.name}' before moving the candidate.")

    # 3. Note required
    if settings.get("note_required") is True:
        from models.note import CandidateNote
        note = db.scalar(
            select(CandidateNote).where(CandidateNote.application_id == application.id)
        )
        if not note:
            raise ValueError(f"Exit requirement failed: A recruiter note is required for the stage '{current_stage.name}' before moving the candidate.")

    # 4. Resume required
    if settings.get("resume_required") is True:
        from models.candidate_resume import CandidateResume
        resume = db.scalar(
            select(CandidateResume).where(
                CandidateResume.user_id == application.candidate_id,
                CandidateResume.is_active == True
            )
        )
        if not resume:
            raise ValueError(f"Exit requirement failed: A candidate resume is required for the stage '{current_stage.name}' before moving the candidate.")

