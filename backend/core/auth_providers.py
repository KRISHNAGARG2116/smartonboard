"""
Abstract Authentication Provider Layer for SmartOnboard.

Provides a pluggable interface for authentication delivery mechanisms,
supporting future expansion to OAuth, Passkeys, magic-link, etc.

Current implementations:
- MockOTPProvider: Development/testing stub that logs OTP codes
- TwilioOTPProvider: Production SMS delivery via Twilio
- DBVerificationTokenProvider: Database-backed verification token management
"""

import hashlib
import logging
import os
import secrets
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.session import tenant_context

logger = logging.getLogger("smartonboard.auth_providers")


# ---------------------------------------------------------------------------
# Abstract base for OTP delivery
# ---------------------------------------------------------------------------

class OTPDeliveryProvider(ABC):
    """Abstract interface for OTP code delivery (SMS, Email, etc.)."""

    @abstractmethod
    def send_otp(self, destination: str, code: str) -> bool:
        """Send an OTP code to the given destination.

        Args:
            destination: Phone number or email address.
            code: The OTP code string.

        Returns:
            True if delivery succeeded, False otherwise.
        """
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


# ---------------------------------------------------------------------------
# Database-backed verification token management
# ---------------------------------------------------------------------------

class DBVerificationTokenProvider:
    """Manages verification tokens stored in the `verification_tokens` table.

    Handles OTP generation, hashing, storage, and verification with
    attempt limiting and expiration enforcement.
    """

    TOKEN_EXPIRY_MINUTES = 5
    MAX_ATTEMPTS = 3

    @staticmethod
    def generate_otp() -> str:
        """Generate a cryptographically random 6-digit OTP."""
        return f"{secrets.randbelow(900000) + 100000}"

    @staticmethod
    def hash_token(token: str) -> str:
        """SHA-256 hash of a plaintext token."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def create_token(
        cls,
        db: Session,
        user_id: uuid.UUID,
        token_type: str,
        code: Optional[str] = None,
    ) -> str:
        """Create a new verification token for the user.

        Invalidates any existing tokens of the same type for this user.
        Returns the plaintext OTP code.
        """
        from models.verification_token import VerificationToken

        plaintext = code or cls.generate_otp()
        token_hash = cls.hash_token(plaintext)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=cls.TOKEN_EXPIRY_MINUTES)

        with tenant_context(auth_mode="true"):
            # Invalidate (consume) existing tokens of same type
            existing = db.scalars(
                select(VerificationToken).where(
                    VerificationToken.user_id == user_id,
                    VerificationToken.token_type == token_type,
                    VerificationToken.consumed_at.is_(None),
                )
            ).all()
            for old in existing:
                old.consumed_at = datetime.now(timezone.utc)
                db.add(old)

            # Create new token
            vt = VerificationToken(
                user_id=user_id,
                token_hash=token_hash,
                token_type=token_type,
                expires_at=expires_at,
                attempts=0,
            )
            db.add(vt)
            db.commit()

        logger.info(f"Verification token created: type={token_type} user_id={user_id}")
        return plaintext

    @classmethod
    def verify_token(
        cls,
        db: Session,
        user_id: uuid.UUID,
        token_type: str,
        code: str,
    ) -> dict:
        """Verify a submitted OTP code against stored tokens.

        Returns a dict:
            - valid: True if code matches and is not expired
            - error: error message if invalid
            - token_id: UUID of matched token (if valid)
        """
        from models.verification_token import VerificationToken

        code_hash = cls.hash_token(code)

        with tenant_context(auth_mode="true"):
            token = db.scalar(
                select(VerificationToken).where(
                    VerificationToken.user_id == user_id,
                    VerificationToken.token_type == token_type,
                    VerificationToken.consumed_at.is_(None),
                ).order_by(VerificationToken.created_at.desc())
            )

            if not token:
                return {"valid": False, "error": "No active verification code found. Please request a new one."}

            # Check expiration
            if token.expires_at < datetime.now(timezone.utc):
                token.consumed_at = datetime.now(timezone.utc)
                db.add(token)
                db.commit()
                return {"valid": False, "error": "Verification code has expired. Please request a new one."}

            # Check attempts
            if token.attempts >= cls.MAX_ATTEMPTS:
                token.consumed_at = datetime.now(timezone.utc)
                db.add(token)
                db.commit()
                return {"valid": False, "error": "Too many failed attempts. Please request a new code."}

            # Check code match
            if token.token_hash != code_hash:
                token.attempts += 1
                db.add(token)
                db.commit()

                remaining = cls.MAX_ATTEMPTS - token.attempts
                if remaining <= 0:
                    token.consumed_at = datetime.now(timezone.utc)
                    db.add(token)
                    db.commit()
                    return {"valid": False, "error": "Too many failed attempts. Please request a new code."}

                return {"valid": False, "error": f"Invalid verification code. {remaining} attempt(s) remaining."}

            # Success - consume token
            token.consumed_at = datetime.now(timezone.utc)
            db.add(token)
            db.commit()

            return {"valid": True, "error": None, "token_id": token.id}
