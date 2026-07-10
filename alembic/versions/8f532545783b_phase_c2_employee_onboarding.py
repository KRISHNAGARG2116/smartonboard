"""phase_c2_employee_onboarding

Revision ID: 8f532545783b
Revises: 835aba993a4e
Create Date: 2026-07-10 12:05:09.728878

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8f532545783b'
down_revision: Union[str, None] = '835aba993a4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Add 'employee' to user_role enum
    with op.get_context().autocommit_block():
        op.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 
                    FROM pg_enum 
                    JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
                    WHERE pg_type.typname = 'user_role' 
                      AND pg_enum.enumlabel = 'employee'
                ) THEN
                    ALTER TYPE user_role ADD VALUE 'employee';
                END IF;
            END
            $$;
        """)

    # 1. Alter employees table to add user_id
    op.add_column('employees', sa.Column('user_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_employees_user_id', 'employees', 'users', ['user_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_employees_user_id'), 'employees', ['user_id'], unique=False)


    # 2. Alter onboarding_tasks to add phase and is_optional
    op.add_column('onboarding_tasks', sa.Column('phase', sa.String(length=50), server_default='preboarding', nullable=False))
    op.add_column('onboarding_tasks', sa.Column('is_optional', sa.Boolean(), server_default='false', nullable=False))

    # 3. Create onboarding_task_dependencies
    op.create_table('onboarding_task_dependencies',
        sa.Column('task_id', sa.UUID(), nullable=False),
        sa.Column('depends_on_task_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['onboarding_tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['depends_on_task_id'], ['onboarding_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('task_id', 'depends_on_task_id')
    )

    # 4. Create employee_onboardings
    op.create_table('employee_onboardings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('template_id', sa.UUID(), nullable=True),
        sa.Column('template_name', sa.String(length=150), nullable=True),
        sa.Column('template_version', sa.Integer(), nullable=True),
        sa.Column('template_snapshot_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['onboarding_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id')
    )
    op.create_index(op.f('ix_employee_onboardings_company_id'), 'employee_onboardings', ['company_id'], unique=False)
    op.create_index(op.f('ix_employee_onboardings_employee_id'), 'employee_onboardings', ['employee_id'], unique=True)

    # 5. Create employee_equipment_requests
    op.create_table('employee_equipment_requests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('item_type', sa.String(length=50), nullable=False),
        sa.Column('item_name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='requested', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_equipment_requests_company_id'), 'employee_equipment_requests', ['company_id'], unique=False)
    op.create_index(op.f('ix_employee_equipment_requests_employee_id'), 'employee_equipment_requests', ['employee_id'], unique=False)

    # 6. Create employee_provisioning_requests
    op.create_table('employee_provisioning_requests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('service_name', sa.String(length=100), nullable=False),
        sa.Column('account_username', sa.String(length=150), nullable=True),
        sa.Column('status', sa.String(length=30), server_default='pending', nullable=False),
        sa.Column('depends_on_provisioning_id', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['depends_on_provisioning_id'], ['employee_provisioning_requests.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_provisioning_requests_company_id'), 'employee_provisioning_requests', ['company_id'], unique=False)
    op.create_index(op.f('ix_employee_provisioning_requests_employee_id'), 'employee_provisioning_requests', ['employee_id'], unique=False)
    op.create_index(op.f('ix_employee_provisioning_requests_depends_on_provisioning_id'), 'employee_provisioning_requests', ['depends_on_provisioning_id'], unique=False)

    # 7. Create employee_documents
    op.create_table('employee_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('document_type', sa.String(length=100), nullable=False),
        sa.Column('document_name', sa.String(length=255), nullable=False),
        sa.Column('document_version', sa.String(length=30), server_default='1.0', nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('uploaded_by_id', sa.UUID(), nullable=False),
        sa.Column('storage_key', sa.String(), nullable=False),
        sa.Column('signed_hash', sa.String(length=64), nullable=True),
        sa.Column('signature_svg_or_text', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_documents_company_id'), 'employee_documents', ['company_id'], unique=False)
    op.create_index(op.f('ix_employee_documents_employee_id'), 'employee_documents', ['employee_id'], unique=False)
    op.create_index(op.f('ix_employee_documents_uploaded_by_id'), 'employee_documents', ['uploaded_by_id'], unique=False)

    # 8. Create employee_policy_acknowledgements
    op.create_table('employee_policy_acknowledgements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('policy_name', sa.String(length=100), nullable=False),
        sa.Column('policy_version', sa.String(length=30), server_default='1.0', nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('user_agent', sa.String(length=500), nullable=False),
        sa.Column('digital_signature', sa.String(length=255), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_policy_acknowledgements_company_id'), 'employee_policy_acknowledgements', ['company_id'], unique=False)
    op.create_index(op.f('ix_employee_policy_acknowledgements_employee_id'), 'employee_policy_acknowledgements', ['employee_id'], unique=False)

    # 9. Create employee_buddy_assignments
    op.create_table('employee_buddy_assignments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('buddy_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='assigned', nullable=False),
        sa.Column('buddy_feedback', sa.Text(), nullable=True),
        sa.Column('employee_feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['buddy_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_buddy_assignments_company_id'), 'employee_buddy_assignments', ['company_id'], unique=False)
    op.create_index(op.f('ix_employee_buddy_assignments_employee_id'), 'employee_buddy_assignments', ['employee_id'], unique=False)

    # 10. Create employee_welcome_events
    op.create_table('employee_welcome_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('event_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), server_default='30', nullable=False),
        sa.Column('meeting_link', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_welcome_events_company_id'), 'employee_welcome_events', ['company_id'], unique=False)
    op.create_index(op.f('ix_employee_welcome_events_employee_id'), 'employee_welcome_events', ['employee_id'], unique=False)

    # 11. Create employee_onboarding_audits
    op.create_table('employee_onboarding_audits',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=True),
        sa.Column('actor_type', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_onboarding_audits_company_id'), 'employee_onboarding_audits', ['company_id'], unique=False)
    op.create_index(op.f('ix_employee_onboarding_audits_employee_id'), 'employee_onboarding_audits', ['employee_id'], unique=False)
    op.create_index(op.f('ix_employee_onboarding_audits_actor_id'), 'employee_onboarding_audits', ['actor_id'], unique=False)

    # 12. Enable RLS and add tenant isolation policies for new tables
    rls_tables = [
        'employee_onboardings', 'employee_equipment_requests', 'employee_provisioning_requests',
        'employee_documents', 'employee_policy_acknowledgements', 'employee_buddy_assignments',
        'employee_welcome_events', 'employee_onboarding_audits'
    ]
    for table in rls_tables:
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


def downgrade() -> None:
    # Drop RLS policies
    rls_tables = [
        'employee_onboardings', 'employee_equipment_requests', 'employee_provisioning_requests',
        'employee_documents', 'employee_policy_acknowledgements', 'employee_buddy_assignments',
        'employee_welcome_events', 'employee_onboarding_audits'
    ]
    for table in rls_tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")

    # Drop tables
    op.drop_table('employee_onboarding_audits')
    op.drop_table('employee_welcome_events')
    op.drop_table('employee_buddy_assignments')
    op.drop_table('employee_policy_acknowledgements')
    op.drop_table('employee_documents')
    op.drop_table('employee_provisioning_requests')
    op.drop_table('employee_equipment_requests')
    op.drop_table('employee_onboardings')
    op.drop_table('onboarding_task_dependencies')

    # Remove columns from onboarding_tasks
    op.drop_column('onboarding_tasks', 'is_optional')
    op.drop_column('onboarding_tasks', 'phase')

    # Remove fk and column from employees
    op.drop_constraint('fk_employees_user_id', 'employees', type_='foreignkey')
    op.drop_index(op.f('ix_employees_user_id'), table_name='employees')
    op.drop_column('employees', 'user_id')
