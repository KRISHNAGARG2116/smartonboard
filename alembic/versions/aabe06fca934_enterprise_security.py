"""enterprise_security

Revision ID: aabe06fca934
Revises: 719e75f45bac
Create Date: 2026-06-01 16:17:05.754280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aabe06fca934'
down_revision: Union[str, None] = '719e75f45bac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create company_ip_whitelists table
    op.create_table(
        'company_ip_whitelists',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('cidr_block', sa.String(length=45), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_company_ip_whitelists_company_id'), 'company_ip_whitelists', ['company_id'], unique=False)

    # 2. Create company_smtp_settings table
    op.create_table(
        'company_smtp_settings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('hostname', sa.String(length=255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('encrypted_password', sa.String(length=512), nullable=False),
        sa.Column('iv', sa.String(length=32), nullable=False),
        sa.Column('tag', sa.String(length=32), nullable=False),
        sa.Column('key_version', sa.String(length=50), server_default='v1', nullable=False),
        sa.Column('sender_email', sa.String(length=255), nullable=False),
        sa.Column('verification_status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('last_verification_error', sa.Text(), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_rotated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_company_smtp_settings_company_id'), 'company_smtp_settings', ['company_id'], unique=True)

    # 3. Enable RLS on both tables
    tables = ('company_ip_whitelists', 'company_smtp_settings')
    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # 4. Apply multi-tenant RLS policies
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
    tables = ('company_ip_whitelists', 'company_smtp_settings')
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")

    # 2. Drop tables
    op.execute("DROP TABLE IF EXISTS company_smtp_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS company_ip_whitelists CASCADE")
