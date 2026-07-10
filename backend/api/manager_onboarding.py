import uuid
from datetime import datetime, date, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from api.deps import CurrentUser, TenantDb
from models import User
from models.employees import Employee, OnboardingTask
from models.employee_onboarding import EmployeeOnboarding
from models.employee_equipment_request import EmployeeEquipmentRequest
from models.employee_provisioning_request import EmployeeProvisioningRequest
from models.employee_buddy_assignment import EmployeeBuddyAssignment
from models.employee_onboarding_audit import EmployeeOnboardingAudit

router = APIRouter(prefix="/manager/onboarding", tags=["Manager Onboarding Workspace"])

class ApproveRejectRequest(BaseModel):
    decision: str = Field(..., description="approve, decline")
    notes: str | None = None

class AssignBuddyRequest(BaseModel):
    employee_id: uuid.UUID
    buddy_id: uuid.UUID

@router.get("/new-hires")
def list_manager_new_hires(
    current_user: CurrentUser,
    db: TenantDb,
):
    """List onboarding employees supervised by the manager."""
    # Find manager employee record matching user
    manager = db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.email == current_user.email,
        )
    )
    if not manager:
        return []

    # Get subordinates in onboarding
    new_hires = db.scalars(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.supervisor_id == manager.id,
            Employee.status == "onboarding",
        )
    ).all()

    results = []
    for hire in new_hires:
        onboarding = db.scalar(
            select(EmployeeOnboarding).where(EmployeeOnboarding.employee_id == hire.id)
        )
        # Calculate dynamic progress
        total_required = db.scalar(
            select(sa_count(OnboardingTask.id))
            .where(OnboardingTask.workflow_id == hire.id, OnboardingTask.is_optional.is_(False))
        ) or 0
        completed_required = db.scalar(
            select(sa_count(OnboardingTask.id))
            .where(OnboardingTask.workflow_id == hire.id, OnboardingTask.is_optional.is_(False), OnboardingTask.status == "completed")
        ) or 0
        progress = int(completed_required / total_required * 100) if total_required > 0 else 0

        results.append({
            "id": str(hire.id),
            "full_name": hire.full_name,
            "email": hire.email,
            "job_title": hire.job_title,
            "department": hire.department,
            "start_date": hire.start_date.isoformat(),
            "progress_percentage": progress,
            "onboarding_status": onboarding.status if onboarding else "pending",
        })

    return results


@router.get("/approvals")
def list_pending_approvals(
    current_user: CurrentUser,
    db: TenantDb,
):
    """Retrieve pending hardware and software provisioning requests for the manager's team."""
    manager = db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.email == current_user.email,
        )
    )
    if not manager:
        return {"equipment": [], "provisioning": []}

    sub_ids = db.scalars(
        select(Employee.id).where(
            Employee.company_id == current_user.company_id,
            Employee.supervisor_id == manager.id,
        )
    ).all()

    if not sub_ids:
        return {"equipment": [], "provisioning": []}

    equipment = db.scalars(
        select(EmployeeEquipmentRequest).where(
            EmployeeEquipmentRequest.company_id == current_user.company_id,
            EmployeeEquipmentRequest.employee_id.in_(sub_ids),
            EmployeeEquipmentRequest.status == "requested",
        )
    ).all()

    provisioning = db.scalars(
        select(EmployeeProvisioningRequest).where(
            EmployeeProvisioningRequest.company_id == current_user.company_id,
            EmployeeProvisioningRequest.employee_id.in_(sub_ids),
            EmployeeProvisioningRequest.status == "pending",
        )
    ).all()

    return {
        "equipment": [
            {
                "id": str(eq.id),
                "employee_id": str(eq.employee_id),
                "item_type": eq.item_type,
                "item_name": eq.item_name,
                "notes": eq.notes,
            }
            for eq in equipment
        ],
        "provisioning": [
            {
                "id": str(pr.id),
                "employee_id": str(pr.employee_id),
                "service_name": pr.service_name,
                "notes": pr.notes,
            }
            for pr in provisioning
        ],
    }


