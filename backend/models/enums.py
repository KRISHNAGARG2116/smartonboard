import enum


class UserRole(str, enum.Enum):
    OWNER = "owner"
    RECRUITER = "recruiter"


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
