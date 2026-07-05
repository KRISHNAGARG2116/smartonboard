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
    - Validates allowed stage transition rules and prevents invalid terminal transitions.
    - Updates application.current_stage_id and syncs application.status.
    - Record movement to CandidateStageHistory.
    - Marks active in-stage SLA trackers as 'completed'.
    - Instantiates a new SLA tracker for the target stage if defined & enabled.
    - Logs timeline events via the centralized ApplicationEventService.
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
    
    # 2. Fetch Target Stage
    target_stage = db.scalar(
        select(StageDefinition).where(
            StageDefinition.id == target_stage_id,
            StageDefinition.company_id == company_id
        )
    )
    if not target_stage:
        raise ValueError("Target stage definition not found")

    # Validate Transitions
    if from_stage_id:
        current_stage = db.get(StageDefinition, from_stage_id)
        if current_stage:
            # Block moving out of terminal stages unless user is owner
            if current_stage.is_terminal:
                is_owner = False
                if actor_id:
                    from models.user import User
                    from models.enums import UserRole
                    actor = db.get(User, actor_id)
                    if actor and actor.role == UserRole.OWNER:
                        is_owner = True
                if not is_owner:
                    raise ValueError("Only a Company Owner can move a candidate out of a terminal stage.")
            
            # Check allowed workflow transitions
            if current_stage.allowed_next_stage_ids:
                allowed_uuids = [uuid.UUID(str(x)) for x in current_stage.allowed_next_stage_ids]
                if target_stage_id not in allowed_uuids:
                    raise ValueError(f"Transition from stage '{current_stage.name}' to '{target_stage.name}' is not allowed by the workflow rules.")
            
            validate_stage_exit_requirements(db, application, current_stage)
    
    # 3. Complete existing SLA trackers
    db.execute(
        update(CandidateStageSLATracker)
        .where(
            CandidateStageSLATracker.application_id == application_id,
            CandidateStageSLATracker.status.in_(["active", "breached", "paused"])
        )
        .values(status="completed")
    )
    
    # 4. Perform Transition
    application.current_stage_id = target_stage_id
    # Sync status with target stage's base category
    new_status = MAP_BASE_CATEGORY_TO_STATUS.get(target_stage.base_category, ApplicationStatus.SCREENING)
    application.status = new_status
    
    # Write to CandidateStageHistory
    from models.stage_transition import CandidateStageHistory
    history = CandidateStageHistory(
        company_id=company_id,
        application_id=application_id,
        previous_stage_id=from_stage_id,
        new_stage_id=target_stage_id,
        changed_by=actor_id,
        reason="API transitioned stage" if not is_auto else "Auto-progression rule matched"
    )
    db.add(history)
    db.flush()
    
    # 5. Instantiate new SLA tracker if configured and enabled
    if target_stage.sla_enabled:
        sla = db.scalar(
            select(StageSLA).where(
                StageSLA.stage_definition_id == target_stage_id,
                StageSLA.company_id == company_id
            )
        )
        duration_seconds = None
        if sla:
            duration_seconds = sla.duration_seconds
        elif target_stage.sla_hours is not None:
            duration_seconds = target_stage.sla_hours * 3600

        if duration_seconds is not None:
            now = datetime.now(timezone.utc)
            tracker = CandidateStageSLATracker(
                company_id=company_id,
                application_id=application_id,
                stage_definition_id=target_stage_id,
                entered_at=now,
                expires_at=now + timedelta(seconds=duration_seconds),
                status="active",
                escalation_count=0
            )
            db.add(tracker)
            db.flush()

    # 6. Apply SLA pausing checks
    check_and_update_sla_timers(db, application_id)
    
    # Log event to centralized timeline
    from core.application_events import ApplicationEventService
    ApplicationEventService.record_event(
        db=db,
        company_id=company_id,
        application_id=application_id,
        event_type="application.stage_changed",
        actor_id=actor_id,
        previous_value=str(from_stage_id) if from_stage_id else None,
        new_value=str(target_stage_id)
    )
        
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
    stage_name = stage.name.lower() if (stage and stage.name) else ""
    should_pause = (
        scheduled_interviews_count > 0 or
        (stage and stage.settings.get("pause_sla") is True) or
        "waiting for candidate" in stage_name or
        "waiting for hiring manager" in stage_name or
        "waiting for interview" in stage_name or
        "waiting" in stage_name
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


def ensure_job_stages(db: Session, job_id: uuid.UUID, company_id: uuid.UUID) -> list[StageDefinition]:
    """
    Checks if active stages exist for a job, and if not, initializes the default 8 stages.
    """
    stages = db.scalars(
        select(StageDefinition)
        .where(
            StageDefinition.job_id == job_id,
            StageDefinition.company_id == company_id,
            StageDefinition.deleted_at.is_(None)
        )
        .order_by(StageDefinition.position.asc())
    ).all()
    if stages:
        return list(stages)

    defaults = [
        ("Applied", "applied", "#3b82f6", "inbox", 10, True, False),
        ("Screening", "screening", "#f59e0b", "search", 20, False, False),
        ("Interview", "interviewing", "#8b5cf6", "calendar", 30, False, False),
        ("Technical", "screening", "#6366f1", "code", 40, False, False),
        ("Final Interview", "interviewing", "#a855f7", "users", 50, False, False),
        ("Offer", "offered", "#10b981", "document", 60, False, False),
        ("Hired", "hired", "#10b981", "check", 70, False, True),
        ("Rejected", "rejected", "#ef4444", "x", 80, False, True),
    ]

    created_stages = []
    for name, category, color, icon, position, is_default, is_terminal in defaults:
        stage = StageDefinition(
            company_id=company_id,
            job_id=job_id,
            name=name,
            base_category=category,
            color=color,
            icon=icon,
            position=position,
            sequence=position,
            is_active=True,
            is_default=is_default,
            is_terminal=is_terminal,
            sla_enabled=True,
            sla_hours=24 if name == "Applied" else None
        )
        db.add(stage)
        created_stages.append(stage)
    db.flush()
    return created_stages

