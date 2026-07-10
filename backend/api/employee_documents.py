import uuid
import hashlib
from datetime import datetime, timezone
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from api.deps import RequireEmployee, EmployeeDb
from models.employees import Employee
from models.employee_document import EmployeeDocument
from models.employee_onboarding_audit import EmployeeOnboardingAudit
from db.session import tenant_context

router = APIRouter(prefix="/employee/documents", tags=["Employee Document Vault"])

class DocumentSignSubmit(BaseModel):
    signature_svg_or_text: str = Field(..., description="E-signature SVG path data or typed name")

@router.get("")
def list_vault_documents(
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """Retrieve lists of files in the employee document vault (NDAs, tax forms, visas, handbooks)."""
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    docs = db.scalars(
        select(EmployeeDocument).where(EmployeeDocument.employee_id == employee.id)
    ).all()

    return docs


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_vault_document(
    request: Request,
    current_employee: RequireEmployee,
    db: EmployeeDb,
    document_type: str = Form(..., description="offer_letter, nda, tax_form, id_proof, visa, handbook, insurance, custom"),
    document_name: str = Form(...),
    document_version: str = Form("1.0"),
    file: UploadFile = File(...),
):
    """Upload a new document file to the employee's vault, calculating SHA-256 checksum and metadata."""
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    # Read file and calculate SHA256 checksum
    content = await file.read()
    checksum = hashlib.sha256(content).hexdigest()

    # Determine a mock storage key path
    storage_key = f"vault/{employee.id}/{uuid.uuid4()}_{file.filename}"

    doc = EmployeeDocument(
        company_id=employee.company_id,
        employee_id=employee.id,
        document_type=document_type,
        document_name=document_name,
        document_version=document_version,
        checksum=checksum,
        uploaded_by_id=current_employee.id,
        storage_key=storage_key,
    )
    db.add(doc)

    # Log audit
    audit = EmployeeOnboardingAudit(
        company_id=employee.company_id,
        employee_id=employee.id,
        actor_id=current_employee.id,
        actor_type="employee",
        action="Document Uploaded",
        details={"document_type": document_type, "document_name": document_name},
    )
    db.add(audit)
    db.commit()
    db.refresh(doc)

    return doc


@router.post("/{document_id}/sign")
def sign_vault_document(
    document_id: uuid.UUID,
    body: DocumentSignSubmit,
    request: Request,
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """Digitally e-sign an onboarding document in the vault, generating an audit-ready hash."""
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    doc = db.scalar(
        select(EmployeeDocument).where(
            EmployeeDocument.id == document_id,
            EmployeeDocument.employee_id == employee.id,
        )
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if doc.signed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is already signed.",
        )

    ip = request.client.host if request.client else "127.0.0.1"
    ua = request.headers.get("user-agent", "unknown")

    # Generate an audit-ready signed hash using document checksum + signature content
    hash_input = f"{doc.checksum}:{body.signature_svg_or_text}:{ip}:{ua}:{datetime.now(timezone.utc).isoformat()}"
    signed_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    doc.signed_at = datetime.now(timezone.utc)
    doc.signed_hash = signed_hash
    doc.signature_svg_or_text = body.signature_svg_or_text
    doc.ip_address = ip
    doc.user_agent = ua
    db.add(doc)

    # Log audit
    audit = EmployeeOnboardingAudit(
        company_id=employee.company_id,
        employee_id=employee.id,
        actor_id=current_employee.id,
        actor_type="employee",
        action="NDA Signed" if doc.document_type == "nda" else "Document Signed",
        details={"document_id": str(doc.id), "document_name": doc.document_name},
    )
    db.add(audit)
    db.commit()
    db.refresh(doc)

    return doc
