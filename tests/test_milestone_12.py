"""
Milestone 12: Identity Layer - Integration Tests

Tests cover all exit criteria:
- Candidate Registration
- Candidate Login
- Candidate JWT
- Recruiter Domain Validation
- Verification Tokens
- Candidate Profile
- Audit Events
- Candidate Authorization Policies
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Domain Validation Unit Tests (no database needed)
# ---------------------------------------------------------------------------

class TestDomainValidation:
    """Test the public mail host blacklist and DNS/MX validation logic."""

    def test_public_mail_hosts_blocked(self):
        from core.domain_validation import is_public_mail_host

        assert is_public_mail_host("user@gmail.com") is True
        assert is_public_mail_host("user@GMAIL.COM") is True
        assert is_public_mail_host("user@yahoo.com") is True
        assert is_public_mail_host("user@hotmail.com") is True
        assert is_public_mail_host("user@outlook.com") is True
        assert is_public_mail_host("user@protonmail.com") is True
        assert is_public_mail_host("user@icloud.com") is True

    def test_corporate_email_allowed(self):
        from core.domain_validation import is_public_mail_host

        assert is_public_mail_host("user@acmecorp.com") is False
        assert is_public_mail_host("recruiter@bigcompany.io") is False
        assert is_public_mail_host("hr@startup.co") is False

    @patch("core.domain_validation.dns.resolver.resolve")
    def test_domain_exists_with_mx(self, mock_resolve):
        """Domain with valid A and MX records → domain_exists=True, mx_verified=True."""
        from core.domain_validation import validate_domain_dns

        mock_mx_record = MagicMock()
        mock_mx_record.exchange = "mail.example.com."

        def side_effect(domain, rtype):
            if rtype == "A":
                return MagicMock()
            elif rtype == "MX":
                return [mock_mx_record]
            return MagicMock()

        mock_resolve.side_effect = side_effect

        result = validate_domain_dns("user@example.com")
        assert result["domain"] == "example.com"
        assert result["domain_exists"] is True
        assert result["mx_verified"] is True
        assert result["error"] is None
        assert len(result["mx_records"]) > 0

    @patch("core.domain_validation.dns.resolver.resolve")
    def test_domain_does_not_exist(self, mock_resolve):
        """NXDOMAIN → error set, domain_exists=False."""
        import dns.resolver
        from core.domain_validation import validate_domain_dns

        mock_resolve.side_effect = dns.resolver.NXDOMAIN()

        result = validate_domain_dns("user@nonexistent.xyz")
        assert result["domain_exists"] is False
        assert result["error"] is not None
        assert "does not exist" in result["error"]

    @patch("core.domain_validation.dns.resolver.resolve")
    def test_domain_exists_no_mx(self, mock_resolve):
        """Domain resolves A but MX fails → domain_exists=True, mx_verified=False (pending)."""
        import dns.resolver
        from core.domain_validation import validate_domain_dns

        def side_effect(domain, rtype):
            if rtype == "A":
                return MagicMock()
            elif rtype == "MX":
                raise dns.resolver.NoAnswer()
            return MagicMock()

        mock_resolve.side_effect = side_effect

        result = validate_domain_dns("user@nomx-domain.com")
        assert result["domain_exists"] is True
        assert result["mx_verified"] is False
        assert result["error"] is None


# ---------------------------------------------------------------------------
# Auth Provider Unit Tests
# ---------------------------------------------------------------------------

class TestAuthProviders:
    """Test the abstract auth provider layer."""

    def test_mock_otp_provider(self):
        from core.auth_providers import MockOTPProvider

        provider = MockOTPProvider()
        assert provider.provider_name() == "mock"
        assert provider.send_otp("+1234567890", "123456") is True

    def test_otp_generation(self):
        from core.auth_providers import DBVerificationTokenProvider

        code = DBVerificationTokenProvider.generate_otp()
        assert len(code) == 6
        assert code.isdigit()
        assert 100000 <= int(code) <= 999999

    def test_token_hashing(self):
        from core.auth_providers import DBVerificationTokenProvider

        hashed = DBVerificationTokenProvider.hash_token("123456")
        expected = hashlib.sha256("123456".encode("utf-8")).hexdigest()
        assert hashed == expected

    def test_get_otp_provider_mock(self):
        """Without Twilio env vars, should return MockOTPProvider."""
        from core.auth_providers import get_otp_provider, MockOTPProvider

        with patch.dict("os.environ", {}, clear=True):
            provider = get_otp_provider()
            assert isinstance(provider, MockOTPProvider)


# ---------------------------------------------------------------------------
# Schema Validation Tests
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    """Test Pydantic schema changes for Milestone 12."""

    def test_user_response_optional_company_id(self):
        from schemas.auth import UserResponse

        # Candidate with no company_id
        resp = UserResponse(
            id=uuid.uuid4(),
            email="candidate@example.com",
            full_name="Test Candidate",
            role="candidate",
            company_id=None,
        )
        assert resp.company_id is None

        # Recruiter with company_id
        company_id = uuid.uuid4()
        resp2 = UserResponse(
            id=uuid.uuid4(),
            email="recruiter@corp.com",
            full_name="Test Recruiter",
            role="owner",
            company_id=company_id,
        )
        assert resp2.company_id == company_id

    def test_candidate_register_request_validation(self):
        from schemas.auth import CandidateRegisterRequest

        # Valid
        req = CandidateRegisterRequest(
            email="test@example.com",
            password="securepass123",
            full_name="Test User",
            phone_number="+15550199333",
        )
        assert req.email == "test@example.com"

        # Invalid - password too short
        with pytest.raises(Exception):
            CandidateRegisterRequest(
                email="test@example.com",
                password="short",
                full_name="Test User",
                phone_number="+15550199333",
            )

    def test_candidate_otp_verify_request(self):
        from schemas.auth import CandidateOTPVerifyRequest

        req = CandidateOTPVerifyRequest(
            email="test@example.com",
            code="123456",
        )
        assert req.code == "123456"

        # Code too short
        with pytest.raises(Exception):
            CandidateOTPVerifyRequest(
                email="test@example.com",
                code="123",
            )


# ---------------------------------------------------------------------------
# Model Tests (structure verification)
# ---------------------------------------------------------------------------

class TestModels:
    """Test that Milestone 12 models exist and have correct structure."""

    def test_verification_token_model(self):
        from models.verification_token import VerificationToken
        assert hasattr(VerificationToken, "token_hash")
        assert hasattr(VerificationToken, "token_type")
        assert hasattr(VerificationToken, "expires_at")
        assert hasattr(VerificationToken, "attempts")
        assert hasattr(VerificationToken, "consumed_at")
        assert VerificationToken.__tablename__ == "verification_tokens"

    def test_candidate_profile_model(self):
        from models.candidate_profile import CandidateProfile
        assert hasattr(CandidateProfile, "user_id")
        assert hasattr(CandidateProfile, "full_name")
        assert hasattr(CandidateProfile, "phone_verified")
        assert hasattr(CandidateProfile, "email_verified")
        assert CandidateProfile.__tablename__ == "candidate_profiles"

    def test_company_trust_metrics_model(self):
        from models.company_trust_metrics import CompanyTrustMetrics
        assert hasattr(CompanyTrustMetrics, "company_id")
        assert hasattr(CompanyTrustMetrics, "hiring_history_count")
        assert hasattr(CompanyTrustMetrics, "interview_completion_rate")
        assert hasattr(CompanyTrustMetrics, "candidate_complaint_rate")
        assert hasattr(CompanyTrustMetrics, "offer_acceptance_rate")
        assert CompanyTrustMetrics.__tablename__ == "company_trust_metrics"

    def test_application_snapshot_model(self):
        from models.application_snapshot import ApplicationSnapshot
        assert hasattr(ApplicationSnapshot, "application_id")
        assert hasattr(ApplicationSnapshot, "resume_snapshot")
        assert hasattr(ApplicationSnapshot, "candidate_snapshot")
        assert ApplicationSnapshot.__tablename__ == "application_snapshots"

    def test_user_role_candidate_exists(self):
        from models.enums import UserRole
        assert UserRole.CANDIDATE.value == "candidate"

    def test_verification_state_enum(self):
        from models.enums import VerificationState
        assert VerificationState.PENDING_VERIFICATION.value == "pending_verification"
        assert VerificationState.VERIFIED_RECRUITER.value == "verified_recruiter"
        assert VerificationState.VERIFIED_COMPANY.value == "verified_company"
        assert VerificationState.SUSPENDED.value == "suspended"

    def test_trust_level_enum(self):
        from models.enums import TrustLevel
        assert TrustLevel.NONE.value == "none"
        assert TrustLevel.TRUSTED_EMPLOYER.value == "trusted_employer"

    def test_company_verification_fields(self):
        from models.company import Company
        assert hasattr(Company, "verification_state")
        assert hasattr(Company, "trust_level")
        assert hasattr(Company, "domain_verified")
        assert hasattr(Company, "website_verified")
        assert hasattr(Company, "identity_verified")

    def test_user_nullable_company_id(self):
        from models.user import User
        col = User.__table__.columns["company_id"]
        assert col.nullable is True

    def test_user_candidate_profile_relationship(self):
        from models.user import User
        # Check that the relationship exists
        mapper = User.__mapper__
        assert "candidate_profile" in mapper.relationships
        assert "verification_tokens" in mapper.relationships


# ---------------------------------------------------------------------------
# Dependency Tests
# ---------------------------------------------------------------------------

class TestDependencies:
    """Test that new FastAPI dependency functions and type aliases exist."""

    def test_current_candidate_alias_exists(self):
        from api.deps import CurrentCandidate
        assert CurrentCandidate is not None

    def test_get_current_candidate_function_exists(self):
        from api.deps import get_current_candidate
        import inspect
        assert inspect.isfunction(get_current_candidate)

    def test_role_checker_allows_candidate(self):
        from api.deps import RoleChecker
        from models.enums import UserRole
        checker = RoleChecker([UserRole.CANDIDATE])
        assert UserRole.CANDIDATE in checker.allowed_roles


# ---------------------------------------------------------------------------
# Route Registration Tests
# ---------------------------------------------------------------------------

class TestRouteRegistration:
    """Test that all Milestone 12 routes are registered on the auth router."""

    def test_candidate_routes_registered(self):
        from api.auth import router

        route_paths = [r.path for r in router.routes]

        assert "/auth/register/candidate" in route_paths
        assert "/auth/login/candidate" in route_paths
        assert "/auth/candidate/email/send-otp" in route_paths
        assert "/auth/candidate/email/verify-otp" in route_paths
        assert "/auth/candidate/me" in route_paths


# ---------------------------------------------------------------------------
# Exit Criteria Verification
# ---------------------------------------------------------------------------

class TestMilestone12ExitCriteria:
    """
    Meta-test that verifies all Milestone 12 exit criteria are met
    by checking that the necessary code artifacts exist.
    """

    def test_candidate_registration_exists(self):
        """Exit: Candidate Registration Exists"""
        from api.auth import register_candidate
        assert callable(register_candidate)

    def test_candidate_login_exists(self):
        """Exit: Candidate Login Exists"""
        from api.auth import login_candidate
        assert callable(login_candidate)

    def test_candidate_jwt_exists(self):
        """Exit: Candidate JWT Exists"""
        from core.security import create_access_token
        # Verify we can create a token with candidate role and no company_id
        token = create_access_token(
            str(uuid.uuid4()),
            {"company_id": None, "role": "candidate", "email": "c@example.com", "session_id": str(uuid.uuid4())}
        )
        assert token is not None
        assert len(token) > 0

    def test_recruiter_domain_validation_exists(self):
        """Exit: Recruiter Domain Validation Exists"""
        from core.domain_validation import is_public_mail_host, validate_domain_dns
        assert callable(is_public_mail_host)
        assert callable(validate_domain_dns)

    def test_verification_tokens_exist(self):
        """Exit: Verification Tokens Exist"""
        from models.verification_token import VerificationToken
        from core.auth_providers import DBVerificationTokenProvider
        assert VerificationToken is not None
        assert callable(DBVerificationTokenProvider.create_token)
        assert callable(DBVerificationTokenProvider.verify_token)

    def test_candidate_profile_exists(self):
        """Exit: Candidate Profile Exists"""
        from models.candidate_profile import CandidateProfile
        assert CandidateProfile.__tablename__ == "candidate_profiles"

    def test_audit_events_exist(self):
        """Exit: Audit Events Exist"""
        from core.audit import log_audit_event
        assert callable(log_audit_event)

    def test_candidate_authorization_policies_exist(self):
        """Exit: Candidate Authorization Policies Exist"""
        from api.deps import get_current_candidate, CurrentCandidate
        assert callable(get_current_candidate)
        assert CurrentCandidate is not None

    def test_abstract_auth_provider_layer_exists(self):
        """Exit: Abstract Auth Provider Layer"""
        from core.auth_providers import OTPDeliveryProvider, MockOTPProvider, TwilioOTPProvider
        from core.auth_providers import get_otp_provider, DBVerificationTokenProvider
        assert OTPDeliveryProvider is not None
        assert callable(get_otp_provider)
