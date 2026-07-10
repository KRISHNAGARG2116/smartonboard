import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base

class EmployeeOnboardingAudit(Base):
    __tablename__ = "employee_onboarding_audits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)  # system, employee, manager, hr
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # "Offer Accepted", "Employee Created", "NDA Signed", "Laptop Ordered", "GitHub Provisioned", "Orientation Completed", "Buddy Assigned", "Onboarding Finished"
    details: Mapped[dict] = mapped_column(JSONB, default=dict, server_default='{}', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    company: Mapped["Company"] = relationship("Company")
    employee: Mapped["Employee"] = relationship("Employee")
    actor: Mapped["User | None"] = relationship("User")
