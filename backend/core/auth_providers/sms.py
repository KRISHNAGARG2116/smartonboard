import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger("smartonboard.auth_providers.sms")


class OTPDeliveryProvider(ABC):
    """Abstract interface for OTP code delivery (SMS, Email, etc.)."""

    @abstractmethod
    def send_otp(self, destination: str, code: str) -> bool:
        """Send an OTP code to the given destination."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name of this provider."""
        ...


class MockOTPProvider(OTPDeliveryProvider):
    """Development/testing provider that logs OTP codes instead of sending."""

    def send_otp(self, destination: str, code: str) -> bool:
        logger.info(f"[MOCK OTP] Code {code} → {destination}")
        print(f"MOCK OTP for {destination}: {code}")
        return True

    def provider_name(self) -> str:
        return "mock"


class TwilioOTPProvider(OTPDeliveryProvider):
    """Production SMS provider via Twilio REST API."""

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_phone = os.getenv("TWILIO_FROM_PHONE", "")

    def send_otp(self, destination: str, code: str) -> bool:
        if not all([self.account_sid, self.auth_token, self.from_phone]):
            logger.warning("Twilio credentials not configured, falling back to mock")
            return MockOTPProvider().send_otp(destination, code)

        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            client.messages.create(
                body=f"Your SmartOnboard verification code is: {code}. It expires in 5 minutes.",
                from_=self.from_phone,
                to=destination,
            )
            logger.info(f"Twilio OTP sent to {destination}")
            return True
        except Exception as e:
            logger.error(f"Twilio delivery failed for {destination}: {e}")
            return False

    def provider_name(self) -> str:
        return "twilio"


def get_otp_provider() -> OTPDeliveryProvider:
    """Factory: return the appropriate OTP provider based on environment config."""
    if os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"):
        return TwilioOTPProvider()
    return MockOTPProvider()
