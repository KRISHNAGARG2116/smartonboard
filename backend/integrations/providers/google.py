import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Tuple
from integrations.base.interfaces import BaseCalendarProvider, BaseEmailProvider
from integrations.base.registry import IntegrationRegistry

logger = logging.getLogger(__name__)

class GoogleCalendarProvider(BaseCalendarProvider):
    @property
    def supports_webhooks(self) -> bool:
        return True

    @property
    def supports_delta_sync(self) -> bool:
        return True

    @property
    def supports_free_busy(self) -> bool:
        return True

    @property
    def supports_push_renewal(self) -> bool:
        return False

    def get_auth_url(self, company_slug: str, state: str) -> str:
        client_id = os.getenv("GOOGLE_CLIENT_ID", "google-client-id")
        redirect_uri = f"http://mock-idp.com/oauth/google/callback"
        return f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=https://www.googleapis.com/auth/calendar&state={state}&access_type=offline&prompt=consent"

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        if code == "invalid_code":
            raise ValueError("Invalid OAuth code")
        return {
            "access_token": f"google_access_token_{code}",
            "refresh_token": f"google_refresh_token_{code}",
            "expires_in": 3600
        }

    def refresh_access_token(self, refresh_token: str) -> dict:
        if refresh_token == "invalid_refresh_token":
            raise ValueError("Invalid refresh token")
        return {
            "access_token": f"google_refreshed_access_{hash(refresh_token)}",
            "expires_in": 3600
        }

    def fetch_busy_slots(self, email: str, access_token: str, start: datetime, end: datetime) -> List[Tuple[datetime, datetime]]:
        b1 = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        b2 = b1 + timedelta(hours=1)
        return [(b1, b2)]

    def book_event(self, email: str, access_token: str, start: datetime, end: datetime, subject: str, description: str, meeting_link_type: str | None = None) -> Tuple[str, str | None]:
        event_id = f"google_event_{int(datetime.now(timezone.utc).timestamp())}"
        meet_link = f"https://meet.google.com/abc-defg-hij" if meeting_link_type == "google_meet" or meeting_link_type is None else None
        return event_id, meet_link

    def cancel_event(self, email: str, access_token: str, external_event_id: str) -> bool:
        return True

    def subscribe_webhook(self, email: str, access_token: str, webhook_url: str) -> dict:
        channel_id = f"google_channel_{int(datetime.now(timezone.utc).timestamp())}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        return {
            "subscription_id": channel_id,
            "expires_at": expires_at.isoformat()
        }

    def fetch_changes(self, email: str, access_token: str, sync_token: str | None = None) -> dict:
        new_sync_token = f"google_sync_token_{int(datetime.now(timezone.utc).timestamp())}"
        return {
            "changes": [
                {
                    "id": "event_123",
                    "status": "confirmed",
                    "start": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
                    "end": (datetime.now(timezone.utc) + timedelta(days=2, hours=1)).isoformat(),
                    "summary": "Mock Sync Interview"
                }
            ],
            "sync_token": new_sync_token
        }


class GoogleEmailProvider(BaseEmailProvider):
    def send_email(self, recipient: str, subject: str, body_html: str, sender_email: str, smtp_settings: dict | None = None) -> str:
        logger.info(f"Sending email via Google API from {sender_email} to {recipient}")
        return f"google_msg_{uuid.uuid4().hex[:12]}"


# Register implementation classes
IntegrationRegistry.register("calendar", "google", GoogleCalendarProvider)
IntegrationRegistry.register("email", "gmail", GoogleEmailProvider)
