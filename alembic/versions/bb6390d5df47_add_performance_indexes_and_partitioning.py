"""add_performance_indexes_and_partitioning

Revision ID: bb6390d5df47
Revises: 849c8fab264b
Create Date: 2026-07-10 21:49:08.927800

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb6390d5df47'
down_revision: Union[str, None] = '849c8fab264b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Performance Indexes
    op.create_index('ix_applications_status_company', 'applications', ['status', 'company_id'], unique=False)
    op.create_index('ix_candidates_full_name', 'candidates', ['full_name'], unique=False)
    op.create_index('ix_candidates_email', 'candidates', ['email'], unique=False)
    op.create_index('ix_cached_match_scores_perf', 'cached_match_scores', ['candidate_id', 'job_id', 'resume_version'], unique=False)
    op.create_index('ix_talent_pools_company', 'talent_pools', ['company_id'], unique=False)

    # 2. Table Partitioning Setup for new/append-only tables
    # Since Postgres does not support directly altering a table to partitioned, we drop and recreate
    # the empty logs/chat tables partitioned by RANGE (created_at).
    op.drop_table('ai_copilot_call_logs')
    op.drop_table('recruiter_chat_messages')

    # Recreate partitioned ai_copilot_call_logs
    op.execute("""
        CREATE TABLE ai_copilot_call_logs (
            id UUID NOT NULL,
            company_id UUID,
            recruiter_id UUID,
            prompt TEXT NOT NULL,
            tools_used JSONB DEFAULT '[]'::jsonb NOT NULL,
            execution_time_ms INTEGER NOT NULL,
            planning_time_ms INTEGER NOT NULL,
            token_usage JSONB DEFAULT '{}'::jsonb NOT NULL,
            plan_complexity INTEGER NOT NULL,
            user_feedback TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at);
    """)

    # Create partitions
    op.execute("""
        CREATE TABLE ai_copilot_call_logs_y2026q3 PARTITION OF ai_copilot_call_logs
        FOR VALUES FROM ('2026-07-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');
    """)
    op.execute("""
        CREATE TABLE ai_copilot_call_logs_y2026q4 PARTITION OF ai_copilot_call_logs
        FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');
    """)
    op.execute("""
        CREATE TABLE ai_copilot_call_logs_default PARTITION OF ai_copilot_call_logs DEFAULT;
    """)

    # Recreate partitioned recruiter_chat_messages
    op.execute("""
        CREATE TABLE recruiter_chat_messages (
            id UUID NOT NULL,
            session_id UUID NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            execution_graph JSONB,
            plan_confidence DOUBLE PRECISION,
            plan_confidence_reason TEXT,
            plan_approved BOOLEAN DEFAULT false NOT NULL,
            permission_snapshot JSONB,
            execution_context_snapshot JSONB,
            tool_calls JSONB DEFAULT '[]'::jsonb NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at);
    """)

    # Create partitions for chat messages
    op.execute("""
        CREATE TABLE recruiter_chat_messages_y2026q3 PARTITION OF recruiter_chat_messages
        FOR VALUES FROM ('2026-07-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');
    """)
    op.execute("""
        CREATE TABLE recruiter_chat_messages_y2026q4 PARTITION OF recruiter_chat_messages
        FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');
    """)
    op.execute("""
        CREATE TABLE recruiter_chat_messages_default PARTITION OF recruiter_chat_messages DEFAULT;
    """)


def downgrade() -> None:
    # Revert index
    op.drop_index('ix_talent_pools_company', 'talent_pools')
    op.drop_index('ix_cached_match_scores_perf', 'cached_match_scores')
    op.drop_index('ix_candidates_email', 'candidates')
    op.drop_index('ix_candidates_full_name', 'candidates')
    op.drop_index('ix_applications_status_company', 'applications')

    # Drop partitioned tables and revert
    op.drop_table('ai_copilot_call_logs')
    op.drop_table('recruiter_chat_messages')

    # Recreate simple tables
    op.create_table('ai_copilot_call_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=True),
        sa.Column('recruiter_id', sa.UUID(), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('tools_used', sa.JSON(), nullable=False),
        sa.Column('execution_time_ms', sa.Integer(), nullable=False),
        sa.Column('planning_time_ms', sa.Integer(), nullable=False),
        sa.Column('token_usage', sa.JSON(), nullable=False),
        sa.Column('plan_complexity', sa.Integer(), nullable=False),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recruiter_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('recruiter_chat_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('execution_graph', sa.JSON(), nullable=True),
        sa.Column('plan_confidence', sa.Float(), nullable=True),
        sa.Column('plan_confidence_reason', sa.Text(), nullable=True),
        sa.Column('plan_approved', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('permission_snapshot', sa.JSON(), nullable=True),
        sa.Column('execution_context_snapshot', sa.JSON(), nullable=True),
        sa.Column('tool_calls', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['recruiter_chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
