import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from models.enums import UserRole, AuthProvider


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("company_id", "email", name="uq_users_company_email"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda x: [e.value for e in x]),
        default=UserRole.RECRUITER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    auth_provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider, name="auth_provider", values_callable=lambda x: [e.value for e in x]),
        default=AuthProvider.LOCAL,
        server_default="local",
        nullable=False,
    )
    google_subject_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    google_hosted_domain: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="users")
    sessions: Mapped[list["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    candidate_notes: Mapped[list["CandidateNote"]] = relationship("CandidateNote", back_populates="user", cascade="all, delete-orphan")
    interviews: Mapped[list["Interview"]] = relationship("Interview", back_populates="interviewer", cascade="all, delete-orphan")
    scorecards: Mapped[list["Scorecard"]] = relationship("Scorecard", back_populates="grader", cascade="all, delete-orphan")
    candidate_profile: Mapped["CandidateProfile | None"] = relationship("CandidateProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    verification_tokens: Mapped[list["VerificationToken"]] = relationship("VerificationToken", back_populates="user", cascade="all, delete-orphan")
    candidate_resumes: Mapped[list["CandidateResume"]] = relationship("CandidateResume", back_populates="user", cascade="all, delete-orphan")

    @property
    def phone_verified(self) -> bool:
        if self.role == UserRole.CANDIDATE:
            return self.candidate_profile.phone_verified if self.candidate_profile else False
        return True

    @property
    def company_onboarding_completed(self) -> bool:
        if self.role == UserRole.CANDIDATE:
            return True
        from sqlalchemy.orm import object_session
        session = object_session(self)
        if session:
            from db.session import tenant_context
            with tenant_context(auth_mode="true"):
                company = self.company
        else:
            company = self.company

        if company:
            settings = company.settings or {}


            from core.company_validation import validate_company_profile
            return validate_company_profile(
                name=company.name,
                website=settings.get("website", ""),
                domain=settings.get("domain", ""),
                industry=settings.get("industry", ""),
                company_size=settings.get("company_size", ""),
            )

        return False


