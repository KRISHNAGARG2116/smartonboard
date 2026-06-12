"""add_email_verified_to_users

Revision ID: 1de1e09682eb
Revises: 4bc027b93ec3
Create Date: 2026-06-12 16:36:04.565475

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1de1e09682eb'
down_revision: Union[str, None] = '4bc027b93ec3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=True))
    op.execute("UPDATE users SET email_verified = TRUE")
    op.alter_column('users', 'email_verified', nullable=False)


def downgrade() -> None:
    op.drop_column('users', 'email_verified')
