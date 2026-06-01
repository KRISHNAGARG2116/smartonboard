import uuid
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from core.celery_app import celery_app
from db.session import SessionLocal, tenant_context
from models.application import Application
from models.pipeline import StageDefinition
from models.sla import StageSLA, CandidateStageSLATracker
from models.approval import ApprovalChain, ApprovalStep, ApprovalTemplateStep
from models.escalation import ApprovalEscalationRule, ApprovalStepEscalation
from models.enums import ApplicationStatus
from models.audit import AuditLog
from core.workflows import transition_candidate_stage
from core.audit import log_audit_event

logger = logging.getLogger(__name__)

def sweep_sla_breaches():
    """
    Sweeps all active candidate stage SLA trackers.
    Triggers actions (notifications, auto-rejection, auto-advancement) if breached.
    Enforces loop protection of max 1 escalation.
    """
    with tenant_context(auth_mode="true"):
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            # Find expired active trackers (escalation_count < 1 for loop protection)
            trackers = db.scalars(
                select(CandidateStageSLATracker)
                .where(
                    CandidateStageSLATracker.status == "active",
                    CandidateStageSLATracker.expires_at <= now,
                    CandidateStageSLATracker.escalation_count < 1
                )
            ).all()
            
            for tracker in trackers:
                try:
                    # 1. Update status to breached and increment escalation count
                    tracker.status = "breached"
                    tracker.breached_at = now
                    tracker.escalation_count += 1
                    db.flush()
                    
                    # 2. Log breach event
                    log_audit_event(
                        db=db,
                        action="pipeline.stage_sla_breached",
                        actor_type="system",
                        company_id=tracker.company_id,
                        resource_type="candidate_stage_sla_tracker",
                        resource_id=str(tracker.id),
                        metadata={
                            "application_id": str(tracker.application_id),
                            "stage_definition_id": str(tracker.stage_definition_id)
                        }
                    )
                    
                    # 3. Retrieve registered SLA policy
                    sla = db.scalar(
                        select(StageSLA).where(
                            StageSLA.stage_definition_id == tracker.stage_definition_id,
                            StageSLA.company_id == tracker.company_id
                        )
                    )
                    if not sla:
                        db.commit()
                        continue
                        
                    action = sla.escalation_action
                    if action == "auto_advance" and sla.fallback_stage_id:
                        # Auto-advance candidate to fallback stage definition!
                        transition_candidate_stage(
                            db=db,
                            company_id=tracker.company_id,
                            application_id=tracker.application_id,
                            target_stage_id=sla.fallback_stage_id,
                            is_auto=True
                        )
                    elif action == "auto_reject":
                        # Reject application
                        application = db.get(Application, tracker.application_id)
                        if application:
                            application.status = ApplicationStatus.REJECTED
                            db.flush()
                            log_audit_event(
                                db=db,
                                action="pipeline.auto_rejected",
                                actor_type="system",
                                company_id=tracker.company_id,
                                resource_type="application",
                                resource_id=str(tracker.application_id),
                                metadata={"reason": "SLA breach auto-reject"}
                            )
                            
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.error(f"Failed to process SLA breach for tracker {tracker.id}: {e}", exc_info=True)
        finally:
            db.close()

