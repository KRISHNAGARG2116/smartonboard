import uuid
import io
from datetime import datetime, date, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from db.session import tenant_context
from models import User, Company
from models.enums import UserRole
from models.employees import Employee
from models.employee_document import EmployeeDocument
from models.employee_policy_acknowledgement import EmployeePolicyAcknowledgement
from core.security import create_access_token
from server import app

@pytest.fixture
def db_session_test(db_engine):
    """Create a scoped test database session and override app dependencies."""
    from sqlalchemy.orm import Session
    from api.deps import get_db, get_employee_db, get_tenant_db
    
    db = Session(db_engine)
    
    def override_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_employee_db] = override_db
    app.dependency_overrides[get_tenant_db] = override_db
    
    yield db
    
    app.dependency_overrides.clear()
    db.close()

@pytest.fixture
def signature_setup(db_session_test):
    """Seed test company, employee."""
    db = db_session_test
    
    with tenant_context(auth_mode="true"):
        company = Company(name="Test Corp Sign Pol", slug="test-corp-sign-pol", status="active")
        db.add(company)
        db.flush()

        employee_user = User(
            company_id=company.id,
            email="newhire_sign@testcorpsign.com",
            password_hash="hash",
            full_name="New Hire Alice",
            role=UserRole.EMPLOYEE,
            email_verified=True,
        )
        db.add(employee_user)
        db.flush()

        employee = Employee(
            company_id=company.id,
            email="newhire_sign@testcorpsign.com",
            full_name="New Hire Alice",
            job_title="Software Engineer",
            department="Engineering",
            employment_type="full_time",
            status="onboarding",
            start_date=date.today() + timedelta(days=14),
            user_id=employee_user.id,
        )
        db.add(employee)
        db.flush()

        # Generate token
        employee_token = create_access_token(
            str(employee_user.id),
            {"company_id": str(company.id), "role": "employee", "email": employee_user.email}
        )

        yield {
            "company_id": company.id,
            "employee_user_id": employee_user.id,
            "employee_id": employee.id,
            "employee_token": employee_token,
        }

        # Cleanup
        db.query(EmployeeDocument).filter(EmployeeDocument.employee_id == employee.id).delete()
        db.query(EmployeePolicyAcknowledgement).filter(EmployeePolicyAcknowledgement.employee_id == employee.id).delete()
        db.delete(employee)
        db.delete(employee_user)
        db.delete(company)
        db.commit()


def test_policy_read_and_acknowledgements(signature_setup):
    """Test retrieving policies list and acknowledging/signing compliance policies."""
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {signature_setup['employee_token']}"}

    # 1. Get policies list
    response = client.get("/api/v1/employee/policies", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["is_acknowledged"] is False

    # 2. Sign policy
    response = client.post(
        "/api/v1/employee/policies/security_policy/acknowledge",
        json={"digital_signature": "New Hire Alice", "policy_version": "1.0"},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # 3. Verify status update
    response = client.get("/api/v1/employee/policies", headers=headers)
    assert response.status_code == 200
    assert response.json()[0]["is_acknowledged"] is True
    assert response.json()[0]["digital_signature"] == "New Hire Alice"


def test_document_vault_uploads_and_esignatures(signature_setup):
    """Test uploading doc to centralized vault, verifying checksums, and digitally signing a document."""
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {signature_setup['employee_token']}"}

    # 1. Upload document (NDA)
    file_content = b"This is a test NDA document content."
    file_io = io.BytesIO(file_content)
    
    response = client.post(
        "/api/v1/employee/documents/upload",
        data={
            "document_type": "nda",
            "document_name": "Mutual Non-Disclosure Agreement",
            "document_version": "1.0",
        },
        files={"file": ("nda_file.pdf", file_io, "application/pdf")},
        headers=headers
    )
    assert response.status_code == 201
    doc = response.json()
    assert doc["document_type"] == "nda"
    assert doc["checksum"] is not None
    assert doc["signed_hash"] is None  # not signed yet

    # 2. List documents
    response = client.get("/api/v1/employee/documents", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    # 3. E-sign document in the vault
    response = client.post(
        f"/api/v1/employee/documents/{doc['id']}/sign",
        json={"signature_svg_or_text": "New Hire Alice"},
        headers=headers
    )
    assert response.status_code == 200
    signed_doc = response.json()
    assert signed_doc["signed_at"] is not None
    assert signed_doc["signed_hash"] is not None
    assert signed_doc["signature_svg_or_text"] == "New Hire Alice"
