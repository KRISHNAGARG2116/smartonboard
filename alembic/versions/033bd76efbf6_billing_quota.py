"""billing_quota

Revision ID: 033bd76efbf6
Revises: aabe06fca934
Create Date: 2026-06-01 16:28:14.835536

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '033bd76efbf6'
down_revision: Union[str, None] = 'aabe06fca934'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create company_subscription_plans table
    op.create_table('company_subscription_plans',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('tier_name', sa.String(length=50), nullable=False),
        sa.Column('candidate_limit', sa.Integer(), nullable=False),
        sa.Column('job_limit', sa.Integer(), nullable=False),
        sa.Column('ai_limit', sa.Integer(), nullable=False),
        sa.Column('webhook_limit', sa.Integer(), nullable=False),
        sa.Column('pending_downgrade_tier', sa.String(length=50), nullable=True),
        sa.Column('pending_downgrade_effective_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('billing_cycle_start', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('billing_cycle_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_company_subscription_plans_company_id'), 'company_subscription_plans', ['company_id'], unique=True)

    # 2. Create company_usage_ledgers table
    op.create_table('company_usage_ledgers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('candidates_processed', sa.Integer(), nullable=False),
        sa.Column('active_jobs_count', sa.Integer(), nullable=False),
        sa.Column('ai_screenings_run', sa.Integer(), nullable=False),
        sa.Column('webhooks_dispatched', sa.Integer(), nullable=False),
        sa.Column('last_reset_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_company_usage_ledgers_company_id'), 'company_usage_ledgers', ['company_id'], unique=True)

    # 3. Create company_usage_histories table
    op.create_table('company_usage_histories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('tier_name', sa.String(length=50), nullable=False),
        sa.Column('billing_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('billing_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('candidates_processed', sa.Integer(), nullable=False),
        sa.Column('active_jobs_count', sa.Integer(), nullable=False),
        sa.Column('ai_screenings_run', sa.Integer(), nullable=False),
        sa.Column('webhooks_dispatched', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_company_usage_histories_company_id'), 'company_usage_histories', ['company_id'], unique=False)
    
    # 4. Add reporting indexes on histories
    op.create_index('ix_company_usage_histories_reporting', 'company_usage_histories', ['company_id', 'created_at', 'tier_name'], unique=False)
    op.create_index('ix_company_usage_histories_billing_period', 'company_usage_histories', ['company_id', 'billing_period_start', 'billing_period_end'], unique=False)

    # 5. Enable RLS on the three tables
    billing_tables = ('company_subscription_plans', 'company_usage_ledgers', 'company_usage_histories')
    for table in billing_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # 6. Apply multi-tenant RLS policies
    for table in billing_tables:
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


def downgrade() -> None:
    # 1. Drop RLS policies
    billing_tables = ('company_subscription_plans', 'company_usage_ledgers', 'company_usage_histories')
    for table in billing_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")

    # 2. Drop reporting indexes
    op.execute("DROP INDEX IF EXISTS ix_company_usage_histories_reporting")
    op.execute("DROP INDEX IF EXISTS ix_company_usage_histories_billing_period")

    # 3. Drop tables and indexes
    op.drop_index(op.f('ix_company_usage_ledgers_company_id'), table_name='company_usage_ledgers')
    op.drop_table('company_usage_ledgers')
    op.drop_index(op.f('ix_company_usage_histories_company_id'), table_name='company_usage_histories')
    op.drop_table('company_usage_histories')
    op.drop_index(op.f('ix_company_subscription_plans_company_id'), table_name='company_subscription_plans')
    op.drop_table('company_subscription_plans')
