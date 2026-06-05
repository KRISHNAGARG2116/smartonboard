"""add_withdrawn_to_application_status

Revision ID: cba0fe9a3c10
Revises: 1d4bd9f0f23c
Create Date: 2026-06-06 01:49:18.343456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cba0fe9a3c10'
down_revision: Union[str, None] = '1d4bd9f0f23c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block in PostgreSQL.
    # We commit the current transaction first.
    op.execute("COMMIT")
    try:
        op.execute("ALTER TYPE application_status ADD VALUE 'withdrawn'")
    except Exception:
        pass


def downgrade() -> None:
    # PostgreSQL does not support dropping enum values directly via ALTER TYPE.
    pass
