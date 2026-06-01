import base64
import json
import logging
import os
import ssl
import smtplib
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from core.vault import SecretVaultService
from core.config import get_settings
from models.enterprise import CompanySMTPSettings

logger = logging.getLogger("app")


def verify_smtp_credentials(hostname: str, port: int, username: str, password_plain: str):
    """
    Performs connection, EHLO, STARTTLS (or SSL directly), and login authentication.
    Raises exception with detailed message if any stage fails.
    """
    timeout = 10.0
    try:
        if port == 465:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(hostname, port, timeout=timeout, context=context)
        else:
            server = smtplib.SMTP(hostname, port, timeout=timeout)
            server.ehlo()
            if server.has_extn("starttls"):
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
        
        if username and password_plain:
            server.login(username, password_plain)
            
        server.quit()
    except Exception as e:
        logger.error(f"SMTP verification failed for {hostname}:{port}: {str(e)}")
        raise ValueError(f"SMTP Handshake/Auth failed: {str(e)}")


def get_smtp_transport_details(db: Session, company_id: uuid.UUID) -> dict:
    """
    Returns decrypted custom SMTP settings if they are verified and not expired (90 days).
    Otherwise, returns global fallback default credentials.
    """
    stmt = select(CompanySMTPSettings).where(CompanySMTPSettings.company_id == company_id)
    settings_obj = db.scalar(stmt)

    if settings_obj and settings_obj.verification_status == "verified":
        # Check 90-day verification expiry policy
        if settings_obj.last_verified_at:
            now = datetime.now(timezone.utc)
            # Make last_verified_at timezone aware if it is naive
            last_verified = settings_obj.last_verified_at
            if last_verified.tzinfo is None:
                last_verified = last_verified.replace(tzinfo=timezone.utc)
                
            if now - last_verified < timedelta(days=90):
                try:
                    vault = SecretVaultService()
                    envelope = {
                        "ciphertext": settings_obj.encrypted_password,
                        "iv": settings_obj.iv,
                        "tag": settings_obj.tag,
                        "key_version": settings_obj.key_version
                    }
                    password_plain = vault.decrypt_secret(json.dumps(envelope))
                    return {
                        "use_custom": True,
                        "hostname": settings_obj.hostname,
                        "port": settings_obj.port,
                        "username": settings_obj.username,
                        "password": password_plain,
                        "sender_email": settings_obj.sender_email
                    }
                except Exception as e:
                    logger.error(f"Failed to decrypt custom SMTP settings password for company {company_id}: {str(e)}")

    # Fallback to global defaults
    return {
        "use_custom": False,
        "hostname": os.getenv("GLOBAL_SMTP_HOST", "smtp.example.com"),
        "port": int(os.getenv("GLOBAL_SMTP_PORT", "587")),
        "username": os.getenv("GLOBAL_SMTP_USERNAME", "no-reply@smartonboard.com"),
        "password": os.getenv("GLOBAL_SMTP_PASSWORD", "global-secure-password"),
        "sender_email": os.getenv("GLOBAL_SMTP_SENDER", "no-reply@smartonboard.com")
    }
