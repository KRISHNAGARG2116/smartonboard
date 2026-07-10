import uuid
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base

class OnboardingTaskDependency(Base):
    __tablename__ = "onboarding_task_dependencies"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("onboarding_tasks.id", ondelete="CASCADE"), primary_key=True
    )
    depends_on_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("onboarding_tasks.id", ondelete="CASCADE"), primary_key=True
    )
