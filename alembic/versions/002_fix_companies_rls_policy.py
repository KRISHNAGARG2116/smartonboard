"""Fix companies RLS policy to support auth_mode

Revision ID: 002
Revises: 001
Create Date: 2026-05-31
"""

from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop the old restrictive policy
    op.execute("DROP POLICY IF EXISTS tenant_isolation_companies ON companies")

    # 2. Create the updated RLS policy that checks auth_mode
    op.execute("""
        CREATE POLICY tenant_isolation_companies ON companies
        FOR ALL
        USING (
            id = NULLIF(current_setting('app.company_id', true), '')::uuid
            OR current_setting('app.auth_mode', true) = 'true'
        )
        WITH CHECK (
            id = NULLIF(current_setting('app.company_id', true), '')::uuid
            OR current_setting('app.auth_mode', true) = 'true'
        )
    """)


def downgrade() -> None:
    # Restore the original restrictive policy
    op.execute("DROP POLICY IF EXISTS tenant_isolation_companies ON companies")
    op.execute("""
        CREATE POLICY tenant_isolation_companies ON companies
        FOR ALL
        USING (id = NULLIF(current_setting('app.company_id', true), '')::uuid)
        WITH CHECK (id = NULLIF(current_setting('app.company_id', true), '')::uuid)
    """)
