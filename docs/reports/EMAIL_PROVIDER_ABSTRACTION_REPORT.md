# Email Provider Abstraction Report

This document audits the implementation of the `EmailProvider` abstraction layer in SmartOnboard (Phase 14B).

---

## 1. Objective of Email Abstraction

Historically, verification emails and transactional alerts were sent using ad-hoc SMTP blocks directly within route handlers. This created tight coupling and made it difficult to swap delivery channels (e.g. SMTP, SendGrid, Amazon SES, Resend) or mock delivery in testing.

To solve this, a dedicated abstract interface `EmailProvider` has been introduced.

---

## 2. Interface Definition

The abstract class defines the contract for all email providers in the system:

```python
# backend/core/auth_providers/email.py
from abc import ABC, abstractmethod

class EmailProvider(ABC):
    """Abstract interface for email delivery providers."""

    @abstractmethod
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send an email to the specified recipient."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this email provider."""
        ...
```

---

## 3. Concrete Implementations

Currently, the package supports the following concrete implementations:
- **`MockEmailProvider`**: Used in development and testing. Instead of delivering actual emails, it logs the recipient, subject, and body to the system log, preventing test execution from spamming external SMTP servers.
- **`SMTPEmailProvider`**: Production provider that utilizes the company's SMTP settings.

This abstraction ensures that the platform is ready for the upcoming Resend Integration (Phase 14C) without requiring changes to any business logic.
