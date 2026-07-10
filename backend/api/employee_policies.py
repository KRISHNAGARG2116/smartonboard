import uuid
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from api.deps import RequireEmployee, EmployeeDb
from models.employees import Employee
from models.employee_policy_acknowledgement import EmployeePolicyAcknowledgement
from models.employee_onboarding_audit import EmployeeOnboardingAudit
from db.session import tenant_context

router = APIRouter(prefix="/employee/policies", tags=["Employee Policies"])

class PolicyAcknowledgeSubmit(BaseModel):
    digital_signature: str = Field(..., min_length=2, description="Signee's typed full name")
    policy_version: str = Field(default="1.0")

@router.get("")
def list_company_policies(
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """List company policies and their current acknowledgement status for the employee."""
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    acknowledgements = db.scalars(
        select(EmployeePolicyAcknowledgement).where(EmployeePolicyAcknowledgement.employee_id == employee.id)
    ).all()

    signed_map = {ack.policy_name: ack for ack in acknowledgements}

    policies = [
        {"name": "security_policy", "title": "Information Security Policy", "version": "1.0", "content": "All employees must lock screens when leaving desks, use two-factor authentication, and report phishing attempts immediately."},
        {"name": "code_of_conduct", "title": "Corporate Code of Conduct", "version": "1.0", "content": "We foster a respectful, inclusive, and professional environment. Harassment, discrimination, and unethical business actions are strictly prohibited."},
        {"name": "remote_work_policy", "title": "Remote Work Guidelines", "version": "1.2", "content": "Remote employees must maintain secure, private workspaces, separate personal computing from work assets, and adhere to core hours."},
    ]

    results = []
    for pol in policies:
        ack = signed_map.get(pol["name"])
        results.append({
            "policy_name": pol["name"],
            "title": pol["title"],
            "version": pol["version"],
            "content": pol["content"],
            "is_acknowledged": ack is not None,
            "acknowledged_at": ack.acknowledged_at.isoformat() if ack else None,
            "digital_signature": ack.digital_signature if ack else None,
        })

    return results


@router.post("/{policy_name}/acknowledge")
def acknowledge_policy(
    policy_name: str,
    body: PolicyAcknowledgeSubmit,
    request: Request,
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """Digitally sign and acknowledge a company compliance policy."""
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    valid_policy_names = ["security_policy", "code_of_conduct", "remote_work_policy", "privacy_policy", "acceptable_use"]
    if policy_name not in valid_policy_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid policy name: {policy_name}",
        )

    # Check if already signed
    existing = db.scalar(
        select(EmployeePolicyAcknowledgement).where(
            EmployeePolicyAcknowledgement.employee_id == employee.id,
            EmployeePolicyAcknowledgement.policy_name == policy_name,
            EmployeePolicyAcknowledgement.policy_version == body.policy_version,
        )
    )
    if existing:
        return {"status": "already_acknowledged", "acknowledged_at": existing.acknowledged_at.isoformat()}

    ip = request.client.host if request.client else "127.0.0.1"
    ua = request.headers.get("user-agent", "unknown")

    ack = EmployeePolicyAcknowledgement(
        company_id=employee.company_id,
        employee_id=employee.id,
        policy_name=policy_name,
        policy_version=body.policy_version,
        ip_address=ip,
        user_agent=ua,
        digital_signature=body.digital_signature,
    )
    db.add(ack)

    # Log audit
    audit = EmployeeOnboardingAudit(
        company_id=employee.company_id,
        employee_id=employee.id,
        actor_id=current_employee.id,
        actor_type="employee",
        action="Policy Acknowledged",
        details={"policy_name": policy_name, "version": body.policy_version},
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "policy_name": policy_name,
        "acknowledged_at": ack.acknowledged_at.isoformat(),
    }