def sweep_approval_escalations():
    """
    Sweeps active approval chains for timed out pending steps.
    Applies timeout escalation rules (delegation, auto-approval, auto-rejection)
    and dispatches recurring approver reminders.
    Enforces loop protection by skipping already escalated steps.
    """
    with tenant_context(auth_mode="true"):
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            # Fetch pending approval chains
            chains = db.scalars(
                select(ApprovalChain).where(ApprovalChain.status == "pending")
            ).all()
            
            for chain in chains:
                # Fetch pending steps in the current sequence of the chain
                steps = db.scalars(
                    select(ApprovalStep)
                    .where(
                        ApprovalStep.approval_chain_id == chain.id,
                        ApprovalStep.sequence == chain.current_step_sequence,
                        ApprovalStep.status == "pending"
                    )
                ).all()
                
                for step in steps:
                    try:
                        # 1. Fetch matching Template Step
                        t_step_stmt = select(ApprovalTemplateStep).where(
                            ApprovalTemplateStep.approval_template_id == chain.approval_template_id,
                            ApprovalTemplateStep.sequence == step.sequence,
                            ApprovalTemplateStep.company_id == step.company_id
                        )
                        if step.parallel_group is not None:
                            t_step_stmt = t_step_stmt.where(ApprovalTemplateStep.parallel_group == step.parallel_group)
                        else:
                            t_step_stmt = t_step_stmt.where(ApprovalTemplateStep.parallel_group.is_(None))
                            
                        t_step = db.scalar(t_step_stmt)
                        if not t_step:
                            continue
                            
                        # 2. Fetch escalation rule configured on the template step
                        rule = db.scalar(
                            select(ApprovalEscalationRule).where(
                                ApprovalEscalationRule.approval_template_step_id == t_step.id,
                                ApprovalEscalationRule.company_id == step.company_id
                            )
                        )
                        if not rule:
                            continue
                            
                        # 3. Handle Reminder Dispatch
                        reminder_threshold = timedelta(seconds=rule.timeout_seconds / 2)
                        if now - step.created_at >= reminder_threshold:
                            reminder_exists = db.scalar(
                                select(AuditLog).where(
                                    AuditLog.action == "approval.step_reminder_sent",
                                    AuditLog.resource_id == str(step.id),
                                    AuditLog.company_id == step.company_id
                                )
                            )
                            if not reminder_exists:
                                log_audit_event(
                                    db=db,
                                    action="approval.step_reminder_sent",
                                    actor_type="system",
                                    company_id=step.company_id,
                                    resource_type="approval_step",
                                    resource_id=str(step.id),
                                    metadata={"approver_id": str(step.approver_id) if step.approver_id else None}
                                )
                                db.commit()
                                
                        # 4. Handle Timeout Escalations
                        if now - step.created_at >= timedelta(seconds=rule.timeout_seconds):
                            # Loop Protection: check if step is already escalated
                            already_escalated = db.scalar(
                                select(ApprovalStepEscalation).where(
                                    ApprovalStepEscalation.approval_step_id == step.id,
                                    ApprovalStepEscalation.company_id == step.company_id
                                )
                            )
                            if already_escalated:
                                continue
                                
                            esc_type = rule.escalation_type
                            if esc_type == "delegate" and rule.delegate_id:
                                # Delegate step
                                old_approver = step.approver_id
                                step.approver_id = rule.delegate_id
                                step.updated_at = now
                                db.flush()
                                
                                esc = ApprovalStepEscalation(
                                    company_id=step.company_id,
                                    approval_step_id=step.id,
                                    triggered_at=now,
                                    action_taken=f"Delegated approval from {old_approver} to {rule.delegate_id}"
                                )
                                db.add(esc)
                                
                                log_audit_event(
                                    db=db,
                                    action="approval.step_escalated",
                                    actor_type="system",
                                    company_id=step.company_id,
                                    resource_type="approval_step",
                                    resource_id=str(step.id),
                                    metadata={"action_taken": "delegate", "delegate_id": str(rule.delegate_id)}
                                )
                                
                            elif esc_type == "auto_approve":
                                # Auto approve step
                                step.status = "approved"
                                step.actioned_at = now
                                db.flush()
                                
                                esc = ApprovalStepEscalation(
                                    company_id=step.company_id,
                                    approval_step_id=step.id,
                                    triggered_at=now,
                                    resolved_at=now,
                                    action_taken="Auto-approved step sequence due to timeout"
                                )
                                db.add(esc)
                                
                                log_audit_event(
                                    db=db,
                                    action="approval.step_approved",
                                    actor_type="system",
                                    company_id=step.company_id,
                                    resource_type="approval_step",
                                    resource_id=str(step.id),
                                    metadata={"chain_id": str(chain.id), "is_auto": True}
                                )
                                
                                log_audit_event(
                                    db=db,
                                    action="approval.step_escalated",
                                    actor_type="system",
                                    company_id=step.company_id,
                                    resource_type="approval_step",
                                    resource_id=str(step.id),
                                    metadata={"action_taken": "auto_approve"}
                                )
                                
                                # Advance chain sequence if no other parallel steps pending in sequence
                                pending_steps = db.scalar(
                                    select(func.count(ApprovalStep.id)).where(
                                        ApprovalStep.approval_chain_id == chain.id,
                                        ApprovalStep.sequence == step.sequence,
                                        ApprovalStep.status == "pending"
                                    )
                                )
                                if pending_steps == 0:
                                    next_seq = db.scalar(
                                        select(ApprovalStep.sequence).where(
                                            ApprovalStep.approval_chain_id == chain.id,
                                            ApprovalStep.sequence > step.sequence
                                        ).order_by(ApprovalStep.sequence.asc()).limit(1)
                                    )
                                    if next_seq:
                                        chain.current_step_sequence = next_seq
                                    else:
                                        chain.status = "approved"
                                        log_audit_event(
                                            db=db,
                                            action="approval.chain_completed",
                                            actor_type="system",
                                            company_id=chain.company_id,
                                            resource_type="approval_chain",
                                            resource_id=str(chain.id),
                                            metadata={"status": "approved"}
                                        )
                                        
                            elif esc_type == "auto_reject":
                                # Auto reject step
                                step.status = "rejected"
                                step.actioned_at = now
                                step.rejection_reason = "Approval timed out (escalation auto-reject)"
                                chain.status = "rejected"
                                db.flush()
                                
                                esc = ApprovalStepEscalation(
                                    company_id=step.company_id,
                                    approval_step_id=step.id,
                                    triggered_at=now,
                                    resolved_at=now,
                                    action_taken="Auto-rejected step sequence due to timeout"
                                )
                                db.add(esc)
                                
                                log_audit_event(
                                    db=db,
                                    action="approval.step_rejected",
                                    actor_type="system",
                                    company_id=step.company_id,
                                    resource_type="approval_step",
                                    resource_id=str(step.id),
                                    metadata={"chain_id": str(chain.id), "reason": "Escalation auto-reject"}
                                )
                                
                                log_audit_event(
                                    db=db,
                                    action="approval.step_escalated",
                                    actor_type="system",
                                    company_id=step.company_id,
                                    resource_type="approval_step",
                                    resource_id=str(step.id),
                                    metadata={"action_taken": "auto_reject"}
                                )
                                
                            db.commit()
                    except Exception as e:
                        db.rollback()
                        logger.error(f"Failed to process escalation for step {step.id}: {e}", exc_info=True)
        finally:
            db.close()

