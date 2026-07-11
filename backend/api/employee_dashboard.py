import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from api.deps import RequireEmployee, EmployeeDb
from models.employee_onboarding import EmployeeOnboarding
from models.employee_equipment_request import EmployeeEquipmentRequest
from models.employee_provisioning_request import EmployeeProvisioningRequest
from models.employee_buddy_assignment import EmployeeBuddyAssignment
from models.employee_welcome_event import EmployeeWelcomeEvent
from models.employee_onboarding_audit import EmployeeOnboardingAudit
from models.employees import OnboardingTask, Employee, OnboardingWorkflow
from db.session import tenant_context

router = APIRouter(prefix="/employee/dashboard", tags=["Employee Dashboard"])

@router.get("")
def get_employee_dashboard(
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """Retrieve detailed onboarding stats and state for the authenticated employee."""
    # Find employee profile
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found for user.",
        )

    # 1. Onboarding overview
    onboarding = db.scalar(
        select(EmployeeOnboarding).where(EmployeeOnboarding.employee_id == employee.id)
    )
    
    # Find active workflow
    workflow = db.scalar(
        select(OnboardingWorkflow).where(OnboardingWorkflow.employee_id == employee.id)
    )
    workflow_id = workflow.id if workflow else None
    
    # Calculate progress percentage dynamically: Completed Required Tasks / Total Required Tasks
    # If no tasks exist, return 0.
    total_required = db.scalar(
        select(func.count(OnboardingTask.id))
        .where(
            OnboardingTask.workflow_id == workflow_id,
            OnboardingTask.is_optional.is_(False),
        )
    ) or 0 if workflow_id else 0
    completed_required = db.scalar(
        select(func.count(OnboardingTask.id))
        .where(
            OnboardingTask.workflow_id == workflow_id,
            OnboardingTask.is_optional.is_(False),
            OnboardingTask.status == "completed",
        )
    ) or 0 if workflow_id else 0
    
    progress_percentage = int((completed_required / total_required * 100)) if total_required > 0 else 0

    # 2. Buddy Details
    buddy_assignment = db.scalar(
        select(EmployeeBuddyAssignment).where(
            EmployeeBuddyAssignment.employee_id == employee.id,
            EmployeeBuddyAssignment.status.in_(["assigned", "accepted"]),
        )
    )
    buddy_info = None
    if buddy_assignment:
        buddy_emp = db.scalar(
            select(Employee).where(Employee.id == buddy_assignment.buddy_id)
        )
        if buddy_emp:
            buddy_info = {
                "id": str(buddy_emp.id),
                "full_name": buddy_emp.full_name,
                "email": buddy_emp.email,
                "job_title": buddy_emp.job_title,
                "status": buddy_assignment.status,
            }

    # 3. Equipment Requests
    equipment_requests = db.scalars(
        select(EmployeeEquipmentRequest).where(EmployeeEquipmentRequest.employee_id == employee.id)
    ).all()
    equipment_summary = [
        {
            "id": str(eq.id),
            "item_type": eq.item_type,
            "item_name": eq.item_name,
            "status": eq.status,
            "notes": eq.notes,
        }
        for eq in equipment_requests
    ]

    # 4. IT Provisioning Status
    provisioning_requests = db.scalars(
        select(EmployeeProvisioningRequest).where(EmployeeProvisioningRequest.employee_id == employee.id)
    ).all()
    provisioning_summary = [
        {
            "id": str(pr.id),
            "service_name": pr.service_name,
            "account_username": pr.account_username,
            "status": pr.status,
            "notes": pr.notes,
            "depends_on_provisioning_id": str(pr.depends_on_provisioning_id) if pr.depends_on_provisioning_id else None,
        }
        for pr in provisioning_requests
    ]

    # 5. Welcome Schedule & Reviews
    welcome_events = db.scalars(
        select(EmployeeWelcomeEvent)
        .where(EmployeeWelcomeEvent.employee_id == employee.id)
        .order_by(EmployeeWelcomeEvent.scheduled_at.asc())
    ).all()
    events_summary = [
        {
            "id": str(ev.id),
            "event_name": ev.event_name,
            "description": ev.description,
            "scheduled_at": ev.scheduled_at.isoformat(),
            "duration_minutes": ev.duration_minutes,
            "meeting_link": ev.meeting_link,
        }
        for ev in welcome_events
    ]

    # 6. Immutable Timeline (Audits)
    audit_logs = db.scalars(
        select(EmployeeOnboardingAudit)
        .where(EmployeeOnboardingAudit.employee_id == employee.id)
        .order_by(EmployeeOnboardingAudit.created_at.asc())
    ).all()
    timeline = [
        {
            "id": str(log.id),
            "action": log.action,
            "actor_type": log.actor_type,
            "created_at": log.created_at.isoformat(),
            "details": log.details,
        }
        for log in audit_logs
    ]

    # Assemble and return dashboard details
    return {
        "employee": {
            "id": str(employee.id),
            "full_name": employee.full_name,
            "job_title": employee.job_title,
            "department": employee.department,
            "start_date": employee.start_date.isoformat(),
            "status": employee.status,
        },
        "onboarding": {
            "status": onboarding.status if onboarding else "pending",
            "progress_percentage": progress_percentage,
            "template_name": onboarding.template_name if onboarding else None,
            "template_version": onboarding.template_version if onboarding else None,
        },
        "buddy": buddy_info,
        "equipment": equipment_summary,
        "provisioning": provisioning_summary,
        "welcome_events": events_summary,
        "timeline": timeline,
    }
