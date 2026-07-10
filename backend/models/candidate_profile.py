import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Boolean, Integer, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resume_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    skills: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict, server_default='{}')
    experience: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list, server_default='[]')
    education: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list, server_default='[]')
    links: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict, server_default='{}')
    languages: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list, server_default='[]')
    availability: Mapped[str | None] = mapped_column(String(255), nullable=True)
    salary_expectations: Mapped[str | None] = mapped_column(String(100), nullable=True)
    work_authorization: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="candidate_profile")
