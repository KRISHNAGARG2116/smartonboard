import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from models.enums import ApplicationStatus


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_applications_job_candidate"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status", values_callable=lambda x: [e.value for e in x]),
        default=ApplicationStatus.SUBMITTED,
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(50), default="pipeline", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="applications")
    job: Mapped["Job"] = relationship(back_populates="applications")
    candidate: Mapped["Candidate"] = relationship(back_populates="applications")
    candidate_notes: Mapped[list["CandidateNote"]] = relationship("CandidateNote", back_populates="application", cascade="all, delete-orphan")
    interviews: Mapped[list["Interview"]] = relationship("Interview", back_populates="application", cascade="all, delete-orphan")
    scorecards: Mapped[list["Scorecard"]] = relationship("Scorecard", back_populates="application", cascade="all, delete-orphan")
