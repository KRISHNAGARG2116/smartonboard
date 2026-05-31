"""analytics_and_intelligence_tables

Revision ID: 008
Revises: 007
Create Date: 2026-05-31 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create candidate_stage_transitions table
    op.create_table('candidate_stage_transitions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('from_status', sa.String(length=50), nullable=False),
        sa.Column('to_status', sa.String(length=50), nullable=False),
        sa.Column('transitioned_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('actor_id', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_stage_transitions_company_id_application_id'), 'candidate_stage_transitions', ['company_id', 'application_id'], unique=False)
    op.create_index(op.f('ix_candidate_stage_transitions_to_status'), 'candidate_stage_transitions', ['to_status'], unique=False)

    # 2. Create funnel_aggregates table
    op.create_table('funnel_aggregates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=False),
        sa.Column('candidate_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('conversion_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'job_id', 'stage', name='uq_funnel_job_stage')
    )
    op.create_index(op.f('ix_funnel_aggregates_job_id'), 'funnel_aggregates', ['job_id'], unique=False)

    # 3. Create recruiter_productivity_aggregates table
    op.create_table('recruiter_productivity_aggregates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('recruiter_id', sa.UUID(), nullable=False),
        sa.Column('applications_reviewed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('candidates_advanced', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('interviews_scheduled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('offers_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('offers_accepted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recruiter_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'recruiter_id', name='uq_recruiter_productivity')
    )
    op.create_index(op.f('ix_recruiter_productivity_aggregates_recruiter_id'), 'recruiter_productivity_aggregates', ['recruiter_id'], unique=False)

    # 4. Create ai_recruiter_insights table
    op.create_table('ai_recruiter_insights',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('insight_type', sa.String(length=50), nullable=False),
        sa.Column('content', sa.String(), nullable=True),
        sa.Column('generation_status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('last_error', sa.String(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('confidence_reason', JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('prompt_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('model_version', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id', 'insight_type', name='uq_app_insight_type')
    )
    op.create_index(op.f('ix_ai_recruiter_insights_application_id'), 'ai_recruiter_insights', ['application_id'], unique=False)

    # 5. Enable Row Level Security (RLS) on all tables
    for table in ('candidate_stage_transitions', 'funnel_aggregates', 'recruiter_productivity_aggregates', 'ai_recruiter_insights'):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # 6. Create multi-tenant isolation policies
    for table in ('candidate_stage_transitions', 'funnel_aggregates', 'recruiter_productivity_aggregates', 'ai_recruiter_insights'):
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
    # Drop RLS policies
    for table in ('candidate_stage_transitions', 'funnel_aggregates', 'recruiter_productivity_aggregates', 'ai_recruiter_insights'):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")

    # Drop tables
    op.drop_table('ai_recruiter_insights')
    op.drop_table('recruiter_productivity_aggregates')
    op.drop_table('funnel_aggregates')
    op.drop_table('candidate_stage_transitions')
