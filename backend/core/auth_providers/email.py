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
    @classmethod
    def send_verification_email(cls, destination: str, code: str) -> bool:
        from core.auth_providers.resend_provider import ResendEmailProvider
        html = ResendEmailProvider.get_verification_html(code)
        subject = "Verify Your SmartOnboard Email"
        log_msg = f"Email verification code sent to {destination} with code {code}"
        return cls._deliver_chain(destination, subject, html, log_msg)

    @classmethod
    def send_password_reset_email(cls, destination: str, token: str) -> bool:
        from core.auth_providers.resend_provider import ResendEmailProvider
        html = ResendEmailProvider.get_password_reset_html(destination, token)
        subject = "Reset Your SmartOnboard Password"
        log_msg = f"Password reset link sent to {destination} with token {token}"
        return cls._deliver_chain(destination, subject, html, log_msg)

    @classmethod
    def send_notification_email(cls, destination: str, subject: str, body: str) -> bool:
        from core.auth_providers.resend_provider import ResendEmailProvider
        html = ResendEmailProvider.get_notification_html(subject, body)
        log_msg = f"Notification to {destination} subject '{subject}': {body}"
        return cls._deliver_chain(destination, subject, html, log_msg)

    @classmethod
    def _deliver_chain(cls, to: str, subject: str, html: str, fallback_log_msg: str) -> bool:
        # 1. Try Resend
        from core.auth_providers.resend_provider import ResendEmailProvider
        if ResendEmailProvider._deliver(to, subject, html):
            return True

        # 2. Try SMTP
        if cls._send_via_smtp(to, subject, html):
            return True

        # 3. Try Mock fallback
        logger.info(f"[EMAIL MOCK FALLBACK] {fallback_log_msg}")
        print(f"EMAIL MOCK FALLBACK: To={to}, Subject={subject}")
        return True

    @classmethod
    def _send_via_smtp(cls, to: str, subject: str, html: str) -> bool:
        import os
        import smtplib
        import ssl
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        host = os.getenv("GLOBAL_SMTP_HOST")
        port_str = os.getenv("GLOBAL_SMTP_PORT")
        username = os.getenv("GLOBAL_SMTP_USERNAME")
        password = os.getenv("GLOBAL_SMTP_PASSWORD")
        sender = os.getenv("GLOBAL_SMTP_SENDER", "no-reply@smartonboard.com")

        # If any essential SMTP settings are missing or default placeholders, skip
        if not host or host == "smtp.example.com" or not port_str:
            logger.info("[SMTP FALLBACK] SMTP not configured. Skipping SMTP step.")
            return False

        try:
            port = int(port_str)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = to

            part = MIMEText(html, "html")
            msg.attach(part)

            timeout = 5.0
            if port == 465:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
            else:
                server = smtplib.SMTP(host, port, timeout=timeout)
                server.ehlo()
                if server.has_extn("starttls"):
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()

            if username and password:
                server.login(username, password)

            server.sendmail(sender, [to], msg.as_string())
            server.quit()
            logger.info(f"SMTP successfully sent email to {to}")
            return True
        except Exception as e:
            logger.warning(f"SMTP delivery failed for {to}: {e}")
            return False


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
        expires_in_minutes: Optional[int] = None,
    ) -> str:
        """Create a new verification token for the user.

        Invalidates any existing tokens of the same type for this user.
        Returns the plaintext OTP code.
        """
        from models.verification_token import VerificationToken

        plaintext = code or cls.generate_otp()
        token_hash = cls.hash_token(plaintext)
        minutes = expires_in_minutes or cls.TOKEN_EXPIRY_MINUTES
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)

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

        logger.info(f"Verification token created: type={token_type} user_id={user_id} expires_in={minutes}m")
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
