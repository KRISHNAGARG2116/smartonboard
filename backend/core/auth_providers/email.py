import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.session import tenant_context

logger = logging.getLogger("smartonboard.auth_providers.email")


class EmailProvider:
    @staticmethod
    def send_verification_email(destination: str, code: str) -> bool:
        # SMTP email verification code delivery fallback
        from core.auth_providers.sms import get_otp_provider
        return get_otp_provider().send_otp(destination, code)

    @staticmethod
    def send_password_reset_email(destination: str, token: str) -> bool:
        logger.info(f"[EMAIL MOCK] Password reset link sent to {destination} with token {token}")
        print(f"EMAIL PASSWORD RESET for {destination}: {token}")
        return True

    @staticmethod
    def send_notification_email(destination: str, subject: str, body: str) -> bool:
        logger.info(f"[EMAIL MOCK] Notification to {destination} subject '{subject}': {body}")
        print(f"EMAIL NOTIFICATION for {destination} [{subject}]: {body}")
        return True


class DBVerificationTokenProvider:
    """Manages verification tokens stored in the `verification_tokens` table."""

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
        """Verify a submitted OTP code against stored tokens."""
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
