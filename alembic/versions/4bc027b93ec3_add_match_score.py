"""add match_score

Revision ID: 4bc027b93ec3
Revises: cba0fe9a3c10
Create Date: 2026-06-06 21:42:41.214082

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4bc027b93ec3'
down_revision: Union[str, None] = 'cba0fe9a3c10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('applications', sa.Column('match_score', sa.Float(), nullable=True))
    op.create_index(op.f('ix_quarantined_files_user_id'), 'quarantined_files', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_quarantined_files_user_id'), table_name='quarantined_files')
    op.drop_column('applications', 'match_score')
