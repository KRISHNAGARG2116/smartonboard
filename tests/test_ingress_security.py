import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from server import app
from db.session import get_db
from core.config import get_settings, Settings


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


def test_api_rate_limiting_triggered(api_client):
    """Verify that high-frequency login calls trigger slowapi rate limiting (429)."""
    from core.limiter import limiter
    limiter.enabled = True
    
    try:
        payload = {"email": "rate@limit.com", "password": "password"}
        
        # Send multiple successive login requests to trigger rate limit (configured as 10/minute)
        responses = []
        for _ in range(12):
            responses.append(api_client.post("/api/v1/auth/login", json=payload))
            
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes
    finally:
        limiter.enabled = False


def test_upload_size_limit_screen_upload(api_client):
    """Verify that uploading files larger than 5MB to screen_upload endpoint returns 413 Payload Too Large."""
    # Generate 6MB file
    oversized_data = b"a" * (6 * 1024 * 1024)
    files = {"file": ("large_resume.pdf", oversized_data, "application/pdf")}
    data = {"job_role": "QA Lead"}
    
    response = api_client.post("/api/screen/upload", files=files, data=data)
    assert response.status_code == 413
    assert "file too large" in response.json()["detail"].lower()


def test_upload_size_limit_recruit(api_client):
    """Verify that uploading files larger than 5MB to recruit endpoint returns 413 Payload Too Large."""
    # Generate 6MB file
    oversized_data = b"a" * (6 * 1024 * 1024)
    files = {"file": ("large_resume.pdf", oversized_data, "application/pdf")}
    data = {"job_role": "QA Lead"}
    
    response = api_client.post("/api/recruit", files=files, data=data)
    assert response.status_code == 413
    assert "file too large" in response.json()["detail"].lower()


def test_production_secrets_validation():
    """Verify that settings fail startup in production if crucial keys are missing or defaulted."""
    # Clear settings cache
    get_settings.cache_clear()
    
    # Save current env state
    old_env = os.environ.get("ENV")
    old_fastapi_env = os.environ.get("FASTAPI_ENV")
    old_jwt_secret = os.environ.get("JWT_SECRET_KEY")
    old_db_url = os.environ.get("DATABASE_URL")
    old_groq_key = os.environ.get("GROQ_API_KEY")

    try:
        # 1. Enable production mode
        os.environ["ENV"] = "production"
        
        # Ensure all required vars are temporarily populated with valid production values
        os.environ["DATABASE_URL"] = "postgresql+psycopg://smartonboard:smartonboard@localhost:5432/smartonboard"
        os.environ["JWT_SECRET_KEY"] = "super-secret-key-123"
        os.environ["GROQ_API_KEY"] = "gsk_prodkey123"

        # 2. Test missing JWT_SECRET_KEY
        del os.environ["JWT_SECRET_KEY"]
        with pytest.raises(ValueError) as exc:
            Settings()
        assert "jwt_secret_key" in str(exc.value).lower()
        
        # Restore JWT
        os.environ["JWT_SECRET_KEY"] = "super-secret-key-123"
        
        # 3. Test defaulted JWT_SECRET_KEY
        os.environ["JWT_SECRET_KEY"] = "change-me-in-production"
        with pytest.raises(ValueError) as exc:
            Settings()
        assert "default fallback" in str(exc.value).lower()
        
        # Restore JWT
        os.environ["JWT_SECRET_KEY"] = "super-secret-key-123"

        # 4. Test missing DATABASE_URL
        del os.environ["DATABASE_URL"]
        with pytest.raises(ValueError) as exc:
            Settings()
        assert "database_url" in str(exc.value).lower()
        
        # Restore DB
        os.environ["DATABASE_URL"] = "postgresql+psycopg://smartonboard:smartonboard@localhost:5432/smartonboard"

        # 5. Test missing GROQ_API_KEY
        del os.environ["GROQ_API_KEY"]
        with pytest.raises(ValueError) as exc:
            Settings()
        assert "groq_api_key" in str(exc.value).lower()

    finally:
        # Restore original environment state
        get_settings.cache_clear()
        
        if old_env is not None:
            os.environ["ENV"] = old_env
        elif "ENV" in os.environ:
            del os.environ["ENV"]
            
        if old_fastapi_env is not None:
            os.environ["FASTAPI_ENV"] = old_fastapi_env
        elif "FASTAPI_ENV" in os.environ:
            del os.environ["FASTAPI_ENV"]
            
        if old_jwt_secret is not None:
            os.environ["JWT_SECRET_KEY"] = old_jwt_secret
        elif "JWT_SECRET_KEY" in os.environ:
            del os.environ["JWT_SECRET_KEY"]
            
        if old_db_url is not None:
            os.environ["DATABASE_URL"] = old_db_url
        elif "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
            
        if old_groq_key is not None:
            os.environ["GROQ_API_KEY"] = old_groq_key
        elif "GROQ_API_KEY" in os.environ:
            del os.environ["GROQ_API_KEY"]
