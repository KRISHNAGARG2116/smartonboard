"""
Domain validation utilities for recruiter registration.

Implements:
- Public mail host blacklisting (gmail, yahoo, etc.)
- Native DNS/MX record validation without external business intelligence providers
- Fallback logic: domain exists but MX fails → allow with pending_verification
"""

import dns.resolver
import logging

logger = logging.getLogger("smartonboard.domain_validation")

# Comprehensive blacklist of public/consumer email providers.
# Recruiters MUST register with corporate email addresses.
PUBLIC_MAIL_HOSTS = frozenset({
    # Google
    "gmail.com", "googlemail.com",
    # Microsoft
    "outlook.com", "hotmail.com", "live.com", "msn.com", "outlook.co.uk",
    # Yahoo
    "yahoo.com", "yahoo.co.uk", "yahoo.co.in", "yahoo.ca", "yahoo.com.au",
    "ymail.com", "rocketmail.com",
    # Apple
    "icloud.com", "me.com", "mac.com",
    # AOL
    "aol.com",
    # ProtonMail
    "protonmail.com", "proton.me", "pm.me",
    # Zoho (free tier)
    "zoho.com", "zohomail.com",
    # Mail.com & GMX
    "mail.com", "email.com", "gmx.com", "gmx.net", "gmx.de",
    # Yandex
    "yandex.com", "yandex.ru", "ya.ru",
    # Tutanota
    "tutanota.com", "tutamail.com", "tuta.io",
    # FastMail
    "fastmail.com", "fastmail.fm",
    # Other common free providers
    "inbox.com", "mail.ru", "rambler.ru", "qq.com", "163.com", "126.com",
    "rediffmail.com", "naver.com", "hanmail.net",
})


def is_public_mail_host(email: str) -> bool:
    """Check if an email address uses a public/consumer mail provider.

    Returns True if the domain is blacklisted (should be rejected for recruiter signup).
    """
    domain = email.lower().strip().split("@")[-1]
    return domain in PUBLIC_MAIL_HOSTS


def validate_domain_dns(email: str) -> dict:
    """Perform DNS/MX validation on the email domain.

    Returns a dict with:
        - domain: the extracted domain
        - domain_exists: True if domain has A/AAAA records
        - mx_verified: True if domain has valid MX records
        - mx_records: list of MX hostnames (if found)
        - error: error message if domain does not exist at all

    Business rules:
        - If domain does not exist (NXDOMAIN) → reject registration (error set)
        - If domain exists but MX query fails → allow with pending_verification
        - If MX records found → domain_verified = True
    """
    domain = email.lower().strip().split("@")[-1]
    result = {
        "domain": domain,
        "domain_exists": False,
        "mx_verified": False,
        "mx_records": [],
        "error": None,
    }

    # Step 1: Check domain existence via A/AAAA records
    try:
        dns.resolver.resolve(domain, "A")
        result["domain_exists"] = True
    except dns.resolver.NXDOMAIN:
        # Domain does not exist at all
        result["error"] = f"Domain '{domain}' does not exist"
        logger.warning(f"Domain validation failed: NXDOMAIN for {domain}")
        return result
    except dns.resolver.NoAnswer:
        # A record query returned no answer; try AAAA
        try:
            dns.resolver.resolve(domain, "AAAA")
            result["domain_exists"] = True
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            result["error"] = f"Domain '{domain}' does not resolve"
            logger.warning(f"Domain validation failed: no A/AAAA for {domain}")
            return result
        except Exception as e:
            # DNS timeout or transient error - allow with pending
            result["domain_exists"] = True
            logger.info(f"DNS AAAA query error for {domain}: {e}, treating as exists")
    except dns.resolver.NoNameservers:
        result["error"] = f"Domain '{domain}' has no name servers"
        logger.warning(f"Domain validation failed: NoNameservers for {domain}")
        return result
    except Exception as e:
        # DNS timeout or transient error - treat domain as existing to avoid false rejections
        result["domain_exists"] = True
        logger.info(f"DNS A query error for {domain}: {e}, treating as exists")

    # Step 2: Check MX records
    try:
        mx_answers = dns.resolver.resolve(domain, "MX")
        mx_hosts = [str(rdata.exchange).rstrip(".") for rdata in mx_answers]
        result["mx_records"] = mx_hosts
        result["mx_verified"] = True
        logger.info(f"Domain {domain} MX verified: {mx_hosts}")
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        # Domain exists but no MX records - allow with pending_verification
        logger.info(f"Domain {domain} exists but no MX records found, pending verification")
    except Exception as e:
        # MX query timeout/error - allow with pending_verification
        logger.info(f"MX query error for {domain}: {e}, allowing with pending verification")

    return result


import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

DISPOSABLE_MAIL_HOSTS = frozenset({
    "mailinator.com",
    "yopmail.com",
    "tempmail.com",
    "dispostable.com",
    "sharklasers.com",
    "guerrillamail.com",
    "guerrillamailblock.com",
    "guerrillamail.net",
    "guerrillamail.org",
    "guerrillamail.biz",
    "10minutemail.com",
    "trashmail.com",
    "getairmail.com",
})


def validate_email_strict(email: str) -> dict:
    """Validate email format and check if it's from a disposable provider."""
    email = email.lower().strip()
    if not EMAIL_REGEX.match(email):
        return {"valid": False, "error": "Invalid email format"}

    domain = email.split("@")[-1]
    if domain in DISPOSABLE_MAIL_HOSTS:
        return {"valid": False, "error": "Disposable email addresses are not allowed"}

    return {"valid": True, "error": None}
