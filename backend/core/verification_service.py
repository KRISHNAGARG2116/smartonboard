import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from core.config import get_settings
from core.auth_providers import DBVerificationTokenProvider, EmailProvider
from models.user import User
from models.candidate_profile import CandidateProfile

logger = logging.getLogger("smartonboard.verification_service")

# In-memory storage for Mock Phone Verify fallback
# Structures:
# _mock_phone_otps: phone_number -> {"code": code, "expires_at": expires_at, "attempts": attempts}
# _mock_phone_lockouts: phone_number -> lockout_expires_at
# _mock_phone_rate_limits: phone_number -> list of send timestamps
_mock_phone_otps = {}
_mock_phone_lockouts = {}
_mock_phone_rate_limits = {}


class VerificationService:
    """Unified service for email (Resend/SMTP) and phone (Twilio Verify / Mock) verifications.
    
    Designed to support both recruiter and candidate verification flows to ensure future parity.
    """

    # --- EMAIL VERIFICATION (Resend / DB Verification Token) ---

    @staticmethod
    def send_email_verification(db: Session, user: User) -> bool:
        """Generate and send an email verification OTP."""
        try:
            # Generate email verification OTP code (10-minute expiry)
            otp_code = DBVerificationTokenProvider.create_token(
                db=db,
                user_id=user.id,
                token_type="email_otp",
                expires_in_minutes=10
            )
            EmailProvider.send_verification_email(user.email, otp_code)
            logger.info(f"Email verification OTP sent to {user.email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email verification to {user.email}: {e}")
            return False

    @staticmethod
    def verify_email_code(db: Session, user: User, code: str) -> bool:
        """Verify an email verification OTP code."""
        result = DBVerificationTokenProvider.verify_token(
            db=db,
            user_id=user.id,
            token_type="email_otp",
            code=code,
        )
        if not result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"],
            )
        return True

    # --- PHONE VERIFICATION (Twilio Verify / Mock) ---

    @classmethod
    def send_phone_verification(cls, db: Session, user: User, phone_number: str) -> bool:
        """Send a phone verification OTP code. Enforces 5 OTP/hour rate limit and 15-minute lockout."""
        phone = phone_number.strip()
        if not phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is required",
            )

        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        verify_sid = os.getenv("TWILIO_VERIFY_SERVICE_SID")

        now = datetime.now(timezone.utc)

        # 1. Enforce lockout (15 minutes)
        lockout_expires = _mock_phone_lockouts.get(phone)
        if lockout_expires and now < lockout_expires:
            remaining = int((lockout_expires - now).total_seconds() / 60)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Too many failed verification attempts. This phone number is locked out. Please try again in {remaining} minute(s).",
            )
        elif lockout_expires:
            # Lockout expired, clean it up
            _mock_phone_lockouts.pop(phone, None)

        # 2. Enforce rate limit (5 OTP / hour)
        sends = _mock_phone_rate_limits.get(phone, [])
        # Filter out sends older than 1 hour
        sends = [s for s in sends if now - s < timedelta(hours=1)]
        _mock_phone_rate_limits[phone] = sends

        if len(sends) >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Verification OTP send limit exceeded. You can request up to 5 verification codes per hour.",
            )

        # Record this send attempt
        _mock_phone_rate_limits[phone].append(now)

        # 3. Deliver OTP
        if account_sid and auth_token and verify_sid:
            try:
                from twilio.rest import Client
                client = Client(account_sid, auth_token)
                # Call Twilio Verify API to initiate verification
                client.verify.v2.services(verify_sid).verifications.create(
                    to=phone,
                    channel="sms"
                )
                logger.info(f"Twilio Verify OTP initiated for {phone}")
                return True
            except Exception as e:
                logger.error(f"Twilio Verify API failed for {phone}: {e}. Falling back to mock delivery.")
                # Fall back to Mock mode on API error
                pass

        # Mock Mode Fallback
        code = f"{secrets.randbelow(900000) + 100000}"
        expires_at = now + timedelta(minutes=10)
        _mock_phone_otps[phone] = {
            "code": code,
            "expires_at": expires_at,
            "attempts": 0
        }
        logger.info(f"[MOCK TWILIO VERIFY] OTP code for {phone}: {code} (Expires in 10 minutes)")
        print(f"MOCK PHONE OTP for {phone}: {code}")
        return True

    @classmethod
    def verify_phone_code(cls, db: Session, user: User, code: str) -> bool:
        """Verify a phone verification OTP. Enforces max 5 failed attempts and lockout."""
        # Retrieve phone number from candidate profile
        profile: Optional[CandidateProfile] = user.candidate_profile
        if not profile or not profile.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No phone number registered on profile. Please request a verification code first.",
            )

        phone = profile.phone_number.strip()
        code_str = code.strip()
        now = datetime.now(timezone.utc)

        # 1. Enforce lockout (15 minutes)
        lockout_expires = _mock_phone_lockouts.get(phone)
        if lockout_expires and now < lockout_expires:
            remaining = int((lockout_expires - now).total_seconds() / 60)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Too many failed verification attempts. This phone number is locked out. Please try again in {remaining} minute(s).",
            )

        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        verify_sid = os.getenv("TWILIO_VERIFY_SERVICE_SID")

        if account_sid and auth_token and verify_sid:
            try:
                from twilio.rest import Client
                from twilio.base.exceptions import TwilioRestException
                client = Client(account_sid, auth_token)
                
                # Verify code via Twilio Verify API
                check = client.verify.v2.services(verify_sid).verification_checks.create(
                    to=phone,
                    code=code_str
                )
                
                if check.status == "approved":
                    logger.info(f"Twilio Verify OTP approved for {phone}")
                    return True
                else:
                    # Twilio check failed but did not raise an exception (e.g. just status='pending')
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid verification code.",
                    )
            except TwilioRestException as e:
                # Handle Twilio-specific verification errors
                # Error 60200: Max verification check attempts reached (lockout)
                if e.code == 60200:
                    # Lock out in mock lockout state as well for sync
                    _mock_phone_lockouts[phone] = now + timedelta(minutes=15)
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Too many failed verification attempts. This number is locked out for 15 minutes. Please try again later.",
                    )
                # Error 60202: Verification expired
                elif e.code == 60202:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Verification code has expired. Please request a new one.",
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Verification failed: {e.msg}",
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Twilio Verify API exception for {phone}: {e}. Falling back to mock verification.")
                # Fall back to Mock mode on API error
                pass

        # Mock Mode Verification
        stored = _mock_phone_otps.get(phone)
        if not stored:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active verification request found or code has expired. Please request a new one.",
            )

        # Check expiration (10 minutes)
        if now > stored["expires_at"]:
            _mock_phone_otps.pop(phone, None)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code has expired. Please request a new one.",
            )

        # Check code match
        if stored["code"] != code_str:
            stored["attempts"] += 1
            if stored["attempts"] >= 5:
                # Lockout for 15 minutes
                _mock_phone_lockouts[phone] = now + timedelta(minutes=15)
                _mock_phone_otps.pop(phone, None)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Too many failed verification attempts. This number is locked out for 15 minutes. Please request a new OTP.",
                )
            
            remaining = 5 - stored["attempts"]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid verification code. {remaining} attempt(s) remaining.",
            )

        # Success - clean up code storage
        _mock_phone_otps.pop(phone, None)
        return True
