import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Tuple
from integrations.base.interfaces import BaseCalendarProvider, BaseEmailProvider
from integrations.base.registry import IntegrationRegistry

logger = logging.getLogger(__name__)

class MicrosoftGraphProvider(BaseCalendarProvider):
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
        return True

    def get_auth_url(self, company_slug: str, state: str) -> str:
        client_id = os.getenv("MICROSOFT_CLIENT_ID", "microsoft-client-id")
        redirect_uri = f"http://mock-idp.com/oauth/outlook/callback"
        return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=Calendars.ReadWrite&state={state}"

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        if code == "invalid_code":
            raise ValueError("Invalid OAuth code")
        return {
            "access_token": f"microsoft_access_token_{code}",
            "refresh_token": f"microsoft_refresh_token_{code}",
            "expires_in": 3600
        }

    def refresh_access_token(self, refresh_token: str) -> dict:
        if refresh_token == "invalid_refresh_token":
            raise ValueError("Invalid refresh token")
        return {
            "access_token": f"microsoft_refreshed_access_{hash(refresh_token)}",
            "expires_in": 3600
        }

    def fetch_busy_slots(self, email: str, access_token: str, start: datetime, end: datetime) -> List[Tuple[datetime, datetime]]:
        b1 = datetime.now(timezone.utc).replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)
        b2 = b1 + timedelta(hours=1)
        return [(b1, b2)]

    def book_event(self, email: str, access_token: str, start: datetime, end: datetime, subject: str, description: str, meeting_link_type: str | None = None) -> Tuple[str, str | None]:
        event_id = f"microsoft_event_{int(datetime.now(timezone.utc).timestamp())}"
        teams_link = f"https://teams.microsoft.com/l/meetup-join/abc" if meeting_link_type == "teams" or meeting_link_type is None else None
        return event_id, teams_link

    def cancel_event(self, email: str, access_token: str, external_event_id: str) -> bool:
        return True

    def subscribe_webhook(self, email: str, access_token: str, webhook_url: str) -> dict:
        subscription_id = f"microsoft_sub_{int(datetime.now(timezone.utc).timestamp())}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=4230)
        return {
            "subscription_id": subscription_id,
            "expires_at": expires_at.isoformat()
        }

    def renew_webhook(self, email: str, access_token: str, subscription_id: str) -> dict:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=4230)
        return {
            "subscription_id": subscription_id,
            "expires_at": expires_at.isoformat()
        }

    def fetch_changes(self, email: str, access_token: str, sync_token: str | None = None) -> dict:
        new_sync_token = f"microsoft_sync_token_{int(datetime.now(timezone.utc).timestamp())}"
        return {
            "changes": [
                {
                    "id": "event_456",
                    "status": "confirmed",
                    "start": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
                    "end": (datetime.now(timezone.utc) + timedelta(days=3, hours=1)).isoformat(),
                    "summary": "Mock Outlook Sync Interview"
                }
            ],
            "sync_token": new_sync_token
        }


class MicrosoftEmailProvider(BaseEmailProvider):
    def send_email(self, recipient: str, subject: str, body_html: str, sender_email: str, smtp_settings: dict | None = None) -> str:
        logger.info(f"Sending email via M365 API from {sender_email} to {recipient}")
        return f"microsoft_msg_{hash(recipient)}"


# Register
IntegrationRegistry.register("calendar", "microsoft", MicrosoftGraphProvider)
IntegrationRegistry.register("calendar", "outlook", MicrosoftGraphProvider)
IntegrationRegistry.register("email", "microsoft365", MicrosoftEmailProvider)
