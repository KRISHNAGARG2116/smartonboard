import abc
from datetime import datetime
from typing import List, Tuple, Dict, Any


class BaseCalendarProvider(abc.ABC):
    @property
    @abc.abstractmethod
    def supports_webhooks(self) -> bool:
        pass

    @property
    @abc.abstractmethod
    def supports_delta_sync(self) -> bool:
        pass

    @property
    @abc.abstractmethod
    def supports_free_busy(self) -> bool:
        pass

    @property
    @abc.abstractmethod
    def supports_push_renewal(self) -> bool:
        pass

    @abc.abstractmethod
    def get_auth_url(self, company_slug: str, state: str) -> str:
        pass

    @abc.abstractmethod
    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        pass

    @abc.abstractmethod
    def refresh_access_token(self, refresh_token: str) -> dict:
        pass

    @abc.abstractmethod
    def fetch_busy_slots(self, email: str, access_token: str, start: datetime, end: datetime) -> List[Tuple[datetime, datetime]]:
        pass

    @abc.abstractmethod
    def book_event(self, email: str, access_token: str, start: datetime, end: datetime, subject: str, description: str, meeting_link_type: str | None = None) -> Tuple[str, str | None]:
        """Returns Tuple[external_event_id, meeting_link_url]"""
        pass

    @abc.abstractmethod
    def cancel_event(self, email: str, access_token: str, external_event_id: str) -> bool:
        pass


class BaseEmailProvider(abc.ABC):
    @abc.abstractmethod
    def send_email(self, recipient: str, subject: str, body_html: str, sender_email: str, smtp_settings: dict | None = None) -> str:
        """Sends email and returns external message id."""
        pass


class BaseChatProvider(abc.ABC):
    @abc.abstractmethod
    def send_message(self, webhook_url: str, message: str) -> bool:
        pass


class BaseHRISProvider(abc.ABC):
    @abc.abstractmethod
    def provision_employee(self, employee_data: dict, credentials: dict) -> dict:
        """Returns {"hris_id": str, "latency_ms": float, "payload": dict}"""
        pass

    @abc.abstractmethod
    def import_candidates(self, credentials: dict) -> List[dict]:
        """Imports candidates from HRIS and returns a list of candidate dictionaries."""
        pass


class BaseBackgroundCheckProvider(abc.ABC):
    @abc.abstractmethod
    def trigger_check(self, candidate_data: dict, check_type: str, credentials: dict) -> dict:
        """Returns {"external_check_id": str, "status": str}"""
        pass

    @abc.abstractmethod
    def get_check_status(self, external_check_id: str, credentials: dict) -> dict:
        """Returns {"status": str, "result": str | None}"""
        pass
