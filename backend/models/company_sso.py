import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class CompanySSOSettings(Base):
    __tablename__ = "company_sso_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True, unique=True
    )
    sso_provider: Mapped[str] = mapped_column(String(20), default="saml2", nullable=False)
    idp_entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    idp_sso_url: Mapped[str] = mapped_column(String(512), nullable=False)
    idp_x509_cert: Mapped[str | None] = mapped_column(String, nullable=True)
    idp_x509_cert_next: Mapped[str | None] = mapped_column(String, nullable=True)
    idp_x509_cert_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    emergency_access_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    oidc_client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    oidc_client_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    oidc_well_known: Mapped[str | None] = mapped_column(String(512), nullable=True)
    role_mapping: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    company: Mapped["Company"] = relationship()
