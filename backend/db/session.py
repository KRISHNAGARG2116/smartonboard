from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_tenant_context(db: Session, company_id: str) -> None:
    db.execute(
        text("SELECT set_config('app.company_id', :company_id, true)"),
        {"company_id": company_id},
    )


def set_auth_mode(db: Session) -> None:
    db.execute(text("SELECT set_config('app.auth_mode', 'true', true)"))
