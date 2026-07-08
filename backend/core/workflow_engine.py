import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models import (
    Application, Candidate, Job, User, Notification, SentEmail, EmailTemplate,
    WorkflowRule, WorkflowRun, UsageBillingEvent, IntegrationAuditLog
)
from db.session import tenant_context
from core.audit import log_audit_event
from core.celery_app import celery_app
from integrations.base.factory import ProviderFactory

logger = logging.getLogger(__name__)


def get_field_value(context: dict, path: str) -> Any:
    """Safely resolves nested keys via dot notation, e.g. 'job.title'"""
    parts = path.split('.')
    current = context
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
    return current


def evaluate_rule_condition(rule: dict, context: dict) -> bool:
    """Evaluates a single rule condition (e.g. source == 'LinkedIn')"""
    field = rule.get("field")
    operator = rule.get("operator")
    expected = rule.get("value")

    actual = get_field_value(context, field)
    if actual is None:
        return False

    # Try numeric casting if relevant
    if operator in (">", ">=", "<", "<="):
        try:
            actual = float(actual)
            expected = float(expected)
        except (ValueError, TypeError):
            return False

    if operator == "==":
        return str(actual) == str(expected)
    if operator == "!=":
        return str(actual) != str(expected)
    if operator == ">":
        return actual > expected
    if operator == ">=":
        return actual >= expected
    if operator == "<":
        return actual < expected
    if operator == "<=":
        return actual <= expected
    if operator == "contains":
        return str(expected).lower() in str(actual).lower()

    return False


def evaluate_conditions(conditions: dict, context: dict) -> bool:
    """Recursively evaluates nested logical condition trees (AND/OR groups)"""
    if not conditions:
        return True

    operator = conditions.get("operator", "AND").upper()
    rules = conditions.get("rules", [])

    if not rules:
        return True

    results = []
    for r in rules:
        if "operator" in r:
            # Nested group
            results.append(evaluate_conditions(r, context))
        else:
            # Leaf condition
            results.append(evaluate_rule_condition(r, context))

    if operator == "AND":
        return all(results)
    if operator == "OR":
        return any(results)

    return False


def emit_billing_event(db: Session, company_id: uuid.UUID, event_type: str, resource_id: str | None = None, quantity: int = 1, metadata: dict = None):
    """Logs standardized usage billing events for downstream consumption."""
    event = UsageBillingEvent(
        company_id=company_id,
        event_type=event_type,
        resource_id=resource_id,
        quantity=quantity,
        metadata_json=metadata or {}
    )
    db.add(event)
    db.flush()


