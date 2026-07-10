import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base

class EmployeeProvisioningRequest(Base):
    __tablename__ = "employee_provisioning_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_name: Mapped[str] = mapped_column(String(100), nullable=False)  # email, slack, teams, github, gitlab, jira, confluence, vpn, cloud_accounts, sso
    account_username: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="pending", server_default="pending", nullable=False
    )  # pending, approved, provisioned, failed, revoked
    depends_on_provisioning_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee_provisioning_requests.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship("Company")
    employee: Mapped["Employee"] = relationship("Employee")
    depends_on: Mapped["EmployeeProvisioningRequest | None"] = relationship(
        "EmployeeProvisioningRequest", remote_side=[id], backref="dependents"
    )
