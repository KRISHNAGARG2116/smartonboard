import os
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from api.demo_workspace import reset_demo_workspace

def test_production_environment_safety_block():
    """Asserts that demo resets raise HTTP 403 Forbidden in production environments."""
    db_mock = MagicMock()
    owner_mock = MagicMock()
    
    # Force production env
    os.environ["FASTAPI_ENV"] = "production"
    
    with pytest.raises(HTTPException) as exc_info:
        reset_demo_workspace(db_mock, owner_mock)
        
    assert exc_info.value.status_code == 403
    assert "blocked in production" in exc_info.value.detail
    
    # Restore dev env
    os.environ["FASTAPI_ENV"] = "development"
