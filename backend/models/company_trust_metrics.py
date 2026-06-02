import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Float, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class CompanyTrustMetrics(Base):
    __tablename__ = "company_trust_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    hiring_history_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    interview_completion_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    candidate_complaint_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    offer_acceptance_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="trust_metrics")
