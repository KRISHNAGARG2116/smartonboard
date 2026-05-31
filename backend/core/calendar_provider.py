import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
import httpx
from typing import Dict, Any, List, Tuple


class BaseCalendarProvider(ABC):
    @property
    @abstractmethod
    def supports_webhooks(self) -> bool:
        """Indicates if the provider supports subscribing to real-time webhook updates."""
        pass

    @property
    @abstractmethod
    def supports_delta_sync(self) -> bool:
        """Indicates if the provider supports delta/incremental synchronization via tokens."""
        pass

    @property
    @abstractmethod
    def supports_free_busy(self) -> bool:
        """Indicates if the provider supports querying free/busy calendar time ranges directly."""
        pass

    @property
    @abstractmethod
    def supports_push_renewal(self) -> bool:
        """Indicates if the provider supports renewing active webhook subscriptions."""
        pass

    @abstractmethod
    def get_auth_url(self, company_slug: str, state: str) -> str:
        """Returns third-party OAuth authorization start URL."""
        pass

    @abstractmethod
    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        """Exchanges authorization code for credentials dict (access_token, refresh_token, expires_in)."""
        pass

    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> dict:
        """Refreshes expired credentials using refresh token."""
        pass

    @abstractmethod
    def fetch_busy_slots(self, email: str, access_token: str, start: datetime, end: datetime) -> List[Tuple[datetime, datetime]]:
        """Queries busy blocks for the interviewer email."""
        pass

    @abstractmethod
    def book_event(self, email: str, access_token: str, start: datetime, end: datetime, subject: str, description: str) -> str:
        """Creates synchronized calendar meeting event and returns external_event_id."""
        pass

    @abstractmethod
    def cancel_event(self, email: str, access_token: str, external_event_id: str) -> bool:
        """Deletes synchronized meeting event externally."""
        pass

    @abstractmethod
    def subscribe_webhook(self, email: str, access_token: str, webhook_url: str) -> dict:
        """Subscribes to webhook notifications and returns subscription metadata (id, expires_at)."""
        pass

    @abstractmethod
    def renew_webhook(self, email: str, access_token: str, subscription_id: str) -> dict:
        """Renews a webhook subscription and returns renewed metadata."""
        pass

    @abstractmethod
    def fetch_changes(self, email: str, access_token: str, sync_token: str | None = None) -> dict:
        """Fetches incremental changes since sync_token and returns updated events and a new sync_token."""
        pass


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
        # Google calendar API webhooks do not support direct "renewal" call;
        # you generally register a new channel. Thus, supports_push_renewal is False.
        return False

    def get_auth_url(self, company_slug: str, state: str) -> str:
        # Mock auth URL start for testing, but fully structured
        client_id = os.getenv("GOOGLE_CLIENT_ID", "google-client-id")
        redirect_uri = f"http://mock-idp.com/oauth/google/callback"
        return f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=https://www.googleapis.com/auth/calendar&state={state}&access_type=offline&prompt=consent"

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        # In a real integration, we post to https://oauth2.googleapis.com/token
        # For our test suite, we simulate or execute mock exchange
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
        # Simulate free/busy check
        # Return a couple of mock busy blocks to satisfy scheduling tests
        # ensure timezone-aware datetime objects are returned
        b1 = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        b2 = b1 + timedelta(hours=1)
        return [(b1, b2)]

    def book_event(self, email: str, access_token: str, start: datetime, end: datetime, subject: str, description: str) -> str:
        # Returns external event ID
        return f"google_event_{int(datetime.now(timezone.utc).timestamp())}"

    def cancel_event(self, email: str, access_token: str, external_event_id: str) -> bool:
        return True

    def subscribe_webhook(self, email: str, access_token: str, webhook_url: str) -> dict:
        channel_id = f"google_channel_{int(datetime.now(timezone.utc).timestamp())}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        return {
            "subscription_id": channel_id,
            "expires_at": expires_at.isoformat()
        }

    def renew_webhook(self, email: str, access_token: str, subscription_id: str) -> dict:
        raise NotImplementedError("Google Calendar Provider does not support push renewal; create a new channel instead.")

    def fetch_changes(self, email: str, access_token: str, sync_token: str | None = None) -> dict:
        new_sync_token = f"google_sync_token_{int(datetime.now(timezone.utc).timestamp())}"
        # Mock changes list
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
        # Microsoft Graph API subscriptions support direct renewal / PATCH operations.
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

    def book_event(self, email: str, access_token: str, start: datetime, end: datetime, subject: str, description: str) -> str:
        return f"microsoft_event_{int(datetime.now(timezone.utc).timestamp())}"

    def cancel_event(self, email: str, access_token: str, external_event_id: str) -> bool:
        return True

    def subscribe_webhook(self, email: str, access_token: str, webhook_url: str) -> dict:
        subscription_id = f"microsoft_sub_{int(datetime.now(timezone.utc).timestamp())}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=4230) # Microsoft Outlook max sub lifetime is ~4230 minutes
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
