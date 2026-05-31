"""intelligence_refinements

Revision ID: 4492b6f731e7
Revises: 008
Create Date: 2026-05-31 22:37:40.276579

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '4492b6f731e7'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ai_recruiter_insights', sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ai_recruiter_insights', sa.Column('candidate_embedding_ids', JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))
    op.add_column('ai_recruiter_insights', sa.Column('scorecard_ids', JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))


def downgrade() -> None:
    op.drop_column('ai_recruiter_insights', 'scorecard_ids')
    op.drop_column('ai_recruiter_insights', 'candidate_embedding_ids')
    op.drop_column('ai_recruiter_insights', 'generated_at')
