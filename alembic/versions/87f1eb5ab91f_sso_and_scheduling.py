"""sso_and_scheduling

Revision ID: 87f1eb5ab91f
Revises: d749eb0dcc4b
Create Date: 2026-05-31 23:28:41.258692

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '87f1eb5ab91f'
down_revision: Union[str, None] = 'd749eb0dcc4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create company_sso_settings table (SAML2 & OIDC Support)
    op.create_table('company_sso_settings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('sso_provider', sa.String(length=20), server_default='saml2', nullable=False),
        sa.Column('idp_entity_id', sa.String(length=255), nullable=False),
        sa.Column('idp_sso_url', sa.String(length=512), nullable=False),
        sa.Column('idp_x509_cert', sa.Text(), nullable=True),
        sa.Column('oidc_client_id', sa.String(length=255), nullable=True),
        sa.Column('oidc_client_secret', sa.Text(), nullable=True),
        sa.Column('oidc_well_known', sa.String(length=512), nullable=True),
        sa.Column('role_mapping', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', name='uq_company_sso_settings')
    )
    op.create_index(op.f('ix_company_sso_settings_company_id'), 'company_sso_settings', ['company_id'], unique=False)

    # 2. Create calendar_credentials table
    op.create_table('calendar_credentials',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('account_email', sa.String(length=255), nullable=False),
        sa.Column('encrypted_access_token', sa.Text(), nullable=False),
        sa.Column('encrypted_refresh_token', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('channel_id', sa.String(length=255), nullable=True),
        sa.Column('sync_token', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'user_id', 'provider', 'account_email', name='uq_user_provider_calendar')
    )
    op.create_index(op.f('ix_calendar_credentials_user_id'), 'calendar_credentials', ['user_id'], unique=False)

    # 3. Create scheduling_links table (with secure token_hash)
    op.create_table('scheduling_links',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('interview_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('one_time_use', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('interview_id', name='uq_interview_scheduling_link'),
        sa.UniqueConstraint('token_hash', name='uq_scheduling_links_token_hash')
    )
    op.create_index(op.f('ix_scheduling_links_token_hash'), 'scheduling_links', ['token_hash'], unique=True)

    # 4. Create interview_slots table (with UNIQUE(interview_id, start_time))
    op.create_table('interview_slots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('interview_id', sa.UUID(), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('external_event_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('interview_id', 'start_time', name='uq_interview_start_time')
    )
    op.create_index(op.f('ix_interview_slots_interview_id'), 'interview_slots', ['interview_id'], unique=False)

    # 5. Enable Row Level Security (RLS) on all new tables
    for table in ('company_sso_settings', 'calendar_credentials', 'scheduling_links', 'interview_slots'):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # 6. Apply multi-tenant RLS policies
    for table in ('company_sso_settings', 'calendar_credentials', 'scheduling_links', 'interview_slots'):
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
    for table in ('company_sso_settings', 'calendar_credentials', 'scheduling_links', 'interview_slots'):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")

    # 2. Drop tables
    op.drop_index(op.f('ix_interview_slots_interview_id'), table_name='interview_slots')
    op.drop_table('interview_slots')
    op.drop_index(op.f('ix_scheduling_links_token_hash'), table_name='scheduling_links')
    op.drop_table('scheduling_links')
    op.drop_index(op.f('ix_calendar_credentials_user_id'), table_name='calendar_credentials')
    op.drop_table('calendar_credentials')
    op.drop_index(op.f('ix_company_sso_settings_company_id'), table_name='company_sso_settings')
    op.drop_table('company_sso_settings')
