"""phase_b3b_enterprise_collaboration

Revision ID: 5e000ecb7050
Revises: 5e000ecb704f
Create Date: 2026-07-05 14:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5e000ecb7050'
down_revision: Union[str, None] = '5e000ecb704f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add columns to applications table
    op.add_column('applications', sa.Column('is_archived', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('applications', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('applications', sa.Column('archived_by', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_applications_archived_by', 'applications', 'users', ['archived_by'], ['id'], ondelete='SET NULL')

    # 2. Add columns to saved_searches table
    op.add_column('saved_searches', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('saved_searches', sa.Column('sort_order', sa.String(length=100), nullable=True))
    op.add_column('saved_searches', sa.Column('default_view', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('saved_searches', sa.Column('is_shared', sa.Boolean(), server_default='false', nullable=False))

    # 3. Add columns to candidate_tags table
    op.add_column('candidate_tags', sa.Column('icon', sa.String(length=50), nullable=True))

    # 4. Add columns to candidate_notes table
    op.add_column('candidate_notes', sa.Column('attachments_json', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))

    # 5. Add columns to interview_kits table
    op.add_column('interview_kits', sa.Column('estimated_duration_minutes', sa.Integer(), server_default='45', nullable=False))
    op.add_column('interview_kits', sa.Column('behavioral_questions', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))
    op.add_column('interview_kits', sa.Column('technical_questions', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))
    op.add_column('interview_kits', sa.Column('scoring_criteria', sa.Text(), nullable=True))
    op.add_column('interview_kits', sa.Column('red_flags_notes', sa.Text(), nullable=True))
    op.add_column('interview_kits', sa.Column('attachments_json', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))
    op.add_column('interview_kits', sa.Column('competencies', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))

    # 6. Create duplicate_warnings table
    op.create_table('duplicate_warnings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        sa.Column('duplicate_candidate_id', sa.UUID(), nullable=False),
        sa.Column('confidence_score', sa.Integer(), nullable=False),
        sa.Column('matched_fields', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['duplicate_candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_duplicate_warnings_company_id'), 'duplicate_warnings', ['company_id'], unique=False)
    op.create_index(op.f('ix_duplicate_warnings_candidate_id'), 'duplicate_warnings', ['candidate_id'], unique=False)

    # 7. Enable RLS and add tenant isolation policy for duplicate_warnings
    op.execute("ALTER TABLE duplicate_warnings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE duplicate_warnings FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY duplicate_warnings_tenant_isolation ON duplicate_warnings "
        "FOR ALL "
        "USING ("
        "    company_id = NULLIF(current_setting('app.company_id', true), '')::uuid "
        "    OR current_setting('app.auth_mode', true) = 'true'"
        ") "
        "WITH CHECK ("
        "    company_id = NULLIF(current_setting('app.company_id', true), '')::uuid "
        "    OR current_setting('app.auth_mode', true) = 'true'"
        ")"
    )


def downgrade() -> None:
    # Drop RLS trigger/policy first
    op.execute("DROP POLICY IF EXISTS duplicate_warnings_tenant_isolation ON duplicate_warnings")

    # Drop duplicate_warnings table
    op.drop_index(op.f('ix_duplicate_warnings_candidate_id'), table_name='duplicate_warnings')
    op.drop_index(op.f('ix_duplicate_warnings_company_id'), table_name='duplicate_warnings')
    op.drop_table('duplicate_warnings')

    # Drop columns from interview_kits
    op.drop_column('interview_kits', 'competencies')
    op.drop_column('interview_kits', 'attachments_json')
    op.drop_column('interview_kits', 'red_flags_notes')
    op.drop_column('interview_kits', 'scoring_criteria')
    op.drop_column('interview_kits', 'technical_questions')
    op.drop_column('interview_kits', 'behavioral_questions')
    op.drop_column('interview_kits', 'estimated_duration_minutes')

    # Drop columns from candidate_notes
    op.drop_column('candidate_notes', 'attachments_json')

    # Drop columns from candidate_tags
    op.drop_column('candidate_tags', 'icon')

    # Drop columns from saved_searches
    op.drop_column('saved_searches', 'is_shared')
    op.drop_column('saved_searches', 'default_view')
    op.drop_column('saved_searches', 'sort_order')
    op.drop_column('saved_searches', 'description')

    # Drop columns from applications
    op.drop_constraint('fk_applications_archived_by', 'applications', type_='foreignkey')
    op.drop_column('applications', 'archived_by')
    op.drop_column('applications', 'archived_at')
    op.drop_column('applications', 'is_archived')
