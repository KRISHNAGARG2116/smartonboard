import uuid
import base64
import hashlib
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest

from models import User, Company
from models.enums import UserRole
from core.session_security import check_impossible_travel, RiskBasedAuthenticationService, enforce_concurrent_session_limits
from core.data_governance import DataGovernanceService
from core.encryption import EnvelopeEncryptionService, SecretsInventoryService
from core.security_monitor import SecurityMonitoringService, WebhookSignatureVerifier
from core.policy_engine import PolicyEngineService, BackupVerificationService
from api.deps import ROLE_HIERARCHY


def test_role_hierarchy_permissions():
    """Asserts hierarchical RBAC configurations map roles as expected."""
    assert UserRole.RECRUITER in ROLE_HIERARCHY[UserRole.OWNER]
    assert UserRole.EMPLOYEE in ROLE_HIERARCHY[UserRole.RECRUITER]
    assert UserRole.OWNER not in ROLE_HIERARCHY[UserRole.RECRUITER]


def test_impossible_travel_filters():
    """Validates velocity filtering for impossible logins."""
    # Traveling from SF to NY in 10 minutes (0.16 hours) is impossible
    assert check_impossible_travel(
        "127.0.0.1", datetime.now(),
        "192.168.1.1", datetime.now() + timedelta(minutes=10)
    ) is True
    
    # Staying on the same IP is never impossible travel
    assert check_impossible_travel(
        "127.0.0.1", datetime.now(),
        "127.0.0.1", datetime.now() + timedelta(minutes=5)
    ) is False


def test_risk_score_calculator():
    """Verifies that threat context signals calculate risk score accurately."""
    context_high = {
        "impossible_travel_detected": True,
        "is_vpn": True,
        "device_changed": True
    }
    # 50 + 25 + 15 = 90
    score = RiskBasedAuthenticationService.calculate_risk_score(context_high)
    assert score == 90.0
    assert RiskBasedAuthenticationService.require_step_up_auth(context_high) is True

    context_low = {
        "device_changed": True
    }
    # 15
    assert RiskBasedAuthenticationService.calculate_risk_score(context_low) == 15.0
    assert RiskBasedAuthenticationService.require_step_up_auth(context_low) is False


def test_concurrent_session_limits():
    """Asserts session limits are respected and old sessions get marked revoked."""
    db_mock = MagicMock()
    
    # Mocking 6 active sessions (limit is 5)
    mock_sessions = []
    for i in range(6):
        session = MagicMock()
        session.is_revoked = False
        session.created_at = datetime.now() + timedelta(minutes=i)
        mock_sessions.append(session)
        
    db_mock.scalars.return_value.all.return_value = mock_sessions
    
    enforce_concurrent_session_limits(db_mock, uuid.uuid4(), limit=5)
    
    # Oldest 2 sessions must be marked as revoked
    assert mock_sessions[0].is_revoked is True
    assert mock_sessions[1].is_revoked is True
    assert mock_sessions[2].is_revoked is False


def test_data_classification_labels():
    """Validates classification label mapping schema."""
    assert DataGovernanceService.get_classification("resume") == "Confidential"
    assert DataGovernanceService.get_classification("security_log") == "Restricted"
    assert DataGovernanceService.get_classification("job_public") == "Public"


def test_retention_sweep_precedence():
    """Asserts retention sweep checks legal hold status before sweeping."""
    db_mock = MagicMock()
    company_id = uuid.uuid4()
    
    # 1. Company with Legal Hold active should bypass sweep
    db_mock.execute.return_value.fetchone.return_value = (True,)
    res = DataGovernanceService.run_retention_sweep(db_mock, company_id)
    assert res["status"] == "bypassed"
    assert res["reason"] == "active_legal_hold"


def test_envelope_encryption_service():
    """Verifies AES-256-GCM envelope encryption and decryption payload loops."""
    secret_text = "HighlySecretDBPassword123"
    
    encrypted = EnvelopeEncryptionService.encrypt_secret(secret_text)
    assert "encrypted_data" in encrypted
    assert "encrypted_dek" in encrypted
    assert "nonce" in encrypted
    
    decrypted = EnvelopeEncryptionService.decrypt_secret(encrypted)
    assert decrypted == secret_text


def test_secrets_inventory_alerts():
    """Checks secrets inventories detect expired or overdue rotations."""
    alerts = SecretsInventoryService.check_rotation_health()
    # At least calendar_oauth is configured as overdue in mock inventory
    assert len(alerts) > 0
    assert any(a["secret"] == "calendar_oauth" for a in alerts)


def test_security_monitoring_severities():
    """Tests intrusion detection event risk classifications."""
    alert = SecurityMonitoringService.analyze_event_risk("auth.brute_force", {"ip_address": "8.8.8.8"})
    assert alert["severity"] == "Critical"
    assert alert["blocked"] is True


def test_webhook_signature_rotations():
    """Asserts signature validation supports rollover dual secrets."""
    payload = b"webhook_data_payload_string"
    active_secret = "active_webhook_secret_key"
    prev_secret = "previous_webhook_secret_key"
    
    # Match active secret
    sig_active = WebhookSignatureVerifier.generate_signature(payload, active_secret)
    assert WebhookSignatureVerifier.verify_webhook_signature(payload, sig_active, active_secret, prev_secret) is True
    
    # Match previous secret during rollover
    sig_prev = WebhookSignatureVerifier.generate_signature(payload, prev_secret)
    assert WebhookSignatureVerifier.verify_webhook_signature(payload, sig_prev, active_secret, prev_secret) is True
    
    # Mismatch check
    assert WebhookSignatureVerifier.verify_webhook_signature(payload, "invalid_signature", active_secret, prev_secret) is False


def test_policy_engine_previews():
    """Verifies security policy previews calculate updates and version numbers."""
    preview = PolicyEngineService.preview_policy_update("password_policy", {"min_length": 16})
    assert preview["current_version"] == 3
    assert preview["target_version"] == 4
    assert preview["changes_preview"]["min_length"] == {"from": 12, "to": 16}


def test_backup_verification_restores():
    """Tests automated restorability checks match target schemas."""
    report = BackupVerificationService.run_restorability_test("backup_test_v1")
    assert report["status"] == "Passed"
    assert report["encryption_verified"] is True
