"""phase_b3c_executive_analytics

Revision ID: f1ca798a58a0
Revises: 5e000ecb7050
Create Date: 2026-07-05 14:39:58.500163

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f1ca798a58a0'
down_revision: Union[str, None] = '5e000ecb7050'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create report_exports table
    op.create_table('report_exports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('requested_by', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('format', sa.String(length=10), nullable=False),
        sa.Column('filters', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('file_path', sa.String(length=255), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_report_exports_company_id'), 'report_exports', ['company_id'], unique=False)
    op.create_index(op.f('ix_report_exports_requested_by'), 'report_exports', ['requested_by'], unique=False)

    # 2. Enable RLS and add tenant isolation policy
    op.execute("ALTER TABLE report_exports ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE report_exports FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY report_exports_tenant_isolation ON report_exports "
        "FOR ALL "
        "USING ("
        "    company_id = NULLIF(current_setting('app.company_id', true), '')::uuid "
        "    OR current_setting('app.auth_mode', true) = 'true'"
        ") "
        "WITH CHECK ("
        "    company_id = NULLIF(current_setting('app.company_id', true), '')::uuid "
        "    OR current_setting('app.auth_mode', true) = 'true'"
        ")"
    )


def downgrade() -> None:
    # Drop RLS trigger/policy first
    op.execute("DROP POLICY IF EXISTS report_exports_tenant_isolation ON report_exports")

    # Drop report_exports table
    op.drop_index(op.f('ix_report_exports_requested_by'), table_name='report_exports')
    op.drop_index(op.f('ix_report_exports_company_id'), table_name='report_exports')
    op.drop_table('report_exports')
