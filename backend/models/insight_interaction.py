import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class AIInsightInteraction(Base):
    __tablename__ = "ai_insight_interactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(30), nullable=False) # 'VIEWED', 'REGENERATED', 'OVERRIDDEN', 'ACCEPTED', 'DISMISSED'
    recommendation_snapshot: Mapped[str | None] = mapped_column(String(20), nullable=True) # 'HIRE', 'NO_HIRE'
    recruiter_decision: Mapped[str | None] = mapped_column(String(30), nullable=True) # 'HIRE', 'NO_HIRE'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship()
    user: Mapped["User"] = relationship()
    application: Mapped["Application"] = relationship()
