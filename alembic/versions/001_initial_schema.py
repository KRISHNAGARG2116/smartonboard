"""Initial schema with tenant RLS

Revision ID: 001
Revises:
Create Date: 2026-05-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

company_status = postgresql.ENUM("active", "suspended", name="company_status", create_type=False)
user_role = postgresql.ENUM("owner", "recruiter", name="user_role", create_type=False)
job_status = postgresql.ENUM("draft", "open", "closed", name="job_status", create_type=False)
application_status = postgresql.ENUM(
    "submitted", "screening", "interview", "offer", "hired", "rejected",
    name="application_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    company_status.create(op.get_bind(), checkfirst=True)
    user_role.create(op.get_bind(), checkfirst=True)
    job_status.create(op.get_bind(), checkfirst=True)
    application_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("status", company_status, nullable=False, server_default="active"),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_companies_slug", "companies", ["slug"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="recruiter"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("company_id", "email", name="uq_users_company_email"),
    )
    op.create_index("ix_users_company_id", "users", ["company_id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("department", sa.String(100), nullable=False, server_default="General"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", job_status, nullable=False, server_default="draft"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_jobs_company_id", "jobs", ["company_id"])
    op.create_index("ix_jobs_company_status", "jobs", ["company_id", "status"])

    op.create_table(
        "candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("company_id", "email", name="uq_candidates_company_email"),
    )
    op.create_index("ix_candidates_company_id", "candidates", ["company_id"])

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", application_status, nullable=False, server_default="submitted"),
        sa.Column("source", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_applications_job_candidate"),
    )
    op.create_index("ix_applications_company_id", "applications", ["company_id"])
    op.create_index("ix_applications_job_id", "applications", ["job_id"])
    op.create_index("ix_applications_company_status", "applications", ["company_id", "status"])

    # Row-level security
    for table in ("companies", "users", "jobs", "candidates", "applications"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY tenant_isolation_companies ON companies
        FOR ALL
        USING (id = NULLIF(current_setting('app.company_id', true), '')::uuid)
        WITH CHECK (id = NULLIF(current_setting('app.company_id', true), '')::uuid)
    """)

    for table in ("users", "jobs", "candidates", "applications"):
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            FOR ALL
            USING (
                company_id = NULLIF(current_setting('app.company_id', true), '')::uuid
                OR current_setting('app.auth_mode', true) = 'true'
            )
            WITH CHECK (
                company_id = NULLIF(current_setting('app.company_id', true), '')::uuid
                OR current_setting('app.auth_mode', true) = 'true'
            )
        """)

    # Allow bootstrap inserts when tenant context is not set (registration)
    op.execute("""
        CREATE POLICY companies_bootstrap_insert ON companies
        FOR INSERT
        WITH CHECK (current_setting('app.company_id', true) IS NULL OR current_setting('app.company_id', true) = '')
    """)
    op.execute("""
        CREATE POLICY users_bootstrap_insert ON users
        FOR INSERT
        WITH CHECK (
            current_setting('app.company_id', true) IS NOT NULL
            AND current_setting('app.company_id', true) != ''
        )
    """)


def downgrade() -> None:
    for table in ("applications", "candidates", "jobs", "users", "companies"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
    op.execute("DROP POLICY IF EXISTS companies_bootstrap_insert ON companies")
    op.execute("DROP POLICY IF EXISTS users_bootstrap_insert ON users")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_companies ON companies")

    op.drop_table("applications")
    op.drop_table("candidates")
    op.drop_table("jobs")
    op.drop_table("users")
    op.drop_table("companies")

    application_status.drop(op.get_bind(), checkfirst=True)
    job_status.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
    company_status.drop(op.get_bind(), checkfirst=True)
