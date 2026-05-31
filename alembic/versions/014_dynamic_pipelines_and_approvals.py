"""dynamic_pipelines_and_approvals

Revision ID: 014_dynamic_pipelines
Revises: 4298ac75dc9c
Create Date: 2026-06-01 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '014_dynamic_pipelines'
down_revision: Union[str, None] = '4298ac75dc9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create pipeline_templates
    op.create_table('pipeline_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pipeline_templates_company_id'), 'pipeline_templates', ['company_id'], unique=False)

    # 2. Create pipelines
    op.create_table('pipelines',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('pipeline_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pipelines_company_id'), 'pipelines', ['company_id'], unique=False)

    # 3. Create stage_definitions
    op.create_table('stage_definitions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('pipeline_template_id', sa.UUID(), nullable=True),
        sa.Column('pipeline_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('base_category', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('automation_rules', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pipeline_template_id'], ['pipeline_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pipeline_id', 'sequence', name='uq_pipeline_stage_seq'),
        sa.UniqueConstraint('pipeline_template_id', 'sequence', name='uq_template_stage_seq'),
        sa.CheckConstraint('pipeline_template_id IS NOT NULL OR pipeline_id IS NOT NULL', name='check_stage_owner')
    )
    op.create_index(op.f('ix_stage_definitions_company_id'), 'stage_definitions', ['company_id'], unique=False)
    op.create_index(op.f('ix_stage_definitions_pipeline_template_id'), 'stage_definitions', ['pipeline_template_id'], unique=False)
    op.create_index(op.f('ix_stage_definitions_pipeline_id'), 'stage_definitions', ['pipeline_id'], unique=False)

    # 4. Create approval_templates
    op.create_table('approval_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approval_templates_company_id'), 'approval_templates', ['company_id'], unique=False)

    # 5. Create approval_template_steps
    op.create_table('approval_template_steps',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('approval_template_id', sa.UUID(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('parallel_group', sa.Integer(), nullable=True),
        sa.Column('role_required', sa.String(length=50), nullable=True),
        sa.Column('approver_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approval_template_id'], ['approval_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approval_template_steps_company_id'), 'approval_template_steps', ['company_id'], unique=False)
    op.create_index(op.f('ix_approval_template_steps_approval_template_id'), 'approval_template_steps', ['approval_template_id'], unique=False)

    # 6. Create approval_chains
    op.create_table('approval_chains',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('approval_template_id', sa.UUID(), nullable=True),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=True),
        sa.Column('offer_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('current_step_sequence', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approval_template_id'], ['approval_templates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approval_chains_company_id'), 'approval_chains', ['company_id'], unique=False)
    op.create_index(op.f('ix_approval_chains_approval_template_id'), 'approval_chains', ['approval_template_id'], unique=False)
    op.create_index(op.f('ix_approval_chains_job_id'), 'approval_chains', ['job_id'], unique=False)
    op.create_index(op.f('ix_approval_chains_offer_id'), 'approval_chains', ['offer_id'], unique=False)

    # Enforce CHECK constraint on target_type / job_id / offer_id integrity
    op.execute("""
        ALTER TABLE approval_chains ADD CONSTRAINT check_approval_chain_target CHECK (
            (target_type = 'requisition' AND job_id IS NOT NULL AND offer_id IS NULL)
            OR
            (target_type = 'offer' AND offer_id IS NOT NULL AND job_id IS NULL)
        )
    """)

    # 7. Create approval_steps
    op.create_table('approval_steps',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('approval_chain_id', sa.UUID(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('parallel_group', sa.Integer(), nullable=True),
        sa.Column('role_required', sa.String(length=50), nullable=True),
        sa.Column('approver_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('actioned_by', sa.UUID(), nullable=True),
        sa.Column('actioned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approval_chain_id'], ['approval_chains.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['actioned_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approval_steps_company_id'), 'approval_steps', ['company_id'], unique=False)
    op.create_index(op.f('ix_approval_steps_approval_chain_id'), 'approval_steps', ['approval_chain_id'], unique=False)

    # 8. Enable Row Level Security (RLS) on all new tables
    tables = (
        'pipeline_templates', 'pipelines', 'stage_definitions',
        'approval_templates', 'approval_template_steps', 'approval_chains', 'approval_steps'
    )
    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # 9. Apply multi-tenant RLS policies
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
    tables = (
        'pipeline_templates', 'pipelines', 'stage_definitions',
        'approval_templates', 'approval_template_steps', 'approval_chains', 'approval_steps'
    )
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")

    # 2. Drop target integrity CHECK constraint
    op.execute("ALTER TABLE approval_chains DROP CONSTRAINT IF EXISTS check_approval_chain_target")

    # 3. Drop tables
    op.drop_index(op.f('ix_approval_steps_approval_chain_id'), table_name='approval_steps')
    op.drop_index(op.f('ix_approval_steps_company_id'), table_name='approval_steps')
    op.drop_table('approval_steps')

    op.drop_index(op.f('ix_approval_chains_offer_id'), table_name='approval_chains')
    op.drop_index(op.f('ix_approval_chains_job_id'), table_name='approval_chains')
    op.drop_index(op.f('ix_approval_chains_approval_template_id'), table_name='approval_chains')
    op.drop_index(op.f('ix_approval_chains_company_id'), table_name='approval_chains')
    op.drop_table('approval_chains')

    op.drop_index(op.f('ix_approval_template_steps_approval_template_id'), table_name='approval_template_steps')
    op.drop_index(op.f('ix_approval_template_steps_company_id'), table_name='approval_template_steps')
    op.drop_table('approval_template_steps')

    op.drop_index(op.f('ix_approval_templates_company_id'), table_name='approval_templates')
    op.drop_table('approval_templates')

    op.drop_index(op.f('ix_stage_definitions_pipeline_id'), table_name='stage_definitions')
    op.drop_index(op.f('ix_stage_definitions_pipeline_template_id'), table_name='stage_definitions')
    op.drop_index(op.f('ix_stage_definitions_company_id'), table_name='stage_definitions')
    op.drop_table('stage_definitions')

    op.drop_index(op.f('ix_pipelines_company_id'), table_name='pipelines')
    op.drop_table('pipelines')

    op.drop_index(op.f('ix_pipeline_templates_company_id'), table_name='pipeline_templates')
    op.drop_table('pipeline_templates')