@router.post("/approvals/{req_type}/{req_id}/resolve")
def resolve_pending_approval(
    req_type: str,
    req_id: uuid.UUID,
    body: ApproveRejectRequest,
    current_user: CurrentUser,
    db: TenantDb,
):
    """Resolve (approve/decline) pending hardware/software request."""
    if req_type not in ["equipment", "provisioning"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request type. Must be 'equipment' or 'provisioning'.",
        )

    # Verify authorization (supervisor verification)
    manager = db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.email == current_user.email,
        )
    )
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only supervisors are permitted to resolve team approvals.",
        )

    if req_type == "equipment":
        req = db.scalar(
            select(EmployeeEquipmentRequest).where(
                EmployeeEquipmentRequest.id == req_id,
                EmployeeEquipmentRequest.company_id == current_user.company_id,
            )
        )
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
        
        # Check supervisor relation
        emp = db.scalar(select(Employee).where(Employee.id == req.employee_id))
        if not emp or emp.supervisor_id != manager.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized.")

        req.status = "approved" if body.decision == "approve" else "retired"
        req.notes = f"Manager notes: {body.notes}" if body.notes else req.notes
        db.add(req)

        # Log audit
        audit = EmployeeOnboardingAudit(
            company_id=req.company_id,
            employee_id=req.employee_id,
            actor_id=current_user.id,
            actor_type="manager",
            action="Laptop Ordered" if body.decision == "approve" else "Equipment Rejected",
            details={"equipment_id": str(req.id), "decision": body.decision},
        )
        db.add(audit)

    else:
        req = db.scalar(
            select(EmployeeProvisioningRequest).where(
                EmployeeProvisioningRequest.id == req_id,
                EmployeeProvisioningRequest.company_id == current_user.company_id,
            )
        )
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
        
        emp = db.scalar(select(Employee).where(Employee.id == req.employee_id))
        if not emp or emp.supervisor_id != manager.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized.")

        req.status = "approved" if body.decision == "approve" else "failed"
        req.notes = f"Manager notes: {body.notes}" if body.notes else req.notes
        db.add(req)

        audit = EmployeeOnboardingAudit(
            company_id=req.company_id,
            employee_id=req.employee_id,
            actor_id=current_user.id,
            actor_type="manager",
            action="GitHub Provisioned" if req.service_name == "github" and body.decision == "approve" else "Provisioning Resolved",
            details={"provisioning_id": str(req.id), "decision": body.decision},
        )
        db.add(audit)

    db.commit()
    return {"status": "success", "message": f"Request {body.decision}d successfully."}


@router.post("/assign-buddy")
def assign_onboarding_buddy(
    body: AssignBuddyRequest,
    current_user: CurrentUser,
    db: TenantDb,
):
    """Assign an onboarding buddy to a new hire."""
    # Verify employee and buddy exist
    employee = db.scalar(
        select(Employee).where(
            Employee.id == body.employee_id,
            Employee.company_id == current_user.company_id,
        )
    )
    buddy = db.scalar(
        select(Employee).where(
            Employee.id == body.buddy_id,
            Employee.company_id == current_user.company_id,
        )
    )
    if not employee or not buddy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee or Buddy not found.",
        )

    # Create buddy assignment
    assignment = EmployeeBuddyAssignment(
        company_id=current_user.company_id,
        employee_id=employee.id,
        buddy_id=buddy.id,
        status="assigned",
    )
    db.add(assignment)

    # Log audit
    audit = EmployeeOnboardingAudit(
        company_id=employee.company_id,
        employee_id=employee.id,
        actor_id=current_user.id,
        actor_type="manager",
        action="Buddy Assigned",
        details={"buddy_id": str(buddy.id), "buddy_name": buddy.full_name},
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "message": f"Buddy {buddy.full_name} assigned successfully."}


@router.get("/overdue-tasks")
def list_overdue_tasks(
    current_user: CurrentUser,
    db: TenantDb,
):
    """List overdue tasks for subordinates."""
    manager = db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.email == current_user.email,
        )
    )
    if not manager:
        return []

    sub_ids = db.scalars(
        select(Employee.id).where(
            Employee.company_id == current_user.company_id,
            Employee.supervisor_id == manager.id,
        )
    ).all()

    if not sub_ids:
        return []

    # Overdue tasks: status != completed and due_date < current date
    today = date.today()
    overdue_tasks = db.scalars(
        select(OnboardingTask).where(
            OnboardingTask.company_id == current_user.company_id,
            OnboardingTask.workflow_id.in_(sub_ids),
            OnboardingTask.status != "completed",
            OnboardingTask.due_date < today,
        )
    ).all()

    results = []
    for task in overdue_tasks:
        emp = db.scalar(select(Employee).where(Employee.id == task.workflow_id))
        results.append({
            "task_id": str(task.id),
            "title": task.title,
            "due_date": task.due_date.isoformat(),
            "new_hire": {
                "id": str(emp.id),
                "full_name": emp.full_name,
                "email": emp.email,
            } if emp else None,
        })

    return results


def sa_count(col):
    from sqlalchemy import func
    return func.count(col)
