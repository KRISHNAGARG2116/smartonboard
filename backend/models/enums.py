import enum


class UserRole(str, enum.Enum):
    OWNER = "owner"
    RECRUITER = "recruiter"
    CANDIDATE = "candidate"


class VerificationState(str, enum.Enum):
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED_RECRUITER = "verified_recruiter"
    VERIFIED_COMPANY = "verified_company"
    SUSPENDED = "suspended"


class TrustLevel(str, enum.Enum):
    NONE = "none"
    TRUSTED_EMPLOYER = "trusted_employer"


class CompanyStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"


class ApplicationStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class InsightGenerationStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
