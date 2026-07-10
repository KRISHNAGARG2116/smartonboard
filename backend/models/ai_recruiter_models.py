import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Text, func, Integer, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base


class RecruiterChatSession(Base):
    __tablename__ = "recruiter_chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_name: Mapped[str] = mapped_column(Text, nullable=False)
    current_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    current_pool_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("talent_pools.id", ondelete="SET NULL"), nullable=True)
    current_filters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    selected_candidate_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    context_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    expires_after: Mapped[int] = mapped_column(Integer, nullable=False, default=86400, server_default="86400") # context expiry in seconds
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    company = relationship("Company")
    recruiter = relationship("User")
    current_job = relationship("Job")
    current_pool = relationship("TalentPool")
    messages = relationship("RecruiterChatMessage", back_populates="session", cascade="all, delete-orphan")


class RecruiterChatMessage(Base):
    __tablename__ = "recruiter_chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recruiter_chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)  # user, assistant
    message: Mapped[str] = mapped_column(Text, nullable=False)
    execution_graph: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Branching planning nodes
    plan_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    plan_confidence_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    permission_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    execution_context_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tool_calls: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, server_default=func.now(), nullable=False)

    session = relationship("RecruiterChatSession", back_populates="messages")


class AICopilotCallLog(Base):
    __tablename__ = "ai_copilot_call_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recruiter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tools_used: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    planning_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    approval_delay_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    token_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    plan_complexity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    user_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)  # helpful, incorrect, incomplete, hallucinated, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, server_default=func.now(), nullable=False)

    company = relationship("Company")
    recruiter = relationship("User")


class AgentPlannerTemplate(Base):
    __tablename__ = "agent_planner_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    template_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    saved_graph: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    company = relationship("Company")
    creator = relationship("User")
