"""create_offers_table

Revision ID: 006
Revises: 005
Create Date: 2026-05-31 16:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create offers table
    op.create_table('offers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('salary', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('equity_grant', sa.String(length=100), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id')
    )
    op.create_index(op.f('ix_offers_application_id'), 'offers', ['application_id'], unique=False)
    op.create_index(op.f('ix_offers_company_id'), 'offers', ['company_id'], unique=False)

    # 2. Enable Row Level Security (RLS) on offers
    op.execute("ALTER TABLE offers ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE offers FORCE ROW LEVEL SECURITY")

    # 3. Create multi-tenant isolation policy on offers
    op.execute("""
        CREATE POLICY tenant_isolation_offers ON offers
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


def downgrade() -> None:
    # Drop RLS policy
    op.execute("DROP POLICY IF EXISTS tenant_isolation_offers ON offers")

    # Drop table
    op.drop_index(op.f('ix_offers_company_id'), table_name='offers')
    op.drop_index(op.f('ix_offers_application_id'), table_name='offers')
    op.drop_table('offers')
