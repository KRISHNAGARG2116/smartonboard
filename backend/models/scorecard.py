import uuid
from datetime import datetime

sa_types_jsonb = None
try:
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:
    pass

from sqlalchemy import DateTime, ForeignKey, String, Text, func, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Scorecard(Base):
    __tablename__ = "scorecards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    grader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    criteria_scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    overall_recommendation: Mapped[str] = mapped_column(String(50), nullable=False) # strong_yes, yes, no, strong_no
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    committee_review_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("committee_reviews.id", ondelete="SET NULL"), nullable=True, index=True
    )
    weighted_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="scorecards")
    application: Mapped["Application"] = relationship(back_populates="scorecards")
    interview: Mapped["Interview"] = relationship(back_populates="scorecard")
    grader: Mapped["User"] = relationship(back_populates="scorecards")
    committee_review: Mapped["CommitteeReview | None"] = relationship(back_populates="scorecards")

