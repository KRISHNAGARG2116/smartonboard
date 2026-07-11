import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from api.deps import RequireEmployee, EmployeeDb
from models.employees import Employee
from models.employee_equipment_request import EmployeeEquipmentRequest
from models.employee_onboarding_audit import EmployeeOnboardingAudit
from db.session import tenant_context

router = APIRouter(prefix="/employee/equipment", tags=["Employee Equipment"])

class EquipmentRequestCreate(BaseModel):
    item_type: str = Field(..., description="laptop, monitor, phone, access_card, software, accessories")
    item_name: str = Field(..., min_length=2, max_length=255)
    notes: str | None = None

class EquipmentRequestUpdate(BaseModel):
    item_name: str = Field(..., min_length=2, max_length=255)
    notes: str | None = None

@router.get("")
def list_equipment_requests(
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """List all equipment requests submitted by or for the employee."""
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    requests = db.scalars(
        select(EmployeeEquipmentRequest).where(EmployeeEquipmentRequest.employee_id == employee.id)
    ).all()

    return requests


@router.post("", status_code=status.HTTP_201_CREATED)
def create_equipment_request(
    body: EquipmentRequestCreate,
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """Submit a new equipment request (e.g., specifying laptop configurations)."""
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    request = EmployeeEquipmentRequest(
        company_id=employee.company_id,
        employee_id=employee.id,
        item_type=body.item_type,
        item_name=body.item_name,
        status="requested",
        notes=body.notes,
    )
    db.add(request)

    # Log audit
    audit = EmployeeOnboardingAudit(
        company_id=employee.company_id,
        employee_id=employee.id,
        actor_id=current_employee.id,
        actor_type="employee",
        action="Laptop Ordered" if body.item_type == "laptop" else "Equipment Requested",
        details={"item_type": body.item_type, "item_name": body.item_name},
    )
    db.add(audit)
    db.commit()
    db.refresh(request)

    return request


@router.put("/{request_id}")
def update_equipment_request(
    request_id: uuid.UUID,
    body: EquipmentRequestUpdate,
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """Modify an existing equipment request, allowed only if it is still in the 'requested' stage."""
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    request = db.scalar(
        select(EmployeeEquipmentRequest).where(
            EmployeeEquipmentRequest.id == request_id,
            EmployeeEquipmentRequest.employee_id == employee.id,
        )
    )
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment request not found.",
        )

    if request.status != "requested":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update equipment request after it has been approved/processed.",
        )

    request.item_name = body.item_name
    request.notes = body.notes
    db.add(request)
    db.commit()
    db.refresh(request)

    return request
