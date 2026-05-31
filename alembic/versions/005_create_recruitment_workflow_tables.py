"""create_recruitment_workflow_tables

Revision ID: 005
Revises: 304a86f0e3ae
Create Date: 2026-05-31 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '304a86f0e3ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create candidate_notes table
    op.create_table('candidate_notes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_notes_application_id'), 'candidate_notes', ['application_id'], unique=False)
    op.create_index(op.f('ix_candidate_notes_company_id'), 'candidate_notes', ['company_id'], unique=False)

    # 2. Create interviews table
    op.create_table('interviews',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('interviewer_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('video_link', sa.String(length=500), nullable=True),
        sa.Column('is_cancelled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interviewer_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interviews_application_id'), 'interviews', ['application_id'], unique=False)
    op.create_index(op.f('ix_interviews_company_id'), 'interviews', ['company_id'], unique=False)

    # 3. Create scorecards table
    op.create_table('scorecards',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('interview_id', sa.UUID(), nullable=False),
        sa.Column('grader_id', sa.UUID(), nullable=False),
        sa.Column('criteria_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('overall_recommendation', sa.String(length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['grader_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('interview_id')
    )
    op.create_index(op.f('ix_scorecards_application_id'), 'scorecards', ['application_id'], unique=False)
    op.create_index(op.f('ix_scorecards_company_id'), 'scorecards', ['company_id'], unique=False)

    # 4. Enable Row Level Security (RLS) on all three tables
    for table in ('candidate_notes', 'interviews', 'scorecards'):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        # Create multi-tenant isolation policy
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

    # 5. Add settings column to jobs table
    op.add_column('jobs', sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'))


def downgrade() -> None:
    # Drop settings column from jobs table
    op.drop_column('jobs', 'settings')

    # Drop RLS policies
    for table in ('scorecards', 'interviews', 'candidate_notes'):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")

    # Drop tables
    op.drop_index(op.f('ix_scorecards_company_id'), table_name='scorecards')
    op.drop_index(op.f('ix_scorecards_application_id'), table_name='scorecards')
    op.drop_table('scorecards')

    op.drop_index(op.f('ix_interviews_company_id'), table_name='interviews')
    op.drop_index(op.f('ix_interviews_application_id'), table_name='interviews')
    op.drop_table('interviews')

    op.drop_index(op.f('ix_candidate_notes_company_id'), table_name='candidate_notes')
    op.drop_index(op.f('ix_candidate_notes_application_id'), table_name='candidate_notes')
    op.drop_table('candidate_notes')
