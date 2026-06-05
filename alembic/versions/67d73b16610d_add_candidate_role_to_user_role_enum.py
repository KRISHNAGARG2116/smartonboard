"""add_candidate_role_to_user_role_enum

Revision ID: 67d73b16610d
Revises: fae88da6f6a4
Create Date: 2026-06-05 22:06:06.445135

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67d73b16610d'
down_revision: Union[str, None] = 'fae88da6f6a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'candidate' value to user_role enum type if it does not already exist.
    # We run this in an autocommit block because ALTER TYPE ... ADD VALUE cannot be executed
    # in a multi-statement transaction in some older PostgreSQL versions / setups.
    with op.get_context().autocommit_block():
        op.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 
                    FROM pg_enum 
                    JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
                    WHERE pg_type.typname = 'user_role' 
                      AND pg_enum.enumlabel = 'candidate'
                ) THEN
                    ALTER TYPE user_role ADD VALUE 'candidate';
                END IF;
            END
            $$;
        """)


def downgrade() -> None:
    # PostgreSQL does not natively support dropping values from an enum type
    # (ALTER TYPE ... DROP VALUE does not exist). Removing a value requires
    # recreating the enum and updating tables, which is unsafe for existing data.
    pass
