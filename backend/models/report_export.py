import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base

class ReportExport(Base):
    __tablename__ = "report_exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False) # 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'EXPIRED'
    format: Mapped[str] = mapped_column(String(10), nullable=False) # 'CSV', 'XLSX', 'PDF'
    filters: Mapped[dict] = mapped_column(JSONB, default=dict, server_default='{}', nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship()
    user: Mapped["User"] = relationship()
