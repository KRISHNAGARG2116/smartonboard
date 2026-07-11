import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import RequireEmployee, EmployeeDb
from models.employees import Employee
from models.employee_provisioning_request import EmployeeProvisioningRequest
from db.session import tenant_context

router = APIRouter(prefix="/employee/provisioning", tags=["Employee Provisioning"])

@router.get("")
def list_provisioning_requests(
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """Retrieve IT provisioning accounts and status (Email, Slack, GitHub, VPN, etc.)."""
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    requests = db.scalars(
        select(EmployeeProvisioningRequest).where(EmployeeProvisioningRequest.employee_id == employee.id)
    ).all()

    # Create lookup map
    request_map = {r.id: r for r in requests}

    results = []
    for r in requests:
        dep_service = None
        dep_status = None
        if r.depends_on_provisioning_id:
            dep_req = request_map.get(r.depends_on_provisioning_id)
            if dep_req:
                dep_service = dep_req.service_name
                dep_status = dep_req.status

        results.append({
            "id": str(r.id),
            "service_name": r.service_name,
            "account_username": r.account_username,
            "status": r.status,
            "notes": r.notes,
            "depends_on_service": dep_service,
            "depends_on_status": dep_status,
        })

    return results
