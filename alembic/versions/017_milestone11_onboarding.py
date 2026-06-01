"""milestone11_onboarding

Revision ID: 017_milestone11_onboarding
Revises: 033bd76efbf6
Create Date: 2026-06-01 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '017_milestone11_onboarding'
down_revision: Union[str, None] = '033bd76efbf6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create company_hris_integrations table
    op.create_table('company_hris_integrations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('credentials_encrypted', sa.Text(), nullable=False),
        sa.Column('credentials_hash', sa.String(length=64), nullable=False),
        sa.Column('key_version', sa.Integer(), nullable=False),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'provider', name='uq_company_hris_provider')
    )
    op.create_index('ix_hris_integrations_company', 'company_hris_integrations', ['company_id', 'provider'], unique=False)

    # 2. Create employees table
    op.create_table('employees',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=True),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('job_title', sa.String(length=150), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('employment_type', sa.String(length=50), nullable=False),
        sa.Column('employee_number', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('supervisor_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supervisor_id'], ['employees.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'email', name='uq_employees_company_email'),
        sa.UniqueConstraint('company_id', 'employee_number', name='uq_employees_company_number')
    )
    op.create_index('ix_employees_company_email', 'employees', ['company_id', 'email'], unique=False)
    op.create_index('ix_employees_company_candidate', 'employees', ['company_id', 'candidate_id'], unique=False)
    op.create_index('ix_employees_company_supervisor', 'employees', ['company_id', 'supervisor_id'], unique=False)

    # 3. Create onboarding_templates table
    op.create_table('onboarding_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_onboarding_templates_company_id'), 'onboarding_templates', ['company_id'], unique=False)

    # 4. Create onboarding_template_tasks table
    op.create_table('onboarding_template_tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('template_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('rule_criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['onboarding_templates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_onboarding_template_tasks_company_id'), 'onboarding_template_tasks', ['company_id'], unique=False)
    op.create_index(op.f('ix_onboarding_template_tasks_template_id'), 'onboarding_template_tasks', ['template_id'], unique=False)

    # 5. Create onboarding_workflows table
    op.create_table('onboarding_workflows',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id')
    )
    op.create_index('ix_onboarding_workflows_company_employee', 'onboarding_workflows', ['company_id', 'employee_id', 'status'], unique=False)

    # 6. Create onboarding_tasks table
    op.create_table('onboarding_tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('assigned_to_role', sa.String(length=50), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_by_id', sa.UUID(), nullable=True),
        sa.Column('meta_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['onboarding_workflows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_onboarding_tasks_company_workflow', 'onboarding_tasks', ['company_id', 'workflow_id', 'status', 'assigned_to_role'], unique=False)

    # 7. Create onboarding_documents table
    op.create_table('onboarding_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('task_id', sa.UUID(), nullable=False),
        sa.Column('document_name', sa.String(length=150), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=True),
        sa.Column('signature_status', sa.String(length=50), nullable=False),
        sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['onboarding_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_onboarding_documents_company_task', 'onboarding_documents', ['company_id', 'task_id', 'signature_status'], unique=False)

    # 8. Create onboarding_event_outbox table
    op.create_table('onboarding_event_outbox',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_event_outbox_company_status', 'onboarding_event_outbox', ['company_id', 'status', 'event_type'], unique=False)

    # 9. Enable and force RLS on all newly created tables
    new_tables = (
        'company_hris_integrations',
        'employees',
        'onboarding_templates',
        'onboarding_template_tasks',
        'onboarding_workflows',
        'onboarding_tasks',
        'onboarding_documents',
        'onboarding_event_outbox'
    )
    for table in new_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # 10. Apply multi-tenant RLS policies
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
        'company_hris_integrations',
        'employees',
        'onboarding_templates',
        'onboarding_template_tasks',
        'onboarding_workflows',
        'onboarding_tasks',
        'onboarding_documents',
        'onboarding_event_outbox'
    )
    # 1. Drop RLS policies
    for table in new_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")

    # 2. Drop indexes & tables in reverse dependency order
    op.drop_index('ix_event_outbox_company_status', table_name='onboarding_event_outbox')
    op.drop_table('onboarding_event_outbox')

    op.drop_index('ix_onboarding_documents_company_task', table_name='onboarding_documents')
    op.drop_table('onboarding_documents')

    op.drop_index('ix_onboarding_tasks_company_workflow', table_name='onboarding_tasks')
    op.drop_table('onboarding_tasks')

    op.drop_index('ix_onboarding_workflows_company_employee', table_name='onboarding_workflows')
    op.drop_table('onboarding_workflows')

    op.drop_index(op.f('ix_onboarding_template_tasks_template_id'), table_name='onboarding_template_tasks')
    op.drop_index(op.f('ix_onboarding_template_tasks_company_id'), table_name='onboarding_template_tasks')
    op.drop_table('onboarding_template_tasks')

    op.drop_index(op.f('ix_onboarding_templates_company_id'), table_name='onboarding_templates')
    op.drop_table('onboarding_templates')

    op.drop_index('ix_employees_company_supervisor', table_name='employees')
    op.drop_index('ix_employees_company_candidate', table_name='employees')
    op.drop_index('ix_employees_company_email', table_name='employees')
    op.drop_table('employees')

    op.drop_index('ix_hris_integrations_company', table_name='company_hris_integrations')
    op.drop_table('company_hris_integrations')
