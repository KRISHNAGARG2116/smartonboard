"""calendar_sync_and_health

Revision ID: 9588ec80239f
Revises: 87f1eb5ab91f
Create Date: 2026-06-01 02:03:16.416873

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9588ec80239f'
down_revision: Union[str, None] = '87f1eb5ab91f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create oauth_states table
    op.create_table('oauth_states',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('state_hash', sa.String(length=64), nullable=False),
        sa.Column('nonce_hash', sa.String(length=64), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('state_hash', name='uq_oauth_states_state_hash')
    )
    op.create_index(op.f('ix_oauth_states_state_hash'), 'oauth_states', ['state_hash'], unique=True)

    # 2. Add health tracking columns to calendar_credentials table
    op.add_column('calendar_credentials', sa.Column('status', sa.String(length=30), server_default='active', nullable=False))
    op.add_column('calendar_credentials', sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('calendar_credentials', sa.Column('last_sync_error', sa.Text(), nullable=True))
    op.add_column('calendar_credentials', sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('calendar_credentials', sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True))

    # 3. Enable RLS on oauth_states table
    op.execute("ALTER TABLE oauth_states ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE oauth_states FORCE ROW LEVEL SECURITY")

    # 4. Apply multi-tenant RLS policy on oauth_states table
    op.execute("""
        CREATE POLICY tenant_isolation_oauth_states ON oauth_states
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
    # 1. Drop RLS policy
    op.execute("DROP POLICY IF EXISTS tenant_isolation_oauth_states ON oauth_states")

    # 2. Drop oauth_states table
    op.drop_index(op.f('ix_oauth_states_state_hash'), table_name='oauth_states')
    op.drop_table('oauth_states')

    # 3. Remove health tracking columns from calendar_credentials
    op.drop_column('calendar_credentials', 'last_retry_at')
    op.drop_column('calendar_credentials', 'retry_count')
    op.drop_column('calendar_credentials', 'last_sync_error')
    op.drop_column('calendar_credentials', 'last_sync_at')
    op.drop_column('calendar_credentials', 'status')
