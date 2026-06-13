"""add_google_auth_fields

Revision ID: 081496f36c3b
Revises: 1de1e09682eb
Create Date: 2026-06-13 02:17:52.861951

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '081496f36c3b'
down_revision: Union[str, None] = '1de1e09682eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the auth_provider enum type
    auth_provider = postgresql.ENUM("local", "google", name="auth_provider")
    auth_provider.create(op.get_bind(), checkfirst=True)

    # Add columns to users table
    op.add_column('users', sa.Column('auth_provider', auth_provider, nullable=False, server_default='local'))
    op.add_column('users', sa.Column('google_subject_id', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('google_hosted_domain', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_users_google_subject_id'), 'users', ['google_subject_id'], unique=True)


def downgrade() -> None:
    # Drop columns and indices
    op.drop_index(op.f('ix_users_google_subject_id'), table_name='users')
    op.drop_column('users', 'google_hosted_domain')
    op.drop_column('users', 'google_subject_id')
    op.drop_column('users', 'auth_provider')

    # Drop enum type
    auth_provider = postgresql.ENUM("local", "google", name="auth_provider")
    auth_provider.drop(op.get_bind(), checkfirst=True)
