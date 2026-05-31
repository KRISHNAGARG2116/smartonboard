"""scheduling_concurrency_and_ownership

Revision ID: 4298ac75dc9c
Revises: 9588ec80239f
Create Date: 2026-06-01 02:28:03.330268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4298ac75dc9c'
down_revision: Union[str, None] = '9588ec80239f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable btree_gist extension for mixed comparison exclusion
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    # 2. Add booking_token_hash column to interview_slots
    op.add_column('interview_slots', sa.Column('booking_token_hash', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_interview_slots_booking_token_hash'), 'interview_slots', ['booking_token_hash'], unique=True)

    # 3. Create exclude overlapping confirmed bookings constraint
    op.execute("""
        ALTER TABLE interview_slots ADD CONSTRAINT exclude_overlapping_confirmed_bookings
        EXCLUDE USING gist (
            interview_id WITH =,
            tstzrange(start_time, end_time) WITH &&
        ) WHERE (status = 'confirmed')
    """)


def downgrade() -> None:
    # 1. Drop exclude constraint
    op.execute("ALTER TABLE interview_slots DROP CONSTRAINT IF EXISTS exclude_overlapping_confirmed_bookings")

    # 2. Clean up columns and indexes
    op.drop_index(op.f('ix_interview_slots_booking_token_hash'), table_name='interview_slots')
    op.drop_column('interview_slots', 'booking_token_hash')

