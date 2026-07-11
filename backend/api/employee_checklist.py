import uuid
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from api.deps import RequireEmployee, EmployeeDb
from models.employees import OnboardingTask, Employee, OnboardingWorkflow
from models.onboarding_task_dependencies import OnboardingTaskDependency
from models.employee_onboarding import EmployeeOnboarding
from models.employee_onboarding_audit import EmployeeOnboardingAudit
from db.session import tenant_context

router = APIRouter(prefix="/employee/checklist", tags=["Employee Checklist"])

@router.get("")
def get_employee_checklist(
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """Retrieve the employee's onboarding tasks grouped by phase, including dependency information."""
    # Find employee profile
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    # Find active workflow
    workflow = db.scalar(
        select(OnboardingWorkflow).where(OnboardingWorkflow.employee_id == employee.id)
    )
    if not workflow:
        return {
            "preboarding": [],
            "day_1": [],
            "week_1": [],
            "month_1": [],
            "month_3": [],
        }

    # Fetch all tasks for this employee workflow
    tasks = db.scalars(
        select(OnboardingTask)
        .where(OnboardingTask.workflow_id == workflow.id)
        .order_by(OnboardingTask.sequence.asc())
    ).all()

    # Build a lookup dictionary of tasks by ID
    task_map = {task.id: task for task in tasks}

    # Fetch all dependencies for these tasks
    task_ids = [task.id for task in tasks]
    dependencies = []
    if task_ids:
        dependencies = db.scalars(
            select(OnboardingTaskDependency).where(OnboardingTaskDependency.task_id.in_(task_ids))
        ).all()

    # Group dependencies by task_id
    dep_map = {}
    for dep in dependencies:
        dep_map.setdefault(dep.task_id, []).append(dep.depends_on_task_id)

    # Structure tasks with dependency and blocked status
    structured_tasks = []
    for task in tasks:
        prereqs = dep_map.get(task.id, [])
        prereq_details = []
        is_blocked = False

        for prereq_id in prereqs:
            prereq_task = task_map.get(prereq_id)
            if prereq_task:
                prereq_details.append({
                    "id": str(prereq_task.id),
                    "title": prereq_task.title,
                    "status": prereq_task.status,
                })
                if prereq_task.status != "completed":
                    is_blocked = True

        structured_tasks.append({
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "phase": task.phase,
            "is_optional": task.is_optional,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "prerequisites": prereq_details,
            "is_blocked": is_blocked,
        })

    # Group by phase: preboarding, day_1, week_1, month_1, month_3
    phases = {
        "preboarding": [],
        "day_1": [],
        "week_1": [],
        "month_1": [],
        "month_3": [],
    }
    for st in structured_tasks:
        phase = st["phase"]
        if phase in phases:
            phases[phase].append(st)
        else:
            phases.setdefault(phase, []).append(st)

    return phases


@router.post("/{task_id}/complete")
def complete_checklist_task(
    task_id: uuid.UUID,
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """Mark an onboarding checklist task as complete after validating all prerequisites."""
    # Find employee profile
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    # Find active workflow
    workflow = db.scalar(
        select(OnboardingWorkflow).where(OnboardingWorkflow.employee_id == employee.id)
    )
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active onboarding workflow not found.",
        )

    # Fetch task and confirm ownership
    task = db.scalar(
        select(OnboardingTask).where(
            OnboardingTask.id == task_id,
            OnboardingTask.workflow_id == workflow.id,
        )
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding task not found.",
        )

    if task.status == "completed":
        return {"status": "already_completed", "task_id": str(task.id)}

    # Verify all dependencies are completed
    dependencies = db.scalars(
        select(OnboardingTaskDependency).where(OnboardingTaskDependency.task_id == task.id)
    ).all()
    
    unfinished_prereqs = []
    for dep in dependencies:
        prereq_task = db.scalar(
            select(OnboardingTask).where(OnboardingTask.id == dep.depends_on_task_id)
        )
        if prereq_task and prereq_task.status != "completed":
            unfinished_prereqs.append(prereq_task.title)

    if unfinished_prereqs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This task is blocked by unfinished prerequisites: {', '.join(unfinished_prereqs)}",
        )

    # Complete the task
    task.status = "completed"
    task.completed_at = datetime.now(timezone.utc)
    task.completed_by_id = current_employee.id
    db.add(task)

    # Log audit event
    audit_log = EmployeeOnboardingAudit(
        company_id=employee.company_id,
        employee_id=employee.id,
        actor_id=current_employee.id,
        actor_type="employee",
        action="Task Completed",
        details={"task_id": str(task.id), "task_title": task.title},
    )
    db.add(audit_log)
    db.flush()

    # Recalculate progress to check if 100% complete
    total_required = db.scalar(
        select(func.count(OnboardingTask.id))
        .where(
            OnboardingTask.workflow_id == workflow.id,
            OnboardingTask.is_optional.is_(False),
        )
    ) or 0
    completed_required = db.scalar(
        select(func.count(OnboardingTask.id))
        .where(
            OnboardingTask.workflow_id == workflow.id,
            OnboardingTask.is_optional.is_(False),
            OnboardingTask.status == "completed",
        )
    ) or 0

    onboarding = db.scalar(
        select(EmployeeOnboarding).where(EmployeeOnboarding.employee_id == employee.id)
    )

    if total_required > 0 and completed_required == total_required:
        if onboarding and onboarding.status != "completed":
            onboarding.status = "completed"
            onboarding.completed_at = datetime.now(timezone.utc)
            db.add(onboarding)

            # Log final onboarding completed audit
            completion_audit = EmployeeOnboardingAudit(
                company_id=employee.company_id,
                employee_id=employee.id,
                actor_id=None,
                actor_type="system",
                action="Onboarding Finished",
                details={"completed_at": onboarding.completed_at.isoformat()},
            )
            db.add(completion_audit)

            # Notify manager & HR (simulated notifications)
            notification_text = f"Onboarding completed successfully for {employee.full_name}!"
            # We can create a system notification row in the database or trigger hooks
            from models.ats_models import Notification
            if employee.supervisor_id:
                supervisor = db.scalar(select(Employee).where(Employee.id == employee.supervisor_id))
                if supervisor and supervisor.user_id:
                    notif = Notification(
                        company_id=employee.company_id,
                        user_id=supervisor.user_id,
                        title="Onboarding Completed",
                        message=notification_text,
                        type="offer",
                    )
                    db.add(notif)

    db.commit()

    return {
        "status": "success",
        "task_id": str(task.id),
        "completed_at": task.completed_at.isoformat(),
        "onboarding_status": onboarding.status if onboarding else "pending",
    }
