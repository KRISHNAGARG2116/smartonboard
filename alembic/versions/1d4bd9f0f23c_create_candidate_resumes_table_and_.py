"""create_candidate_resumes_table_and_alter_quarantined_files

Revision ID: 1d4bd9f0f23c
Revises: 67d73b16610d
Create Date: 2026-06-06 01:14:59.224516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d4bd9f0f23c'
down_revision: Union[str, None] = '67d73b16610d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.dialects.postgresql import JSONB, UUID

def upgrade() -> None:
    # 1. Alter quarantined_files to make company_id nullable and add user_id
    op.alter_column('quarantined_files', 'company_id',
               existing_type=sa.UUID(),
               nullable=True)
    op.add_column('quarantined_files', sa.Column('user_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_quarantined_files_user_id', 'quarantined_files', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    # 2. Create candidate_resumes table
    op.create_table('candidate_resumes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('parsed_skills', JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('parsed_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_resumes_user_id'), 'candidate_resumes', ['user_id'], unique=False)

    # 3. Add skills and summary columns to candidate_profiles
    op.add_column('candidate_profiles', sa.Column('skills', JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('candidate_profiles', sa.Column('summary', sa.Text(), nullable=True))


def downgrade() -> None:
    # 1. Drop added columns from candidate_profiles
    op.drop_column('candidate_profiles', 'summary')
    op.drop_column('candidate_profiles', 'skills')

    # 2. Drop candidate_resumes table
    op.drop_index(op.f('ix_candidate_resumes_user_id'), table_name='candidate_resumes')
    op.drop_table('candidate_resumes')

    # 3. Revert quarantined_files modifications
    op.drop_constraint('fk_quarantined_files_user_id', 'quarantined_files', type_='foreignkey')
    op.drop_column('quarantined_files', 'user_id')
    op.alter_column('quarantined_files', 'company_id',
               existing_type=sa.UUID(),
               nullable=False)
