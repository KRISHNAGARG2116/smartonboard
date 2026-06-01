"""webhook_hub

Revision ID: 719e75f45bac
Revises: 016_hiring_committees
Create Date: 2026-06-01 16:07:24.772947

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '719e75f45bac'
down_revision: Union[str, None] = '016_hiring_committees'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create webhook_subscriptions table
    op.create_table(
        'webhook_subscriptions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('encrypted_secret', sa.String(length=512), nullable=False),
        sa.Column('iv', sa.String(length=32), nullable=False),
        sa.Column('tag', sa.String(length=32), nullable=False),
        sa.Column('key_version', sa.String(length=50), server_default='v1', nullable=False),
        sa.Column('secret_key_hash', sa.String(length=64), nullable=False),
        sa.Column('active_events', sa.ARRAY(sa.String(length=255)), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='active', nullable=False),
        sa.Column('consecutive_failures', sa.Integer(), server_default='0', nullable=False),
        sa.Column('disabled_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_subscriptions_company_id'), 'webhook_subscriptions', ['company_id'], unique=False)
    op.create_index(op.f('ix_webhook_subscriptions_secret_key_hash'), 'webhook_subscriptions', ['secret_key_hash'], unique=False)

    # 2. Create webhook_delivery_logs table
    op.create_table(
        'webhook_delivery_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('subscription_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=255), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('attempt_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('elapsed_seconds', sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_id'], ['webhook_subscriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_delivery_logs_company_id'), 'webhook_delivery_logs', ['company_id'], unique=False)
    op.create_index(op.f('ix_webhook_delivery_logs_subscription_id'), 'webhook_delivery_logs', ['subscription_id'], unique=False)

    # 3. Enable RLS on both tables
    tables = ('webhook_subscriptions', 'webhook_delivery_logs')
    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # 4. Apply multi-tenant RLS policies
    for table in tables:
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
    tables = ('webhook_subscriptions', 'webhook_delivery_logs')
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")

    # 2. Drop new tables
    op.execute("DROP TABLE IF EXISTS webhook_delivery_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS webhook_subscriptions CASCADE")
