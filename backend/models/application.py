import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func, Table, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from models.enums import ApplicationStatus


application_secondary_recruiters = Table(
    "application_secondary_recruiters",
    Base.metadata,
    Column("application_id", UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

application_watchers = Table(
    "application_watchers",
    Base.metadata,
    Column("application_id", UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


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
    current_stage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stage_definitions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(50), default="pipeline", nullable=False)
    committee_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    match_score: Mapped[float | None] = mapped_column(nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="applications")
    job: Mapped["Job"] = relationship(back_populates="applications")
    candidate: Mapped["Candidate"] = relationship(back_populates="applications")
    current_stage: Mapped["StageDefinition | None"] = relationship("StageDefinition")
    candidate_notes: Mapped[list["CandidateNote"]] = relationship("CandidateNote", back_populates="application", cascade="all, delete-orphan")
    interviews: Mapped[list["Interview"]] = relationship("Interview", back_populates="application", cascade="all, delete-orphan")
    scorecards: Mapped[list["Scorecard"]] = relationship("Scorecard", back_populates="application", cascade="all, delete-orphan")
    offer: Mapped["Offer"] = relationship("Offer", back_populates="application", cascade="all, delete-orphan", uselist=False)
    snapshot: Mapped["ApplicationSnapshot | None"] = relationship("ApplicationSnapshot", back_populates="application", uselist=False, cascade="all, delete-orphan")
    
    owner: Mapped["User | None"] = relationship("User", foreign_keys=[owner_id])
    secondary_recruiters: Mapped[list["User"]] = relationship(
        "User", secondary=application_secondary_recruiters, backref="coordinated_applications"
    )
    watchers: Mapped[list["User"]] = relationship(
        "User", secondary=application_watchers, backref="watched_applications"
    )
    events: Mapped[list["ApplicationEvent"]] = relationship(
        "ApplicationEvent", back_populates="application", cascade="all, delete-orphan", order_by="ApplicationEvent.created_at"
    )
