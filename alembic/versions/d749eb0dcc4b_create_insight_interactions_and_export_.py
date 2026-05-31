"""create_insight_interactions_and_export_jobs

Revision ID: d749eb0dcc4b
Revises: 4492b6f731e7
Create Date: 2026-05-31 22:54:40.521216

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd749eb0dcc4b'
down_revision: Union[str, None] = '4492b6f731e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create export_jobs table
    op.create_table('export_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('file_path', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_export_jobs_user_id'), 'export_jobs', ['user_id'], unique=False)

    # 2. Create ai_insight_interactions table
    op.create_table('ai_insight_interactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('insight_type', sa.String(length=50), nullable=False),
        sa.Column('interaction_type', sa.String(length=30), nullable=False),
        sa.Column('recommendation_snapshot', sa.String(length=20), nullable=True),
        sa.Column('recruiter_decision', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_insight_interactions_application_id'), 'ai_insight_interactions', ['application_id'], unique=False)
    op.create_index(op.f('ix_ai_insight_interactions_user_id'), 'ai_insight_interactions', ['user_id'], unique=False)

    # 3. Enable RLS on both tables
    for table in ('ai_insight_interactions', 'export_jobs'):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # 4. Create RLS multi-tenant policies
    for table in ('ai_insight_interactions', 'export_jobs'):
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
    for table in ('ai_insight_interactions', 'export_jobs'):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")

    # 2. Drop tables
    op.drop_index(op.f('ix_ai_insight_interactions_user_id'), table_name='ai_insight_interactions')
    op.drop_index(op.f('ix_ai_insight_interactions_application_id'), table_name='ai_insight_interactions')
    op.drop_table('ai_insight_interactions')
    op.drop_index(op.f('ix_export_jobs_user_id'), table_name='export_jobs')
    op.drop_table('export_jobs')
