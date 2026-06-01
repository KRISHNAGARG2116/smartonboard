import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Integer, Text, Boolean, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class CompanyIPWhitelist(Base):
    __tablename__ = "company_ip_whitelists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cidr_block: Mapped[str] = mapped_column(String(45), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    company: Mapped["Company"] = relationship(back_populates="ip_whitelists")


class CompanySMTPSettings(Base):
    __tablename__ = "company_smtp_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True, unique=True
    )
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(String(512), nullable=False)
    iv: Mapped[str] = mapped_column(String(32), nullable=False)
    tag: Mapped[str] = mapped_column(String(32), nullable=False)
    key_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    last_verification_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship(back_populates="smtp_settings")


class CompanySubscriptionPlan(Base):
    __tablename__ = "company_subscription_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True, unique=True
    )
    tier_name: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    candidate_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    job_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    ai_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    webhook_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    pending_downgrade_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pending_downgrade_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    billing_cycle_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    billing_cycle_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship(back_populates="subscription_plan")


class CompanyUsageLedger(Base):
    __tablename__ = "company_usage_ledgers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True, unique=True
    )
    candidates_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_jobs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_screenings_run: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    webhooks_dispatched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship(back_populates="usage_ledger")


class CompanyUsageHistory(Base):
    __tablename__ = "company_usage_histories"

    __table_args__ = (
        Index("ix_company_usage_histories_reporting", "company_id", "created_at", "tier_name", unique=False),
        Index("ix_company_usage_histories_billing_period", "company_id", "billing_period_start", "billing_period_end", unique=False),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tier_name: Mapped[str] = mapped_column(String(50), nullable=False)
    billing_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    billing_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    candidates_processed: Mapped[int] = mapped_column(Integer, nullable=False)
    active_jobs_count: Mapped[int] = mapped_column(Integer, nullable=False)
    ai_screenings_run: Mapped[int] = mapped_column(Integer, nullable=False)
    webhooks_dispatched: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    company: Mapped["Company"] = relationship(back_populates="usage_histories")
