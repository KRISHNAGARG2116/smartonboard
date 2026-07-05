"""phase_b3a_enterprise_ats_foundation

Revision ID: 5e000ecb704f
Revises: 4612fe6bcd5f
Create Date: 2026-07-05 13:53:37.956714

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5e000ecb704f'
down_revision: Union[str, None] = '4612fe6bcd5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add columns to stage_definitions
    op.add_column('stage_definitions', sa.Column('job_id', sa.UUID(), nullable=True))
    op.add_column('stage_definitions', sa.Column('color', sa.String(length=50), nullable=True))
    op.add_column('stage_definitions', sa.Column('icon', sa.String(length=50), nullable=True))
    op.add_column('stage_definitions', sa.Column('position', sa.Integer(), nullable=True))
    op.add_column('stage_definitions', sa.Column('sla_hours', sa.Integer(), nullable=True))
    op.add_column('stage_definitions', sa.Column('sla_enabled', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('stage_definitions', sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('stage_definitions', sa.Column('is_terminal', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('stage_definitions', sa.Column('allowed_next_stage_ids', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True))
    op.add_column('stage_definitions', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    op.create_foreign_key('fk_stage_definitions_job_id', 'stage_definitions', 'jobs', ['job_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_stage_definitions_job_id'), 'stage_definitions', ['job_id'], unique=False)

    # 2. Create candidate_stage_histories table
    op.create_table('candidate_stage_histories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('previous_stage_id', sa.UUID(), nullable=True),
        sa.Column('new_stage_id', sa.UUID(), nullable=False),
        sa.Column('changed_by', sa.UUID(), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['previous_stage_id'], ['stage_definitions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['new_stage_id'], ['stage_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_stage_histories_company_id'), 'candidate_stage_histories', ['company_id'], unique=False)
    op.create_index(op.f('ix_candidate_stage_histories_application_id'), 'candidate_stage_histories', ['application_id'], unique=False)

    # 3. Enable RLS and add tenant isolation policy for candidate_stage_histories
    op.execute("ALTER TABLE candidate_stage_histories ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE candidate_stage_histories FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY candidate_stage_histories_tenant_isolation ON candidate_stage_histories "
        "FOR ALL "
        "USING ("
        "    company_id = NULLIF(current_setting('app.company_id', true), '')::uuid "
        "    OR current_setting('app.auth_mode', true) = 'true'"
        ") "
        "WITH CHECK ("
        "    company_id = NULLIF(current_setting('app.company_id', true), '')::uuid "
        "    OR current_setting('app.auth_mode', true) = 'true'"
        ")"
    )

    # 4. Enable RLS and add tenant isolation policy for application_events
    op.execute("ALTER TABLE application_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE application_events FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY application_events_tenant_isolation ON application_events "
        "FOR ALL "
        "USING ("
        "    EXISTS ("
        "        SELECT 1 FROM applications "
        "        WHERE applications.id = application_events.application_id "
        "          AND (applications.company_id = NULLIF(current_setting('app.company_id', true), '')::uuid "
        "               OR current_setting('app.auth_mode', true) = 'true')"
        "    )"
        ")"
    )

    # 5. Add Immutability Protections for candidate_stage_histories and application_events
    op.execute(
        """
        CREATE OR REPLACE FUNCTION block_immutable_records_mutations()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Timeline and history logs are immutable append-only records.';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER check_history_immutability
        BEFORE UPDATE OR DELETE ON candidate_stage_histories
        FOR EACH ROW EXECUTE FUNCTION block_immutable_records_mutations();
        """
    )
    op.execute(
        """
        CREATE TRIGGER check_events_immutability
        BEFORE UPDATE OR DELETE ON application_events
        FOR EACH ROW EXECUTE FUNCTION block_immutable_records_mutations();
        """
    )


def downgrade() -> None:
    # Drop Immutability and RLS triggers/policies first
    op.execute("DROP TRIGGER IF EXISTS check_events_immutability ON application_events")
    op.execute("DROP TRIGGER IF EXISTS check_history_immutability ON candidate_stage_histories")
    op.execute("DROP FUNCTION IF EXISTS block_immutable_records_mutations")
    op.execute("DROP POLICY IF EXISTS application_events_tenant_isolation ON application_events")
    op.execute("DROP POLICY IF EXISTS candidate_stage_histories_tenant_isolation ON candidate_stage_histories")

    # Drop candidate_stage_histories table
    op.drop_index(op.f('ix_candidate_stage_histories_application_id'), table_name='candidate_stage_histories')
    op.drop_index(op.f('ix_candidate_stage_histories_company_id'), table_name='candidate_stage_histories')
    op.drop_table('candidate_stage_histories')

    # Drop columns from stage_definitions
    op.drop_constraint('fk_stage_definitions_job_id', 'stage_definitions', type_='foreignkey')
    op.drop_index(op.f('ix_stage_definitions_job_id'), table_name='stage_definitions')
    op.drop_column('stage_definitions', 'deleted_at')
    op.drop_column('stage_definitions', 'allowed_next_stage_ids')
    op.drop_column('stage_definitions', 'is_terminal')
    op.drop_column('stage_definitions', 'is_default')
    op.drop_column('stage_definitions', 'sla_enabled')
    op.drop_column('stage_definitions', 'sla_hours')
    op.drop_column('stage_definitions', 'position')
    op.drop_column('stage_definitions', 'icon')
    op.drop_column('stage_definitions', 'color')
    op.drop_column('stage_definitions', 'job_id')
