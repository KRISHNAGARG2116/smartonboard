import ipaddress
import socket
import uuid
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

ALLOWED_EVENTS = {
    "candidate.created",
    "candidate.deleted",
    "application.status_changed",
    "offer.approved",
    "offer.rejected",
    "sla.breached",
    "interview.scheduled",
    "interview.cancelled",
    "scorecard.submitted",
    "note.created",
}


def is_ssrf_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False

        # Handle literal IPs
        try:
            ip_obj = ipaddress.ip_address(hostname)
            if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local:
                return False
            return True
        except ValueError:
            pass

        # Resolve hostname to check IPs (IPv4 and IPv6)
        addr_info = socket.getaddrinfo(hostname, None)
        for item in addr_info:
            ip = item[4][0]
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local:
                return False
        return True
    except Exception:
        return False


class WebhookSubscriptionCreate(BaseModel):
    url: str = Field(..., max_length=2048, description="Target destination URL for webhook payloads")
    active_events: list[str] = Field(..., min_items=1, description="List of events to subscribe to")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if not is_ssrf_safe_url(v):
            raise ValueError("URL points to an invalid or private network address (SSRF protection)")
        return v

    @field_validator("active_events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        invalid_events = [e for e in v if e not in ALLOWED_EVENTS]
        if invalid_events:
            raise ValueError(f"Invalid webhook event types: {', '.join(invalid_events)}. Supported: {', '.join(ALLOWED_EVENTS)}")
        return v


class WebhookSubscriptionResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    url: str
    active_events: list[str]
    status: str
    consecutive_failures: int
    disabled_until: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookSubscriptionDetailResponse(WebhookSubscriptionResponse):
    signing_secret: str | None = None


class WebhookDeliveryLogResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    subscription_id: uuid.UUID
    event_type: str
    payload: dict
    attempt_number: int
    response_status: int | None = None
    response_body: str | None = None
    elapsed_seconds: float
    executed_at: datetime

    model_config = {"from_attributes": True}
