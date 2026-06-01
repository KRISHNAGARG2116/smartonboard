"""milestone11_phase2

Revision ID: 018_milestone11_phase2
Revises: 017_milestone11_onboarding
Create Date: 2026-06-01 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '018_milestone11_phase2'
down_revision: Union[str, None] = '017_milestone11_onboarding'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Alter employees table to add sync-specific columns
    op.add_column('employees', sa.Column('hris_id', sa.String(length=100), nullable=True))
    op.add_column('employees', sa.Column('sync_status', sa.String(length=30), server_default='pending', nullable=False))
    op.add_column('employees', sa.Column('sync_error', sa.Text(), nullable=True))
    op.create_index('ix_employees_company_sync_status', 'employees', ['company_id', 'sync_status'], unique=False)
    op.create_index('ix_employees_company_hris_id', 'employees', ['company_id', 'hris_id'], unique=False)

    # 2. Create hris_field_mappings table
    op.create_table('hris_field_mappings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('local_field', sa.String(length=100), nullable=False),
        sa.Column('provider_field', sa.String(length=100), nullable=False),
        sa.Column('is_custom', sa.Boolean(), nullable=False),
        sa.Column('transform_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'provider', 'local_field', name='uq_hris_field_mapping_local')
    )
    op.create_index('ix_field_mappings_company_provider', 'hris_field_mappings', ['company_id', 'provider'], unique=False)

    # 3. Create sync_metrics table
    op.create_table('sync_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Double(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sync_metrics_company_metric', 'sync_metrics', ['company_id', 'metric_name', 'timestamp'], unique=False)

    # 4. Create dlq_records table
    op.create_table('dlq_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('outbox_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['outbox_id'], ['onboarding_event_outbox.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_dlq_records_company_status', 'dlq_records', ['company_id', 'status'], unique=False)

    # 5. Create employee_sync_history table
    op.create_table('employee_sync_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('request_id', sa.UUID(), nullable=False),
        sa.Column('sync_state', sa.String(length=30), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('payload_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sync_history_company_employee', 'employee_sync_history', ['company_id', 'employee_id'], unique=False)
    op.create_index('ix_sync_history_company_provider', 'employee_sync_history', ['company_id', 'provider'], unique=False)

    # 6. Enable RLS on newly created tables
    new_tables = (
        'hris_field_mappings',
        'sync_metrics',
        'dlq_records',
        'employee_sync_history'
    )
    for table in new_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # 7. Apply multi-tenant RLS policies
    for table in new_tables:
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
        'hris_field_mappings',
        'sync_metrics',
        'dlq_records',
        'employee_sync_history'
    )
    # 1. Drop RLS policies
    for table in new_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")

    # 2. Drop tables & indexes
    op.drop_index('ix_sync_history_company_provider', table_name='employee_sync_history')
    op.drop_index('ix_sync_history_company_employee', table_name='employee_sync_history')
    op.drop_table('employee_sync_history')

    op.drop_index('ix_dlq_records_company_status', table_name='dlq_records')
    op.drop_table('dlq_records')

    op.drop_index('ix_sync_metrics_company_metric', table_name='sync_metrics')
    op.drop_table('sync_metrics')

    op.drop_index('ix_field_mappings_company_provider', table_name='hris_field_mappings')
    op.drop_table('hris_field_mappings')

    # 3. Drop columns on employees table
    op.drop_index('ix_employees_company_hris_id', table_name='employees')
    op.drop_index('ix_employees_company_sync_status', table_name='employees')
    op.drop_column('employees', 'sync_error')
    op.drop_column('employees', 'sync_status')
    op.drop_column('employees', 'hris_id')
