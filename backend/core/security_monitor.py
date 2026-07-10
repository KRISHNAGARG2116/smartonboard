import hmac
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ThreatAlertSeverity:
    INFORMATIONAL = "Informational"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class SecurityMonitoringService:
    @classmethod
    def analyze_event_risk(cls, event_type: str, details: dict) -> Dict[str, Any]:
        """
        Classifies intrusion and privilege escalation alerts with severity levels.
        """
        severity = ThreatAlertSeverity.INFORMATIONAL
        needs_immediate_block = False
        message = ""

        if event_type == "auth.brute_force":
            severity = ThreatAlertSeverity.CRITICAL
            needs_immediate_block = True
            message = f"Brute force lockout triggered on IP {details.get('ip_address')}"
            
        elif event_type == "auth.failed_login":
            attempts = details.get("attempts", 1)
            severity = ThreatAlertSeverity.LOW if attempts < 3 else ThreatAlertSeverity.MEDIUM
            message = f"Failed login attempt from IP {details.get('ip_address')} (Attempts: {attempts})"
            
        elif event_type == "rbac.privilege_escalation":
            severity = ThreatAlertSeverity.HIGH
            message = f"User {details.get('user_id')} attempted to access restricted admin resource without permissions."
            
        elif event_type == "ai.unusual_activity":
            prompt_rate = details.get("prompts_per_minute", 0)
            if prompt_rate > 50:
                severity = ThreatAlertSeverity.HIGH
                message = f"High-volume AI requests detected: {prompt_rate} prompts/min from recruiter {details.get('user_id')}"
            else:
                severity = ThreatAlertSeverity.MEDIUM
                message = f"Unusual AI rate: {prompt_rate} prompts/min"
                
        elif event_type == "data.suspicious_export":
            records_count = details.get("records_count", 0)
            if records_count > 100:
                severity = ThreatAlertSeverity.CRITICAL
                message = f"Bulk data extraction warning: {records_count} candidates exported by user {details.get('user_id')}"
            else:
                severity = ThreatAlertSeverity.MEDIUM
                message = f"Data export: {records_count} records"

        logger.warning(f"[{severity.upper()} SECURITY ALERT] {message}")

        return {
            "severity": severity,
            "message": message,
            "blocked": needs_immediate_block,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class WebhookSignatureVerifier:
    @classmethod
    def generate_signature(cls, payload: bytes, secret: str) -> str:
        """Helper to generate HMAC SHA256 signature."""
        return hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

    @classmethod
    def verify_webhook_signature(
        cls,
        payload: bytes,
        signature: str,
        active_secret: str,
        previous_secret: str | None = None
    ) -> bool:
        """
        Verifies signature against current active secret OR previous secret
        to avoid downtime during webhook secret rotations.
        """
        # 1. Test active signature
        expected_active = cls.generate_signature(payload, active_secret)
        if hmac.compare_digest(expected_active, signature):
            return True

        # 2. Test fallback previous signature if present
        if previous_secret:
            expected_prev = cls.generate_signature(payload, previous_secret)
            if hmac.compare_digest(expected_prev, signature):
                logger.info("Webhook verified successfully using previous secret rollover signature.")
                return True

        logger.warning("Webhook signature verification failed against both active and rollover secrets.")
        return False
