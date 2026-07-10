import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base

class EmployeePolicyAcknowledgement(Base):
    __tablename__ = "employee_policy_acknowledgements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    policy_name: Mapped[str] = mapped_column(String(100), nullable=False)  # security_policy, code_of_conduct, privacy_policy, acceptable_use, remote_work_policy
    policy_version: Mapped[str] = mapped_column(String(30), default="1.0", nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=False)
    digital_signature: Mapped[str] = mapped_column(String(255), nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    company: Mapped["Company"] = relationship("Company")
    employee: Mapped["Employee"] = relationship("Employee")