@celery_app.task
def check_sla_breaches_task():
    sweep_sla_breaches()

@celery_app.task
def check_approval_escalations_task():
    sweep_approval_escalations()


def sweep_onboarding_escalations():
    """
    Scans outstanding pending onboarding tasks past their due dates,
    applying Level 1, Level 2, and Level 3 escalations recursively.
    """
    with tenant_context(auth_mode="true"):
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            # Fetch pending onboarding tasks with due_date in the past
            from models import OnboardingTask, OnboardingWorkflow, Employee, User, OnboardingTaskEscalation, OnboardingTaskReminder
            
            stmt = select(OnboardingTask).where(
                OnboardingTask.status == "pending",
                OnboardingTask.due_date < now.date()
            )
            overdue_tasks = db.scalars(stmt).all()
            
            for task in overdue_tasks:
                try:
                    # Resolve active onboarding workflow & employee for metadata
                    wf = db.get(OnboardingWorkflow, task.workflow_id)
                    if not wf:
                        continue
                    emp = db.get(Employee, wf.employee_id)
                    if not emp:
                        continue
                        
                    # Calculate duration overdue (in days)
                    due_datetime = datetime.combine(task.due_date, datetime.min.time(), tzinfo=timezone.utc)
                    delta_days = (now - due_datetime).days
                    
                    if delta_days >= 5:
                        # LEVEL 3: HR Escalation (escalate to company recruiter or admin)
                        existing_l3 = db.scalar(
                            select(OnboardingTaskEscalation).where(
                                OnboardingTaskEscalation.task_id == task.id,
                                OnboardingTaskEscalation.escalation_level == 3
                            )
                        )
                        if not existing_l3:
                            hr_user = db.scalar(
                                select(User).where(
                                    User.company_id == task.company_id,
                                    User.role == "recruiter"
                                ).limit(1)
                            )
                            if not hr_user:
                                hr_user = db.scalar(
                                    select(User).where(
                                        User.company_id == task.company_id,
                                        User.role == "owner"
                                    ).limit(1)
                                )
                            if hr_user:
                                escalation = OnboardingTaskEscalation(
                                    company_id=task.company_id,
                                    task_id=task.id,
                                    escalated_to_id=hr_user.id,
                                    escalation_level=3,
                                    triggered_at=now
                                )
                                db.add(escalation)
                                db.flush()
                                
                                # Log Activity Log
                                from core.signatures import log_onboarding_activity
                                log_onboarding_activity(
                                    db=db,
                                    company_id=task.company_id,
                                    employee_id=emp.id,
                                    actor_id=None,
                                    actor_type="system",
                                    event_type="escalation_triggered",
                                    metadata={
                                        "task_id": str(task.id),
                                        "task_title": task.title,
                                        "escalation_level": 3,
                                        "escalated_to": hr_user.email
                                    }
                                )
                                
                                # Log Audit event
                                log_audit_event(
                                    db=db,
                                    action="onboarding.task_escalated",
                                    actor_type="system",
                                    company_id=task.company_id,
                                    resource_type="onboarding_task",
                                    resource_id=str(task.id),
                                    metadata={"escalation_level": 3, "escalated_to_id": str(hr_user.id)}
                                )
                                db.commit()
                                
                    elif delta_days >= 3:
                        # LEVEL 2: Manager Notification (escalate to supervisor)
                        existing_l2 = db.scalar(
                            select(OnboardingTaskEscalation).where(
                                OnboardingTaskEscalation.task_id == task.id,
                                OnboardingTaskEscalation.escalation_level == 2
                            )
                        )
                        if not existing_l2 and emp.supervisor_id:
                            supervisor = db.get(Employee, emp.supervisor_id)
                            supervisor_user = None
                            if supervisor:
                                supervisor_user = db.scalar(
                                    select(User).where(
                                        User.company_id == task.company_id,
                                        User.email == supervisor.email
                                    )
                                )
                            
                            if not supervisor_user:
                                supervisor_user = db.scalar(
                                    select(User).where(
                                        User.company_id == task.company_id,
                                        User.role == "recruiter"
                                    ).limit(1)
                                )
                            if not supervisor_user:
                                supervisor_user = db.scalar(
                                    select(User).where(
                                        User.company_id == task.company_id,
                                        User.role == "owner"
                                    ).limit(1)
                                )
                                
                            if supervisor_user:
                                escalation = OnboardingTaskEscalation(
                                    company_id=task.company_id,
                                    task_id=task.id,
                                    escalated_to_id=supervisor_user.id,
                                    escalation_level=2,
                                    triggered_at=now
                                )
                                db.add(escalation)
                                db.flush()
                                
                                # Log Activity Log
                                from core.signatures import log_onboarding_activity
                                log_onboarding_activity(
                                    db=db,
                                    company_id=task.company_id,
                                    employee_id=emp.id,
                                    actor_id=None,
                                    actor_type="system",
                                    event_type="escalation_triggered",
                                    metadata={
                                        "task_id": str(task.id),
                                        "task_title": task.title,
                                        "escalation_level": 2,
                                        "escalated_to": supervisor_user.email
                                    }
                                )
                                
                                # Log Audit event
                                log_audit_event(
                                    db=db,
                                    action="onboarding.task_escalated",
                                    actor_type="system",
                                    company_id=task.company_id,
                                    resource_type="onboarding_task",
                                    resource_id=str(task.id),
                                    metadata={"escalation_level": 2, "escalated_to_id": str(supervisor_user.id)}
                                )
                                db.commit()
                                
                    elif delta_days >= 1:
                        # LEVEL 1: Assignee Reminder (dispatches an assignee reminder)
                        recent_reminder = db.scalar(
                            select(OnboardingTaskReminder).where(
                                OnboardingTaskReminder.task_id == task.id,
                                OnboardingTaskReminder.created_at >= now - timedelta(hours=24)
                            )
                        )
                        if not recent_reminder:
                            reminder = OnboardingTaskReminder(
                                company_id=task.company_id,
                                task_id=task.id,
                                notification_channel="email",
                                scheduled_at=now,
                                dispatched_at=now,
                                status="sent",
                                created_at=now
                            )
                            db.add(reminder)
                            db.flush()
                            
                            # Log Activity Log
                            from core.signatures import log_onboarding_activity
                            log_onboarding_activity(
                                db=db,
                                company_id=task.company_id,
                                employee_id=emp.id,
                                actor_id=None,
                                actor_type="system",
                                event_type="reminder_sent",
                                metadata={
                                    "task_id": str(task.id),
                                    "task_title": task.title,
                                    "channel": "email"
                                }
                            )
                            
                            # Log Audit event
                            log_audit_event(
                                db=db,
                                action="onboarding.task_reminder_sent",
                                actor_type="system",
                                company_id=task.company_id,
                                resource_type="onboarding_task",
                                resource_id=str(task.id),
                                metadata={"channel": "email"}
                            )
                            db.commit()
                            
                except Exception as ex:
                    db.rollback()
                    logger.error(f"Failed to process onboarding task escalation for task {task.id}: {ex}", exc_info=True)
        finally:
            db.close()


@celery_app.task
def process_onboarding_escalations_task():
    sweep_onboarding_escalations()

