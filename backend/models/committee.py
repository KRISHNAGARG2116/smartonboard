import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, Numeric, ARRAY, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base

class ScorecardTemplate(Base):
    __tablename__ = "scorecard_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship()
    skills: Mapped[list["ScorecardTemplateSkill"]] = relationship(
        "ScorecardTemplateSkill", back_populates="template", cascade="all, delete-orphan"
    )

class ScorecardTemplateSkill(Base):
    __tablename__ = "scorecard_template_skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    scorecard_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scorecard_templates.id", ondelete="CASCADE"), nullable=False
    )
    skill_key: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    template: Mapped["ScorecardTemplate"] = relationship("ScorecardTemplate", back_populates="skills")

class HiringCommittee(Base):
    __tablename__ = "hiring_committees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quorum_percentage: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    min_score_threshold: Mapped[float] = mapped_column(Numeric(3, 2), default=3.00, nullable=False)
    consensus_sd_threshold: Mapped[float] = mapped_column(Numeric(3, 2), default=0.75, nullable=False)
    allow_veto: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    veto_skill_keys: Mapped[list[str]] = mapped_column(ARRAY(String(100)), default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    company: Mapped["Company"] = relationship()
    members: Mapped[list["HiringCommitteeMember"]] = relationship(
        "HiringCommitteeMember", back_populates="committee", cascade="all, delete-orphan"
    )

class HiringCommitteeMember(Base):
    __tablename__ = "hiring_committee_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    hiring_committee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hiring_committees.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), default="reviewer", nullable=False)
    reviewer_weight: Mapped[float] = mapped_column(Numeric(4, 2), default=1.00, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    committee: Mapped["HiringCommittee"] = relationship("HiringCommittee", back_populates="members")
    user: Mapped["User"] = relationship("User")

class CommitteeReview(Base):
    __tablename__ = "committee_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hiring_committee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hiring_committees.id", ondelete="CASCADE"), nullable=False
    )
    scorecard_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scorecard_templates.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    average_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    reconciliation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship()
    application: Mapped["Application"] = relationship()
    committee: Mapped["HiringCommittee"] = relationship("HiringCommittee")
    template: Mapped["ScorecardTemplate"] = relationship("ScorecardTemplate")
    reviewers: Mapped[list["CommitteeReviewReviewer"]] = relationship(
        "CommitteeReviewReviewer", back_populates="review", cascade="all, delete-orphan"
    )
    scorecards: Mapped[list["Scorecard"]] = relationship("Scorecard", back_populates="committee_review")

class CommitteeReviewReviewer(Base):
    __tablename__ = "committee_review_reviewers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    committee_review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("committee_reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), default="reviewer", nullable=False)
    reviewer_weight: Mapped[float] = mapped_column(Numeric(4, 2), default=1.00, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    review: Mapped["CommitteeReview"] = relationship("CommitteeReview", back_populates="reviewers")
    user: Mapped["User"] = relationship("User")
