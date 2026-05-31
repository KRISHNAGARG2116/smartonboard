"""advanced_pipeline_automation

Revision ID: 015_advanced_automation
Revises: 014_dynamic_pipelines
Create Date: 2026-06-01 03:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '015_advanced_automation'
down_revision: Union[str, None] = '014_dynamic_pipelines'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create stage_slas
    op.create_table('stage_slas',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('stage_definition_id', sa.UUID(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('escalation_action', sa.String(length=50), nullable=False),
        sa.Column('fallback_stage_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stage_definition_id'], ['stage_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fallback_stage_id'], ['stage_definitions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stage_slas_company_id'), 'stage_slas', ['company_id'], unique=False)
    op.create_index(op.f('ix_stage_slas_stage_definition_id'), 'stage_slas', ['stage_definition_id'], unique=False)

    # 2. Create candidate_stage_sla_trackers
    op.create_table('candidate_stage_sla_trackers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('stage_definition_id', sa.UUID(), nullable=False),
        sa.Column('entered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('breached_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='active', nullable=False),
        sa.Column('escalation_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stage_definition_id'], ['stage_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_stage_sla_trackers_company_id'), 'candidate_stage_sla_trackers', ['company_id'], unique=False)
    op.create_index(op.f('ix_candidate_stage_sla_trackers_application_id'), 'candidate_stage_sla_trackers', ['application_id'], unique=False)
    op.create_index(op.f('ix_candidate_stage_sla_trackers_stage_definition_id'), 'candidate_stage_sla_trackers', ['stage_definition_id'], unique=False)

    # 3. Create approval_escalation_rules
    op.create_table('approval_escalation_rules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('approval_template_step_id', sa.UUID(), nullable=False),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False),
        sa.Column('escalation_type', sa.String(length=50), nullable=False),
        sa.Column('delegate_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approval_template_step_id'], ['approval_template_steps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['delegate_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approval_escalation_rules_company_id'), 'approval_escalation_rules', ['company_id'], unique=False)
    op.create_index(op.f('ix_approval_escalation_rules_approval_template_step_id'), 'approval_escalation_rules', ['approval_template_step_id'], unique=False)

    # 4. Create approval_step_escalations
    op.create_table('approval_step_escalations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('approval_step_id', sa.UUID(), nullable=False),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('action_taken', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approval_step_id'], ['approval_steps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approval_step_escalations_company_id'), 'approval_step_escalations', ['company_id'], unique=False)
    op.create_index(op.f('ix_approval_step_escalations_approval_step_id'), 'approval_step_escalations', ['approval_step_id'], unique=False)

    # 4b. Add current_stage_id to applications table
    op.add_column('applications', sa.Column('current_stage_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_applications_current_stage', 'applications', 'stage_definitions', ['current_stage_id'], ['id'], ondelete='SET NULL')

    # 5. Enable Row Level Security (RLS) on all new tables
    tables = ('stage_slas', 'candidate_stage_sla_trackers', 'approval_escalation_rules', 'approval_step_escalations')
    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # 6. Apply multi-tenant RLS policies
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
    tables = ('stage_slas', 'candidate_stage_sla_trackers', 'approval_escalation_rules', 'approval_step_escalations')
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")

    # 2. Drop tables safely
    op.execute("DROP TABLE IF EXISTS approval_step_escalations CASCADE")
    op.execute("DROP TABLE IF EXISTS approval_escalation_rules CASCADE")
    op.execute("DROP TABLE IF EXISTS candidate_stage_sla_trackers CASCADE")
    op.execute("DROP TABLE IF EXISTS stage_slas CASCADE")

    # 3. Drop current_stage_id from applications table safely
    op.execute("ALTER TABLE applications DROP CONSTRAINT IF EXISTS fk_applications_current_stage")
    op.execute("ALTER TABLE applications DROP COLUMN IF EXISTS current_stage_id")