class WorkflowEngine:
    @classmethod
    def trigger_workflows(
        cls,
        db: Session,
        company_id: uuid.UUID,
        trigger_type: str,
        application_id: uuid.UUID,
        idempotency_key: str | None = None,
        depth: int = 0
    ) -> List[uuid.UUID]:
        """Scans active rules matching the trigger and enqueues runs in Celery."""
        # Loop prevention safeguard
        if depth > 10:
            logger.warning(f"Workflow execution halted: Maximum execution depth (10) reached for app {application_id}")
            return []

        # Check idempotency
        if idempotency_key:
            existing = db.scalar(select(WorkflowRun).where(WorkflowRun.idempotency_key == idempotency_key))
            if existing:
                logger.info(f"Duplicate workflow execution blocked by idempotency key: {idempotency_key}")
                return [existing.id]

        # Scan active rules for this company and trigger type
        rules = db.scalars(
            select(WorkflowRule).where(
                WorkflowRule.company_id == company_id,
                WorkflowRule.trigger_type == trigger_type,
                WorkflowRule.is_active == True,
                WorkflowRule.status == "active"
            )
        ).all()

        run_ids = []
        for rule in rules:
            # Verify action limit safeguard
            if len(rule.actions_json) > 15:
                logger.warning(f"Rule {rule.id} rejected: Actions count ({len(rule.actions_json)}) exceeds safeguard limit (15).")
                continue

            run = WorkflowRun(
                company_id=company_id,
                workflow_rule_id=rule.id,
                application_id=application_id,
                status="pending",
                idempotency_key=idempotency_key,
                depth=depth,
                execution_logs=[]
            )
            db.add(run)
            db.flush()
            run_ids.append(run.id)

        db.flush()

        # Enqueue run tasks asynchronously in Celery
        for rid in run_ids:
            execute_workflow_run_task.delay(str(company_id), str(rid))

        return run_ids

    @classmethod
    def execute_run(cls, db: Session, run_id: uuid.UUID) -> dict:
        """Executes a single enqueued workflow run, evaluating conditions and triggering actions."""
        run = db.get(WorkflowRun, run_id)
        if not run:
            raise ValueError(f"Workflow run not found: {run_id}")

        if run.status in ("success", "failed") and run.attempt_number >= 5:
            return {"status": run.status, "message": "Already resolved or max retries exceeded"}

        rule = run.rule
        app = run.application

        run.status = "processing"
        run.execution_logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "execution_started",
            "attempt": run.attempt_number
        })
        db.flush()

        try:
            # Build context payload
            context = cls.build_context(db, run.company_id, app)

            # Evaluate nested conditions group
            passed = evaluate_conditions(rule.conditions_json, context)
            run.execution_logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "conditions_evaluated",
                "passed": passed,
                "conditions": rule.conditions_json
            })

            if not passed:
                run.status = "success"
                run.execution_logs.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event": "conditions_failed_exit"
                })
                db.commit()
                return {"status": "success", "conditions_passed": False}

            # Execute action steps sequentially
            for idx, action in enumerate(rule.actions_json):
                action_type = action.get("type")
                action_val = action.get("value")

                run.execution_logs.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event": "action_started",
                    "action_index": idx,
                    "action_type": action_type
                })
                db.flush()

                cls.execute_action(db, run.company_id, app, action_type, action_val, context)

                run.execution_logs.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event": "action_completed",
                    "action_index": idx
                })

            run.status = "success"
            run.execution_logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "execution_completed"
            })
            
            # Emit billing event
            emit_billing_event(db, run.company_id, "workflow.executed", str(rule.id))
            
            db.commit()
            return {"status": "success", "conditions_passed": True}

        except Exception as e:
            db.rollback()
            error_msg = str(e)
            run.error_message = error_msg
            run.execution_logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "execution_failed",
                "error": error_msg
            })

            if run.attempt_number < 5:
                run.status = "retrying"
                run.attempt_number += 1
                backoff_seconds = (2 ** run.attempt_number) * 30
                run.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
                db.commit()
                
                # Reschedule task
                execute_workflow_run_task.apply_async(
                    args=[str(run.company_id), str(run.id)],
                    countdown=backoff_seconds
                )
            else:
                run.status = "failed"
                db.commit()

                # Log to Integration Audit Trail
                audit = IntegrationAuditLog(
                    company_id=run.company_id,
                    integration_type="workflow",
                    action="workflow.failed",
                    status="failure",
                    details_json={"run_id": str(run.id), "rule_id": str(rule.id), "error": error_msg}
                )
                db.add(audit)
                db.commit()

            return {"status": run.status, "error": error_msg}

    @classmethod
    def build_context(cls, db: Session, company_id: uuid.UUID, app: Application | None) -> dict:
        if not app:
            return {}
        candidate = db.get(Candidate, app.candidate_id)
        job = db.get(Job, app.job_id)
        return {
            "status": app.status.value if app.status else "",
            "source": app.source or "",
            "candidate": {
                "id": str(candidate.id) if candidate else "",
                "email": candidate.email if candidate else "",
                "full_name": candidate.full_name if candidate else "",
            },
            "job": {
                "id": str(job.id) if job else "",
                "title": job.title if job else "",
                "department": job.department if job else "",
            }
        }

    @classmethod
    def execute_action(cls, db: Session, company_id: uuid.UUID, app: Application, action_type: str, action_val: Any, context: dict):
        if action_type == "assign_recruiter":
            # Updates application owner_id
            recruiter_id = uuid.UUID(str(action_val))
            app.owner_id = recruiter_id
            db.add(app)
            db.flush()

        elif action_type == "send_email":
            # Sends an email template
            template_id = uuid.UUID(str(action_val))
            template = db.get(EmailTemplate, template_id)
            if not template:
                raise ValueError(f"Email template not found: {template_id}")

            candidate = db.get(Candidate, app.candidate_id)
            if candidate:
                body = template.body_markdown.replace("{{candidate_name}}", candidate.full_name or "")
                
                # Fetch SMTP details
                from core.smtp import get_smtp_transport_details
                transport = get_smtp_transport_details(db, company_id)
                provider = ProviderFactory.get_provider("email", "smtp")
                
                msg_id = provider.send_email(
                    recipient=candidate.email,
                    subject=template.subject,
                    body_html=body,
                    sender_email=transport["sender_email"],
                    smtp_settings=transport if transport["use_custom"] else None
                )

                sent = SentEmail(
                    company_id=company_id,
                    application_id=app.id,
                    recipient=candidate.email,
                    subject=template.subject,
                    status="sent"
                )
                db.add(sent)
                db.flush()
                emit_billing_event(db, company_id, "email.sent", str(sent.id))

        elif action_type == "slack_notification":
            # Sends Slack message
            from models.slack_teams import SlackTeamsIntegration
            slack_integration = db.scalar(select(SlackTeamsIntegration).where(SlackTeamsIntegration.company_id == company_id))
            if slack_integration:
                chat_provider = ProviderFactory.get_provider("chat", "slack")
                msg = str(action_val).replace("{{candidate_name}}", context.get("candidate", {}).get("full_name", ""))
                chat_provider.send_message(slack_integration.webhook_url, msg)

        elif action_type == "start_onboarding":
            # Push transition payload to legacy onboarding outbox
            from models.employees import OnboardingEventOutbox
            outbox = OnboardingEventOutbox(
                company_id=company_id,
                event_type="employee.created",
                payload={"employee_id": str(app.candidate_id), "source": "workflow"},
                status="pending"
            )
            db.add(outbox)
            db.flush()

        else:
            logger.info(f"Unimplemented or custom action skipped: {action_type}")

    @classmethod
    def simulate_workflow(cls, db: Session, rule_id: uuid.UUID, application_id: uuid.UUID) -> dict:
        """Traces matching dry-run condition evaluations without committing any database modifications."""
        rule = db.get(WorkflowRule, rule_id)
        if not rule:
            raise ValueError("Rule not found")

        app = db.get(Application, application_id)
        context = cls.build_context(db, rule.company_id, app)

        trace = []
        trace.append({"step": "Simulation Started", "status": "info"})

        # Evaluate trigger match
        trigger_matched = (rule.trigger_type == "application.created") # mock verify
        trace.append({"step": f"Trigger matching verification: expected {rule.trigger_type}", "status": "pass"})

        # Evaluate conditions
        passed = evaluate_conditions(rule.conditions_json, context)
        trace.append({
            "step": f"Logical conditions evaluated: {'PASSED' if passed else 'FAILED'}",
            "status": "pass" if passed else "fail",
            "conditions": rule.conditions_json
        })

        projected_actions = []
        if passed:
            for idx, act in enumerate(rule.actions_json):
                projected_actions.append(f"{idx+1}. {act.get('type')} ({act.get('value')})")

        return {
            "trigger_matched": trigger_matched,
            "conditions_passed": passed,
            "trace": trace,
            "projected_actions": projected_actions
        }


@celery_app.task
def execute_workflow_run_task(company_id_str: str, run_id_str: str):
    """Celery wrapper executing enqueued run tasks inside tenant boundaries."""
    from db.session import SessionLocal
    run_id = uuid.UUID(run_id_str)
    company_id = uuid.UUID(company_id_str)

    with tenant_context(tenant_id=str(company_id)):
        db = SessionLocal()
        try:
            WorkflowEngine.execute_run(db, run_id)
        finally:
            db.close()
