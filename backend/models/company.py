import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from models.enums import CompanyStatus


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    status: Mapped[CompanyStatus] = mapped_column(
        Enum(CompanyStatus, name="company_status", values_callable=lambda x: [e.value for e in x]),
        default=CompanyStatus.ACTIVE,
        nullable=False,
    )
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["User"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    candidate_notes: Mapped[list["CandidateNote"]] = relationship("CandidateNote", back_populates="company", cascade="all, delete-orphan")
    interviews: Mapped[list["Interview"]] = relationship("Interview", back_populates="company", cascade="all, delete-orphan")
    scorecards: Mapped[list["Scorecard"]] = relationship("Scorecard", back_populates="company", cascade="all, delete-orphan")
    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="company", cascade="all, delete-orphan")
    candidate_embeddings: Mapped[list["CandidateEmbedding"]] = relationship("CandidateEmbedding", back_populates="company", cascade="all, delete-orphan")
    webhook_subscriptions: Mapped[list["WebhookSubscription"]] = relationship("WebhookSubscription", back_populates="company", cascade="all, delete-orphan")
    webhook_delivery_logs: Mapped[list["WebhookDeliveryLog"]] = relationship("WebhookDeliveryLog", back_populates="company", cascade="all, delete-orphan")
    ip_whitelists: Mapped[list["CompanyIPWhitelist"]] = relationship("CompanyIPWhitelist", back_populates="company", cascade="all, delete-orphan")
    smtp_settings: Mapped["CompanySMTPSettings"] = relationship("CompanySMTPSettings", back_populates="company", uselist=False, cascade="all, delete-orphan")
    subscription_plan: Mapped["CompanySubscriptionPlan"] = relationship("CompanySubscriptionPlan", back_populates="company", uselist=False, cascade="all, delete-orphan")
    usage_ledger: Mapped["CompanyUsageLedger"] = relationship("CompanyUsageLedger", back_populates="company", uselist=False, cascade="all, delete-orphan")
    usage_histories: Mapped[list["CompanyUsageHistory"]] = relationship("CompanyUsageHistory", back_populates="company", cascade="all, delete-orphan")
    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="company", cascade="all, delete-orphan")
    hris_integrations: Mapped[list["CompanyHRISIntegration"]] = relationship("CompanyHRISIntegration", back_populates="company", cascade="all, delete-orphan")
    onboarding_templates: Mapped[list["OnboardingTemplate"]] = relationship("OnboardingTemplate", back_populates="company", cascade="all, delete-orphan")
    hris_field_mappings: Mapped[list["HRISFieldMapping"]] = relationship("HRISFieldMapping", back_populates="company", cascade="all, delete-orphan")
    sync_metrics: Mapped[list["SyncMetric"]] = relationship("SyncMetric", back_populates="company", cascade="all, delete-orphan")
    dlq_records: Mapped[list["DLQRecord"]] = relationship("DLQRecord", back_populates="company", cascade="all, delete-orphan")
    employee_sync_histories: Mapped[list["EmployeeSyncHistory"]] = relationship("EmployeeSyncHistory", back_populates="company", cascade="all, delete-orphan")
    onboarding_portal_tokens: Mapped[list["OnboardingPortalToken"]] = relationship("OnboardingPortalToken", back_populates="company", cascade="all, delete-orphan")
    onboarding_document_signatures: Mapped[list["OnboardingDocumentSignature"]] = relationship("OnboardingDocumentSignature", back_populates="company", cascade="all, delete-orphan")
    onboarding_task_reminders: Mapped[list["OnboardingTaskReminder"]] = relationship("OnboardingTaskReminder", back_populates="company", cascade="all, delete-orphan")
    onboarding_task_escalations: Mapped[list["OnboardingTaskEscalation"]] = relationship("OnboardingTaskEscalation", back_populates="company", cascade="all, delete-orphan")
    onboarding_activity_logs: Mapped[list["OnboardingActivityLog"]] = relationship("OnboardingActivityLog", back_populates="company", cascade="all, delete-orphan")



