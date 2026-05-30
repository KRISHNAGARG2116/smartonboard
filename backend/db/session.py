import contextvars
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Connection, Engine
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

import sys

# Thread-safe and async-safe context variables
tenant_id_var = contextvars.ContextVar("tenant_id", default="")
auth_mode_var = contextvars.ContextVar("auth_mode", default="false")


@contextmanager
def tenant_context(tenant_id: str = "", auth_mode: str = "false") -> Generator[None, None, None]:
    t_token = tenant_id_var.set(tenant_id)
    a_token = auth_mode_var.set(auth_mode)
    try:
        yield
    finally:
        tenant_id_var.reset(t_token)
        auth_mode_var.reset(a_token)


def _apply_rls_context(connection) -> None:
    # If the dialect is not initialized yet (e.g. during first connect checks), skip
    if getattr(connection.dialect, "server_version_info", None) is None:
        return

    tenant_id = tenant_id_var.get()
    auth_mode = auth_mode_var.get()

    sys.stderr.write(f"RCA_DEBUG: tenant_id={tenant_id!r}, auth_mode={auth_mode!r}\n")

    # Execute directly on the SQLAlchemy connection within the active session
    connection.execute(
        text("SELECT set_config('app.company_id', :company_id, false)"),
        {"company_id": tenant_id},
    )
    connection.execute(
        text("SELECT set_config('app.auth_mode', :auth_mode, false)"),
        {"auth_mode": auth_mode},
    )


# Hook 1: Apply RLS context on transaction boundary
@event.listens_for(Session, "after_begin")
def set_rls_context_on_begin(session, transaction, connection):
    _apply_rls_context(connection)


# Hook 2: Apply RLS context on statement execution if ContextVars changed
@event.listens_for(Engine, "before_cursor_execute")
def set_rls_context_on_execute(conn, cursor, statement, parameters, context, executemany):
    # Avoid infinite recursion on our own set_config queries
    if "set_config" in statement:
        return
    _apply_rls_context(conn)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_tenant_context(db: Session, company_id: str) -> None:
    tenant_id_var.set(company_id)
    connection = db.connection()
    _apply_rls_context(connection)


def set_auth_mode(db: Session) -> None:
    auth_mode_var.set("true")
    connection = db.connection()
    _apply_rls_context(connection)
