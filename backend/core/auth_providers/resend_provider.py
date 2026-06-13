import logging
import os
from datetime import datetime
import resend

logger = logging.getLogger("smartonboard.auth_providers.resend")

class ResendEmailProvider:
    @staticmethod
    def _get_api_key() -> str | None:
        key = os.getenv("RESEND_API_KEY")
        if not key or key.strip() == "" or key.startswith("mock-"):
            return None
        return key.strip()

    @staticmethod
    def _get_sender() -> str:
        sender = os.getenv("RESEND_SENDER_EMAIL")
        if not sender or sender.strip() == "":
            return "onboarding@resend.dev"
        return sender.strip()

    @classmethod
    def get_verification_html(cls, code: str) -> str:
        year = datetime.now().year
        return f"""<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f4f5f7; padding: 20px; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e1e4e8; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); padding: 30px; text-align: center;">
        <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.025em;">SmartOnboard</h1>
      </div>
      <div style="padding: 40px; text-align: center;">
        <h2 style="margin-top: 0; color: #111827; font-size: 20px; font-weight: 600;">Verify Your Email Address</h2>
        <p style="color: #4b5563; font-size: 16px; line-height: 1.5; margin-bottom: 30px;">Thank you for registering with SmartOnboard. Please use the following 6-digit verification code to verify your email address. This code will expire in 10 minutes.</p>
        <div style="background-color: #f3f4f6; border-radius: 6px; padding: 20px; font-size: 32px; font-weight: 700; letter-spacing: 0.2em; color: #4f46e5; display: inline-block; min-width: 200px; margin-bottom: 30px; border: 1px solid #e5e7eb;">{code}</div>
        <p style="color: #9ca3af; font-size: 13px; line-height: 1.5; margin: 0;">If you did not request this verification code, please ignore this email.</p>
      </div>
      <div style="background-color: #f9fafb; padding: 20px; text-align: center; border-top: 1px solid #f3f4f6; color: #9ca3af; font-size: 12px;">
        © {year} SmartOnboard. All rights reserved.
      </div>
    </div>
  </body>
</html>
"""

    @classmethod
    def get_password_reset_html(cls, destination: str, token: str) -> str:
        year = datetime.now().year
        reset_url = f"http://localhost:5173/reset-password?token={token}&email={destination}"
        return f"""<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f4f5f7; padding: 20px; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e1e4e8; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); padding: 30px; text-align: center;">
        <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.025em;">SmartOnboard</h1>
      </div>
      <div style="padding: 40px; text-align: center;">
        <h2 style="margin-top: 0; color: #111827; font-size: 20px; font-weight: 600;">Reset Your Password</h2>
        <p style="color: #4b5563; font-size: 16px; line-height: 1.5; margin-bottom: 30px;">We received a request to reset your password for your SmartOnboard account. Click the button below to choose a new password. This link will expire in 30 minutes.</p>
        <a href="{reset_url}" style="background-color: #4f46e5; color: #ffffff; border-radius: 6px; padding: 14px 28px; font-size: 16px; font-weight: 600; text-decoration: none; display: inline-block; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(79, 70, 229, 0.2);">Reset Password</a>
        <p style="color: #9ca3af; font-size: 13px; line-height: 1.5; margin-bottom: 15px;">Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #4f46e5; font-size: 14px; margin-bottom: 30px;"><a href="{reset_url}" style="color: #4f46e5;">{reset_url}</a></p>
        <p style="color: #9ca3af; font-size: 13px; line-height: 1.5; margin: 0;">If you did not request a password reset, you can safely ignore this email.</p>
      </div>
      <div style="background-color: #f9fafb; padding: 20px; text-align: center; border-top: 1px solid #f3f4f6; color: #9ca3af; font-size: 12px;">
        © {year} SmartOnboard. All rights reserved.
      </div>
    </div>
  </body>
</html>
"""

    @classmethod
    def get_notification_html(cls, subject: str, body: str) -> str:
        year = datetime.now().year
        return f"""<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f4f5f7; padding: 20px; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e1e4e8; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); padding: 30px; text-align: center;">
        <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.025em;">SmartOnboard</h1>
      </div>
      <div style="padding: 40px;">
        <h2 style="margin-top: 0; color: #111827; font-size: 20px; font-weight: 600;">{subject}</h2>
        <div style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
          {body}
        </div>
        <p style="color: #9ca3af; font-size: 13px; line-height: 1.5; margin: 0; border-top: 1px solid #f3f4f6; padding-top: 20px;">This is a system notification from SmartOnboard.</p>
      </div>
      <div style="background-color: #f9fafb; padding: 20px; text-align: center; border-top: 1px solid #f3f4f6; color: #9ca3af; font-size: 12px;">
        © {year} SmartOnboard. All rights reserved.
      </div>
    </div>
  </body>
</html>
"""

    @classmethod
    def send_verification_email(cls, destination: str, code: str) -> bool:
        html_content = cls.get_verification_html(code)
        return cls._deliver(destination, "Verify Your SmartOnboard Email", html_content)

    @classmethod
    def send_password_reset_email(cls, destination: str, token: str) -> bool:
        html_content = cls.get_password_reset_html(destination, token)
        return cls._deliver(destination, "Reset Your SmartOnboard Password", html_content)

    @classmethod
    def send_notification_email(cls, destination: str, subject: str, body: str) -> bool:
        html_content = cls.get_notification_html(subject, body)
        return cls._deliver(destination, subject, html_content)

    @classmethod
    def _deliver(cls, to: str, subject: str, html: str) -> bool:
        api_key = cls._get_api_key()
        if not api_key:
            logger.info(f"[RESEND MOCK] Would send email via Resend to={to} subject='{subject}'")
            # Return False to let the fallback chain continue
            return False

        try:
            resend.api_key = api_key
            sender = cls._get_sender()
            # Send using resend SDK
            resend.Emails.send({
                "from": sender,
                "to": to,
                "subject": subject,
                "html": html
            })
            logger.info(f"Resend successfully sent email to {to}")
            return True
        except Exception as e:
            logger.error(f"Resend delivery failed for {to}: {e}")
            return False
