import re
import uuid


class AnonymizationService:
    """
    Service responsible for redacting candidate PII (names, emails, phones, socials, graduation years)
    before sending data to external Generative AI providers, mitigating recruiter bias.
    """

    @staticmethod
    def generate_candidate_alias(candidate_id: uuid.UUID) -> str:
        """
        Generates a unique, deterministic candidate alias based on their UUID (e.g. Candidate_Alias_A72).
        This preserves candidate identity across prompt iterations without exposing raw name.
        """
        hex_str = candidate_id.hex.upper()
        # Grab first 3 characters of the UUID to form a short, deterministic hash alias
        hash_suffix = hex_str[:3]
        return f"Candidate_Alias_{hash_suffix}"

    @classmethod
    def anonymize_text(
        cls,
        text: str,
        full_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        candidate_alias: str = "Candidate_Alias_Unknown"
    ) -> str:
        """
        Redacts names, emails, phones, socials/URLs, and graduation years from the text body,
        replacing them with safe anonymized tags.
        """
        if not text:
            return ""

        scrubbed = text

        # 1. Redact Emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        scrubbed = re.sub(email_pattern, "[EMAIL]", scrubbed)
        if email:
            scrubbed = re.sub(re.escape(email), "[EMAIL]", scrubbed, flags=re.IGNORECASE)
            # Also catch local part of email
            local_part = email.split("@")[0]
            if len(local_part) > 2:
                scrubbed = re.sub(r'\b' + re.escape(local_part) + r'\b', "[EMAIL_USER]", scrubbed, flags=re.IGNORECASE)

        # 2. Redact Phone Numbers
        # General pattern matching standard international / local phone numbers
        phone_pattern = r'\b(?:\+?\d{1,3}[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b'
        scrubbed = re.sub(phone_pattern, "[PHONE]", scrubbed)
        if phone:
            # Strip standard punctuation to match raw formats
            raw_phone = re.sub(r'\D', '', phone)
            if len(raw_phone) >= 7:
                # Regex for phone digits with potential separation
                digits_pat = r'[-. ]?'.join(list(raw_phone))
                scrubbed = re.sub(digits_pat, "[PHONE]", scrubbed)
            scrubbed = re.sub(re.escape(phone), "[PHONE]", scrubbed, flags=re.IGNORECASE)

        # 3. Redact Social Media Links / General URLs
        url_pattern = r'\bhttps?://[^\s<>"]+|www\.[^\s<>"]+\b'
        scrubbed = re.sub(url_pattern, "[URL]", scrubbed)

        # 4. Redact candidate name and replace with the alias
        if full_name:
            scrubbed = re.sub(re.escape(full_name), candidate_alias, scrubbed, flags=re.IGNORECASE)
            parts = [p.strip() for p in full_name.split() if len(p.strip()) > 2]
            for part in parts:
                scrubbed = re.sub(r'\b' + re.escape(part) + r'\b', candidate_alias, scrubbed, flags=re.IGNORECASE)

        # 5. Redact Graduation Years / Dates (to mitigate ageism bias)
        # Matches years between 1970 and 2035
        year_pattern = r'\b(19[7-9]\d|20[0-3]\d)\b'
        scrubbed = re.sub(year_pattern, "[YEAR]", scrubbed)

        return scrubbed
