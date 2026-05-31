"""hiring_committees

Revision ID: 016_hiring_committees
Revises: 015_advanced_automation
Create Date: 2026-06-01 04:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '016_hiring_committees'
down_revision: Union[str, None] = '015_advanced_automation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create scorecard_templates
    op.create_table('scorecard_templates',
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
    op.create_index(op.f('ix_scorecard_templates_company_id'), 'scorecard_templates', ['company_id'], unique=False)

    # 2. Create scorecard_template_skills
    op.create_table('scorecard_template_skills',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('scorecard_template_id', sa.UUID(), nullable=False),
        sa.Column('skill_key', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('weight', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scorecard_template_id'], ['scorecard_templates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('scorecard_template_id', 'skill_key', name='uq_template_skill'),
        sa.CheckConstraint('weight > 0.00 AND weight <= 1.00', name='chk_skill_weight')
    )

    # 3. Create hiring_committees
    op.create_table('hiring_committees',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('quorum_percentage', sa.Integer(), server_default='100', nullable=False),
        sa.Column('min_score_threshold', sa.Numeric(precision=3, scale=2), server_default='3.00', nullable=False),
        sa.Column('consensus_sd_threshold', sa.Numeric(precision=3, scale=2), server_default='0.75', nullable=False),
        sa.Column('allow_veto', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('veto_skill_keys', sa.ARRAY(sa.String(length=100)), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('quorum_percentage > 0 AND quorum_percentage <= 100', name='chk_quorum'),
        sa.CheckConstraint('consensus_sd_threshold > 0.00', name='chk_sd')
    )
    op.create_index(op.f('ix_hiring_committees_company_id'), 'hiring_committees', ['company_id'], unique=False)

    # 4. Create hiring_committee_members
    op.create_table('hiring_committee_members',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('hiring_committee_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=50), server_default='reviewer', nullable=False),
        sa.Column('reviewer_weight', sa.Numeric(precision=4, scale=2), server_default='1.00', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hiring_committee_id'], ['hiring_committees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hiring_committee_id', 'user_id', name='uq_committee_member'),
        sa.CheckConstraint('reviewer_weight > 0.00 AND reviewer_weight <= 10.00', name='chk_rev_weight')
    )

    # 5. Create committee_reviews
    op.create_table('committee_reviews',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('hiring_committee_id', sa.UUID(), nullable=False),
        sa.Column('scorecard_template_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('average_score', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('reconciliation_notes', sa.Text(), nullable=True),
        sa.Column('review_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hiring_committee_id'], ['hiring_committees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scorecard_template_id'], ['scorecard_templates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id', 'hiring_committee_id', name='uq_application_committee')
    )
    op.create_index(op.f('ix_committee_reviews_application_id'), 'committee_reviews', ['application_id'], unique=False)

    # 6. Create committee_review_reviewers (Snapshot Roster)
    op.create_table('committee_review_reviewers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('committee_review_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=50), server_default='reviewer', nullable=False),
        sa.Column('reviewer_weight', sa.Numeric(precision=4, scale=2), server_default='1.00', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['committee_review_id'], ['committee_reviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('committee_review_id', 'user_id', name='uq_review_member_snapshot'),
        sa.CheckConstraint('reviewer_weight > 0.00 AND reviewer_weight <= 10.00', name='chk_rev_weight_snapshot')
    )
    op.create_index(op.f('ix_committee_review_reviewers_review_id'), 'committee_review_reviewers', ['committee_review_id'], unique=False)

    # 7. Add columns to pre-existing tables
    op.add_column('scorecards', sa.Column('committee_review_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_scorecards_committee_review', 'scorecards', 'committee_reviews', ['committee_review_id'], ['id'], ondelete='SET NULL')
    op.add_column('scorecards', sa.Column('weighted_score', sa.Numeric(precision=3, scale=2), nullable=True))

    op.add_column('applications', sa.Column('committee_status', sa.String(length=50), nullable=True))

    # 8. Enable Row Level Security (RLS) on all new tables
    tables = ('scorecard_templates', 'scorecard_template_skills', 'hiring_committees', 'hiring_committee_members', 'committee_reviews', 'committee_review_reviewers')
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
    tables = ('scorecard_templates', 'scorecard_template_skills', 'hiring_committees', 'hiring_committee_members', 'committee_reviews', 'committee_review_reviewers')
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")

    # 2. Drop columns from applications
    op.execute("ALTER TABLE applications DROP COLUMN IF EXISTS committee_status")

    # 3. Drop columns and foreign key from scorecards
    op.execute("ALTER TABLE scorecards DROP CONSTRAINT IF EXISTS fk_scorecards_committee_review")
    op.execute("ALTER TABLE scorecards DROP COLUMN IF EXISTS committee_review_id")
    op.execute("ALTER TABLE scorecards DROP COLUMN IF EXISTS weighted_score")

    # 4. Drop new tables
    op.execute("DROP TABLE IF EXISTS committee_review_reviewers CASCADE")
    op.execute("DROP TABLE IF EXISTS committee_reviews CASCADE")
    op.execute("DROP TABLE IF EXISTS hiring_committee_members CASCADE")
    op.execute("DROP TABLE IF EXISTS hiring_committees CASCADE")
    op.execute("DROP TABLE IF EXISTS scorecard_template_skills CASCADE")
    op.execute("DROP TABLE IF EXISTS scorecard_templates CASCADE")
