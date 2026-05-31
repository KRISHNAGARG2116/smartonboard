import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class AIRecruiterInsight(Base):
    __tablename__ = "ai_recruiter_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str | None] = mapped_column(String, nullable=True)
    generation_status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_reason: Mapped[dict] = mapped_column(JSONB, default=dict, server_default='{}', nullable=False)
    prompt_version: Mapped[int] = mapped_column(default=1, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    candidate_embedding_ids: Mapped[list] = mapped_column(JSONB, default=list, server_default='[]', nullable=False)
    scorecard_ids: Mapped[list] = mapped_column(JSONB, default=list, server_default='[]', nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("application_id", "insight_type", name="uq_app_insight_type"),
    )

    company: Mapped["Company"] = relationship()
    application: Mapped["Application"] = relationship()
