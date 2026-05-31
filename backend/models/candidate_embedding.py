import os
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, ARRAY, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


def get_embedding_column_type():
    """Dynamically returns BGE 384 Vector type if pgvector is available, otherwise falls back to ARRAY(Float)."""
    if os.getenv("USE_PGVECTOR", "true").lower() == "false":
        return ARRAY(Float)
    try:
        from pgvector.sqlalchemy import Vector
        return Vector(384)
    except ImportError:
        return ARRAY(Float)


class CandidateEmbedding(Base):
    __tablename__ = "candidate_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "candidate_id", "chunk_index", 
            name="uq_candidate_embeddings_company_candidate_chunk"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_embedding: Mapped[list[float]] = mapped_column(get_embedding_column_type(), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="huggingface")
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False, default="BAAI/bge-small-en-v1.5")
    embedding_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="candidate_embeddings")
    candidate: Mapped["Candidate"] = relationship(back_populates="candidate_embeddings")
