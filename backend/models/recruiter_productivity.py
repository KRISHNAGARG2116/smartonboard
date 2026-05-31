import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class RecruiterProductivityAggregate(Base):
    __tablename__ = "recruiter_productivity_aggregates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    applications_reviewed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidates_advanced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    interviews_scheduled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    offers_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    offers_accepted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("company_id", "recruiter_id", name="uq_recruiter_productivity"),
    )

    company: Mapped["Company"] = relationship()
    recruiter: Mapped["User"] = relationship()
