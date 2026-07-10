import uuid
from datetime import date, datetime
import sqlalchemy as sa
from sqlalchemy import Date, DateTime, ForeignKey, String, Boolean, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base

class CompanyHRISIntegration(Base):
    __tablename__ = "company_hris_integrations"
    __table_args__ = (
        UniqueConstraint("company_id", "provider", name="uq_company_hris_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="inactive", nullable=False)
    credentials_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    credentials_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default="now()")

    company: Mapped["Company"] = relationship("Company", back_populates="hris_integrations")


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("company_id", "email", name="uq_employees_company_email"),
        UniqueConstraint("company_id", "employee_number", name="uq_employees_company_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    job_title: Mapped[str] = mapped_column(String(150), nullable=False)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employment_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'full_time', 'part_time', 'contractor', 'intern'
    employee_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="onboarding", nullable=False)  # 'onboarding', 'active', 'suspended', 'terminated'
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    supervisor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True
    )
    hris_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)  # 'pending', 'queued', 'processing', 'synced', 'retrying', 'failed', 'manual_review'
    sync_error: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default="now()")

    company: Mapped["Company"] = relationship("Company", back_populates="employees")
    user: Mapped["User | None"] = relationship("User", foreign_keys=[user_id])

    candidate: Mapped["Candidate | None"] = relationship("Candidate")
    onboarding_workflow: Mapped["OnboardingWorkflow | None"] = relationship("OnboardingWorkflow", back_populates="employee", cascade="all, delete-orphan", uselist=False)
    supervisor: Mapped["Employee | None"] = relationship("Employee", remote_side=[id], backref="subordinates")
    sync_histories: Mapped[list["EmployeeSyncHistory"]] = relationship("EmployeeSyncHistory", back_populates="employee", cascade="all, delete-orphan")


class OnboardingTemplate(Base):
    __tablename__ = "onboarding_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default="now()")

    company: Mapped["Company"] = relationship("Company", back_populates="onboarding_templates")
    tasks: Mapped[list["OnboardingTemplateTask"]] = relationship("OnboardingTemplateTask", back_populates="template", cascade="all, delete-orphan")


class OnboardingTemplateTask(Base):
    __tablename__ = "onboarding_template_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("onboarding_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'document_signature', 'form_filling', 'it_provisioning', 'manual_verification'
    rule_criteria: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default="now()")

    template: Mapped["OnboardingTemplate"] = relationship("OnboardingTemplate", back_populates="tasks")


class OnboardingWorkflow(Base):
    __tablename__ = "onboarding_workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="initiated", nullable=False)  # 'initiated', 'in_progress', 'completed', 'failed'
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default="now()")

    employee: Mapped["Employee"] = relationship("Employee", back_populates="onboarding_workflow")
    tasks: Mapped[list["OnboardingTask"]] = relationship("OnboardingTask", back_populates="workflow", cascade="all, delete-orphan")


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("onboarding_workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)  # 'pending', 'in_progress', 'completed', 'failed', 'skipped'
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assigned_to_role: Mapped[str] = mapped_column(String(50), default="candidate", nullable=False)  # 'candidate', 'recruiter', 'it_admin', 'hr_admin'
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    meta_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    phase: Mapped[str] = mapped_column(String(50), default="preboarding", server_default="preboarding", nullable=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default="now()")


    workflow: Mapped["OnboardingWorkflow"] = relationship("OnboardingWorkflow", back_populates="tasks")
    documents: Mapped[list["OnboardingDocument"]] = relationship("OnboardingDocument", back_populates="task", cascade="all, delete-orphan")


class OnboardingDocument(Base):
    __tablename__ = "onboarding_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("onboarding_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_name: Mapped[str] = mapped_column(String(150), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String, nullable=True)
    signature_status: Mapped[str] = mapped_column(String(50), default="not_required", nullable=False)  # 'not_required', 'pending_candidate', 'pending_company', 'signed', 'declined'
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default="now()")

    task: Mapped["OnboardingTask"] = relationship("OnboardingTask", back_populates="documents")


class OnboardingEventOutbox(Base):
    __tablename__ = "onboarding_event_outbox"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)  # 'employee.created', 'onboarding.task_completed'
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)  # 'pending', 'processed', 'failed'
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default="now()")


class HRISFieldMapping(Base):
    __tablename__ = "hris_field_mappings"
    __table_args__ = (
        UniqueConstraint("company_id", "provider", "local_field", name="uq_hris_field_mapping_local"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    local_field: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_field: Mapped[str] = mapped_column(String(100), nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transform_rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default="now()")

    company: Mapped["Company"] = relationship("Company", back_populates="hris_field_mappings")


class SyncMetric(Base):
    __tablename__ = "sync_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(sa.Double(), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")

    company: Mapped["Company"] = relationship("Company", back_populates="sync_metrics")


class DLQRecord(Base):
    __tablename__ = "dlq_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    outbox_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("onboarding_event_outbox.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="failed", nullable=False)  # 'failed', 'resolved'
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default="now()")

    company: Mapped["Company"] = relationship("Company", back_populates="dlq_records")
    outbox: Mapped["OnboardingEventOutbox"] = relationship("OnboardingEventOutbox")


class EmployeeSyncHistory(Base):
    __tablename__ = "employee_sync_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sync_state: Mapped[str] = mapped_column(String(30), nullable=False)  # 'queued', 'processing', 'retrying', 'synced', 'failed', 'manual_review'
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")

    company: Mapped["Company"] = relationship("Company", back_populates="employee_sync_histories")
    employee: Mapped["Employee"] = relationship("Employee", back_populates="sync_histories")


class OnboardingPortalToken(Base):
    __tablename__ = "onboarding_portal_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    access_scopes: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")

    company: Mapped["Company"] = relationship("Company", back_populates="onboarding_portal_tokens")
    employee: Mapped["Employee"] = relationship("Employee")


class OnboardingDocumentSignature(Base):
    __tablename__ = "onboarding_document_signatures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("onboarding_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=False)
    signer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    signature_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")

    company: Mapped["Company"] = relationship("Company", back_populates="onboarding_document_signatures")
    employee: Mapped["Employee"] = relationship("Employee")
    document: Mapped["OnboardingDocument"] = relationship("OnboardingDocument")


class OnboardingTaskReminder(Base):
    __tablename__ = "onboarding_task_reminders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("onboarding_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_channel: Mapped[str] = mapped_column(String(30), nullable=False)  # 'email', 'slack', 'sms'
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", nullable=False)  # 'scheduled', 'sent', 'cancelled'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")

    company: Mapped["Company"] = relationship("Company", back_populates="onboarding_task_reminders")
    task: Mapped["OnboardingTask"] = relationship("OnboardingTask")


class OnboardingTaskEscalation(Base):
    __tablename__ = "onboarding_task_escalations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("onboarding_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    escalated_to_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    escalation_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="onboarding_task_escalations")
    task: Mapped["OnboardingTask"] = relationship("OnboardingTask")
    escalated_to: Mapped["User"] = relationship("User")


class OnboardingActivityLog(Base):
    __tablename__ = "onboarding_activity_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(30), nullable=False)  # 'candidate', 'employee', 'recruiter', 'system'
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")

    company: Mapped["Company"] = relationship("Company", back_populates="onboarding_activity_logs")
    employee: Mapped["Employee"] = relationship("Employee")
