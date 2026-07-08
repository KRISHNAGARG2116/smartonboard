"""phase_b3d_integrations_and_automation

Revision ID: 735aba993a4e
Revises: f1ca798a58a0
Create Date: 2026-07-08 20:54:05.174951

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '735aba993a4e'
down_revision: Union[str, None] = 'f1ca798a58a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tables
    op.create_table('workflow_rules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('parent_rule_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='draft', nullable=False),
        sa.Column('trigger_type', sa.String(length=100), nullable=False),
        sa.Column('conditions_json', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('actions_json', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_rule_id'], ['workflow_rules.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_rules_company_id'), 'workflow_rules', ['company_id'], unique=False)

    op.create_table('workflow_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('workflow_rule_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('attempt_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_logs', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('depth', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_rule_id'], ['workflow_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_runs_company_id'), 'workflow_runs', ['company_id'], unique=False)
    op.create_index(op.f('ix_workflow_runs_idempotency_key'), 'workflow_runs', ['idempotency_key'], unique=True)

    op.create_table('email_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('body_markdown', sa.Text(), nullable=False),
        sa.Column('trigger_type', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_templates_company_id'), 'email_templates', ['company_id'], unique=False)

    op.create_table('sent_emails',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=True),
        sa.Column('recipient', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='sent', nullable=False),
        sa.Column('open_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('click_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sent_emails_company_id'), 'sent_emails', ['company_id'], unique=False)

    op.create_table('api_keys',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.String(100)), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_ip', sa.String(length=45), nullable=True),
        sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('usage_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_company_id'), 'api_keys', ['company_id'], unique=False)
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)

    op.create_table('slack_teams_integrations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('webhook_url', sa.String(length=2048), nullable=False),
        sa.Column('settings_json', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_slack_teams_integrations_company_id'), 'slack_teams_integrations', ['company_id'], unique=True)

    op.create_table('background_check_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('check_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('result', sa.String(length=50), nullable=True),
        sa.Column('external_check_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_background_check_records_company_id'), 'background_check_records', ['company_id'], unique=False)

    op.create_table('hris_imports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('progress_pct', sa.Integer(), server_default='0', nullable=False),
        sa.Column('imported_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('skipped_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('failed_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_csv_path', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hris_imports_company_id'), 'hris_imports', ['company_id'], unique=False)

    op.create_table('integration_audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('integration_type', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('details_json', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_integration_audit_logs_company_id'), 'integration_audit_logs', ['company_id'], unique=False)

    op.create_table('integration_health',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), server_default='0', nullable=False),
        sa.Column('next_check_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_integration_health_company_id'), 'integration_health', ['company_id'], unique=False)
    op.create_index(op.f('ix_integration_health_provider'), 'integration_health', ['provider'], unique=False)

    op.create_table('usage_billing_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('quantity', sa.Integer(), server_default='1', nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usage_billing_events_company_id'), 'usage_billing_events', ['company_id'], unique=False)

    # 2. Enable RLS and add tenant isolation policies
    new_tables = [
        'workflow_rules', 'workflow_runs', 'email_templates', 'sent_emails',
        'api_keys', 'slack_teams_integrations', 'background_check_records',
        'hris_imports', 'integration_audit_logs', 'integration_health', 'usage_billing_events'
    ]

    for table in new_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            f"FOR ALL "
            f"USING ("
            f"    company_id = NULLIF(current_setting('app.company_id', true), '')::uuid "
            f"    OR current_setting('app.auth_mode', true) = 'true'"
            f") "
            f"WITH CHECK ("
            f"    company_id = NULLIF(current_setting('app.company_id', true), '')::uuid "
            f"    OR current_setting('app.auth_mode', true) = 'true'"
            f")"
        )

    # 4. Upgrade block_immutable_records_mutations function to support bypass_audit_immutability
    op.execute(
        """
        CREATE OR REPLACE FUNCTION block_immutable_records_mutations()
        RETURNS TRIGGER AS $$
        BEGIN
            IF current_setting('app.bypass_audit_immutability', true) = 'true' THEN
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                ELSE
                    RETURN NEW;
                END IF;
            END IF;
            RAISE EXCEPTION 'Timeline and history logs are immutable append-only records.';
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    new_tables = [
        'workflow_rules', 'workflow_runs', 'email_templates', 'sent_emails',
        'api_keys', 'slack_teams_integrations', 'background_check_records',
        'hris_imports', 'integration_audit_logs', 'integration_health', 'usage_billing_events'
    ]

    # Revert block_immutable_records_mutations function
    op.execute(
        """
        CREATE OR REPLACE FUNCTION block_immutable_records_mutations()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Timeline and history logs are immutable append-only records.';
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Drop RLS policies
    for table in new_tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")

    # Drop tables
    op.drop_table('usage_billing_events')
    op.drop_table('integration_health')
    op.drop_table('integration_audit_logs')
    op.drop_table('hris_imports')
    op.drop_table('background_check_records')
    op.drop_table('slack_teams_integrations')
    op.drop_table('api_keys')
    op.drop_table('sent_emails')
    op.drop_table('email_templates')
    op.drop_table('workflow_runs')
    op.drop_table('workflow_rules')
