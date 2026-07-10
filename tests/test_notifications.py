import uuid
from unittest.mock import MagicMock
import pytest
from models.ats_models import Notification
from api.notifications import list_notifications, mark_notification_read

def test_list_notifications_query():
    """Asserts that notification listings return matching entries."""
    db_mock = MagicMock()
    user_mock = MagicMock()
    user_mock.id = uuid.uuid4()
    
    n_mock = Notification(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        user_id=user_mock.id,
        title="Mock Alert",
        message="Alert details",
        type="sla",
        status="unread"
    )
    
    db_mock.scalars.return_value.all.return_value = [n_mock]
    
    results = list_notifications(db_mock, user_mock)
    assert len(results) == 1
    assert results[0]["title"] == "Mock Alert"
    assert results[0]["status"] == "unread"
