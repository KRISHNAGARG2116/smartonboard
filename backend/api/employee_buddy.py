import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from api.deps import RequireEmployee, EmployeeDb
from models.employees import Employee
from models.employee_buddy_assignment import EmployeeBuddyAssignment
from models.employee_onboarding_audit import EmployeeOnboardingAudit
from db.session import tenant_context

router = APIRouter(prefix="/employee/buddy", tags=["Employee Buddy"])

class BuddyFeedbackSubmit(BaseModel):
    feedback: str = Field(..., min_length=2, description="Onboarding buddy feedback comments")

@router.get("")
def get_buddy_details(
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """Retrieve details of the assigned onboarding buddy."""
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    assignment = db.scalar(
        select(EmployeeBuddyAssignment).where(
            EmployeeBuddyAssignment.employee_id == employee.id,
            EmployeeBuddyAssignment.status.in_(["assigned", "accepted", "completed"]),
        )
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No onboarding buddy assigned yet.",
        )

    buddy_emp = db.scalar(
        select(Employee).where(Employee.id == assignment.buddy_id)
    )
    if not buddy_emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Buddy employee profile not found.",
        )

    return {
        "id": str(assignment.id),
        "buddy_id": str(buddy_emp.id),
        "full_name": buddy_emp.full_name,
        "email": buddy_emp.email,
        "phone": buddy_emp.phone,
        "job_title": buddy_emp.job_title,
        "department": buddy_emp.department,
        "status": assignment.status,
        "buddy_feedback": assignment.buddy_feedback,
        "employee_feedback": assignment.employee_feedback,
    }


@router.post("/feedback")
def submit_buddy_feedback(
    body: BuddyFeedbackSubmit,
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """Submit evaluation and feedback regarding the buddy match."""
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    assignment = db.scalar(
        select(EmployeeBuddyAssignment).where(
            EmployeeBuddyAssignment.employee_id == employee.id,
            EmployeeBuddyAssignment.status.in_(["assigned", "accepted"]),
        )
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active buddy assignment found.",
        )

    assignment.employee_feedback = body.feedback
    assignment.status = "completed"
    db.add(assignment)

    # Log audit
    audit = EmployeeOnboardingAudit(
        company_id=employee.company_id,
        employee_id=employee.id,
        actor_id=current_employee.id,
        actor_type="employee",
        action="Buddy Feedback Submitted",
        details={"buddy_assignment_id": str(assignment.id)},
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "message": "Feedback submitted successfully."}
