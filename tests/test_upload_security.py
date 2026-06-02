import io
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from server import app, storage_service
from db.session import get_db

@pytest.fixture
def api_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_valid_pdf_accepted(api_client):
    """Verify that a valid PDF file structure is successfully accepted and screened."""
    valid_pdf_data = b"%PDF-1.4\n%%EOF"
    files = {"file": ("resume.pdf", valid_pdf_data, "application/pdf")}
    data = {"job_role": "Software Engineer"}

    with patch("celery_worker.scan_and_promote_resume_task.delay") as mock_celery_task:
        mock_task_instance = MagicMock()
        mock_task_instance.id = "mocked-task-id-123"
        mock_celery_task.return_value = mock_task_instance
        
        response = api_client.post("/api/screen/upload", files=files, data=data)
        assert response.status_code == 202
        res_data = response.json()
        assert res_data["task_id"] == "mocked-task-id-123"
        assert "quarantine_file_id" in res_data
        assert res_data["status"] == "PENDING"
        mock_celery_task.assert_called_once()


def test_valid_docx_accepted(api_client):
    """Verify that a valid DOCX signature and structure is successfully accepted."""
    import zipfile
    docx_io = io.BytesIO()
    with zipfile.ZipFile(docx_io, "w") as z:
        z.writestr("word/document.xml", "<w:document><w:body><w:p><w:r><w:t>Resume</w:t></w:r></w:p></w:body></w:document>")
    valid_docx_data = docx_io.getvalue()
    
    files = {"file": ("resume.docx", valid_docx_data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    data = {"job_role": "Software Engineer"}

    with patch("celery_worker.scan_and_promote_resume_task.delay") as mock_celery_task:
        mock_task_instance = MagicMock()
        mock_task_instance.id = "mocked-task-id-456"
        mock_celery_task.return_value = mock_task_instance
        
        response = api_client.post("/api/screen/upload", files=files, data=data)
        assert response.status_code == 202
        res_data = response.json()
        assert res_data["task_id"] == "mocked-task-id-456"
        assert "quarantine_file_id" in res_data
        assert res_data["status"] == "PENDING"
        mock_celery_task.assert_called_once()


def test_fake_pdf_rejected(api_client):
    """Verify that a text file disguised as a PDF (fake signature) is rejected."""
    fake_pdf_data = b"plain text mimicking pdf but missing signature"
    files = {"file": ("resume.pdf", fake_pdf_data, "application/pdf")}
    data = {"job_role": "Software Engineer"}

    response = api_client.post("/api/screen/upload", files=files, data=data)
    assert response.status_code == 400
    assert "invalid file signature" in response.json()["detail"].lower()


def test_malware_detection_path(api_client):
    """Verify that files containing the EICAR malware test signature are blocked."""
    eicar_malware = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    files = {"file": ("resume.pdf", eicar_malware, "application/pdf")}
    data = {"job_role": "Software Engineer"}

    response = api_client.post("/api/screen/upload", files=files, data=data)
    assert response.status_code == 400
    assert "malware detected" in response.json()["detail"].lower()


def test_upload_pipeline_security(api_client):
    """Verify that quarantined files are securely deleted upon any scanning or validation failure."""
    fake_pdf_data = b"plain text mimicking pdf but missing signature"
    files = {"file": ("resume.pdf", fake_pdf_data, "application/pdf")}
    data = {"job_role": "Software Engineer"}

    # Track how many files are currently in quarantine
    quarantine_files_before = list(storage_service.quarantine_dir.glob("*"))

    response = api_client.post("/api/screen/upload", files=files, data=data)
    assert response.status_code == 400

    quarantine_files_after = list(storage_service.quarantine_dir.glob("*"))
    assert len(quarantine_files_after) == len(quarantine_files_before)


def test_verify_clamav_connection_production_failure():
    """Verify that in production, startup check crashes the process if ClamAV daemon is unreachable."""
    from core.malware import verify_clamav_connection
    
    with patch("core.malware.IS_PRODUCTION", True), \
         patch("clamd.ClamdNetworkSocket") as mock_socket:
        
        mock_socket.side_effect = Exception("Connection refused")
        
        with pytest.raises(SystemExit) as exc:
            verify_clamav_connection()
        assert "CRITICAL" in str(exc.value)


def test_verify_clamav_connection_development_warning():
    """Verify that in development, startup check does NOT crash but logs a warning when ClamAV is unreachable."""
    from core.malware import verify_clamav_connection
    
    with patch("core.malware.IS_PRODUCTION", False), \
         patch("clamd.ClamdNetworkSocket") as mock_socket:
        
        mock_socket.side_effect = Exception("Connection refused")
        
        # Should complete without raising SystemExit or any exception
        verify_clamav_connection()


def test_generic_zip_renamed_docx_rejected(api_client):
    """Verify that a generic ZIP archive renamed to .docx is structurally rejected."""
    import zipfile
    
    # Generate generic ZIP containing non-DOCX files
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w") as z:
        z.writestr("image.png", b"fake binary image bytes")
    generic_zip_data = zip_io.getvalue()
    
    files = {"file": ("malicious.docx", generic_zip_data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    data = {"job_role": "Software Engineer"}
    
    response = api_client.post("/api/screen/upload", files=files, data=data)
    assert response.status_code == 400
    assert "invalid docx" in response.json()["detail"].lower()

