"""milestone11_phase3

Revision ID: 019_milestone11_phase3
Revises: 018_milestone11_phase2
Create Date: 2026-06-01 23:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '019_milestone11_phase3'
down_revision: Union[str, None] = '018_milestone11_phase2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create onboarding_portal_tokens table
    op.create_table('onboarding_portal_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False),
        sa.Column('access_scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index('ix_portal_tokens_employee', 'onboarding_portal_tokens', ['company_id', 'employee_id'], unique=False)
    op.create_index('ix_portal_tokens_hash', 'onboarding_portal_tokens', ['token_hash'], unique=True)

    # 2. Create onboarding_document_signatures table
    op.create_table('onboarding_document_signatures',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('user_agent', sa.String(length=500), nullable=False),
        sa.Column('signer_name', sa.String(length=150), nullable=False),
        sa.Column('signature_hash', sa.String(length=64), nullable=False),
        sa.Column('signed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['onboarding_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_doc_signatures_employee', 'onboarding_document_signatures', ['company_id', 'employee_id'], unique=False)

    # 3. Create onboarding_task_reminders table
    op.create_table('onboarding_task_reminders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('task_id', sa.UUID(), nullable=False),
        sa.Column('notification_channel', sa.String(length=30), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['onboarding_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_task_reminders_status_time', 'onboarding_task_reminders', ['company_id', 'status', 'scheduled_at'], unique=False)

    # 4. Create onboarding_task_escalations table
    op.create_table('onboarding_task_escalations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('task_id', sa.UUID(), nullable=False),
        sa.Column('escalated_to_id', sa.UUID(), nullable=False),
        sa.Column('escalation_level', sa.Integer(), nullable=False),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['onboarding_tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['escalated_to_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_task_escalations_unresolved', 'onboarding_task_escalations', ['company_id', 'task_id'], unique=False, postgresql_where=sa.text('resolved_at IS NULL'))

    # 5. Create onboarding_activity_log table
    op.create_table('onboarding_activity_log',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=True),
        sa.Column('actor_type', sa.String(length=30), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_onboarding_activity_employee', 'onboarding_activity_log', ['company_id', 'employee_id'], unique=False)
    op.create_index('ix_onboarding_activity_event', 'onboarding_activity_log', ['company_id', 'event_type'], unique=False)

    # 6. Enable RLS and apply tenant isolation policies
    new_tables = (
        'onboarding_portal_tokens',
        'onboarding_document_signatures',
        'onboarding_task_reminders',
        'onboarding_task_escalations',
        'onboarding_activity_log'
    )
    for table in new_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
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
    new_tables = (
        'onboarding_portal_tokens',
        'onboarding_document_signatures',
        'onboarding_task_reminders',
        'onboarding_task_escalations',
        'onboarding_activity_log'
    )
    # 1. Drop RLS policies
    for table in new_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")

    # 2. Drop tables & indexes
    op.drop_index('ix_onboarding_activity_event', table_name='onboarding_activity_log')
    op.drop_index('ix_onboarding_activity_employee', table_name='onboarding_activity_log')
    op.drop_table('onboarding_activity_log')

    op.drop_index('ix_task_escalations_unresolved', table_name='onboarding_task_escalations')
    op.drop_table('onboarding_task_escalations')

    op.drop_index('ix_task_reminders_status_time', table_name='onboarding_task_reminders')
    op.drop_table('onboarding_task_reminders')

    op.drop_index('ix_doc_signatures_employee', table_name='onboarding_document_signatures')
    op.drop_table('onboarding_document_signatures')

    op.drop_index('ix_portal_tokens_hash', table_name='onboarding_portal_tokens')
    op.drop_index('ix_portal_tokens_employee', table_name='onboarding_portal_tokens')
    op.drop_table('onboarding_portal_tokens')
