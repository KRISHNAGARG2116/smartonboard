import logging
import smtplib
import ssl
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from integrations.base.interfaces import BaseEmailProvider
from integrations.base.registry import IntegrationRegistry

logger = logging.getLogger(__name__)

class SmtpEmailProvider(BaseEmailProvider):
    def send_email(self, recipient: str, subject: str, body_html: str, sender_email: str, smtp_settings: dict | None = None) -> str:
        if not smtp_settings:
            raise ValueError("SMTP configuration settings are required")

        hostname = smtp_settings.get("hostname")
        port = smtp_settings.get("port")
        username = smtp_settings.get("username")
        password = smtp_settings.get("password")
        sender = smtp_settings.get("sender_email") or sender_email

        logger.info(f"Dispatching SMTP message to {recipient} via {hostname}:{port}")

        # Construct MIME Message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient

        part = MIMEText(body_html, "html")
        msg.attach(part)

        # Mock connection checks for testing
        if hostname == "mock-smtp.example.com" or "mock" in hostname:
            logger.info("Mock SMTP connection executed successfully.")
            return f"smtp_msg_{uuid.uuid4().hex[:12]}"

        # Standard smtplib sending
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

            if username and password:
                server.login(username, password)

            server.sendmail(sender, [recipient], msg.as_string())
            server.quit()
            return f"smtp_msg_{uuid.uuid4().hex[:12]}"
        except Exception as e:
            logger.error(f"SMTP dispatch failure to {recipient}: {str(e)}")
            raise e


# Register
IntegrationRegistry.register("email", "smtp", SmtpEmailProvider)
