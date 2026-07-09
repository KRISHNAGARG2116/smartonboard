"""phase_c1_candidate_platform

Revision ID: 835aba993a4e
Revises: 735aba993a4e
Create Date: 2026-07-09 20:56:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '835aba993a4e'
down_revision: Union[str, None] = '735aba993a4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create candidate_tasks table
    op.create_table('candidate_tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), server_default='pending', nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('meta_payload', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_tasks_company_id'), 'candidate_tasks', ['company_id'], unique=False)
    op.create_index(op.f('ix_candidate_tasks_candidate_id'), 'candidate_tasks', ['candidate_id'], unique=False)

    # 2. Create candidate_documents table
    op.create_table('candidate_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        sa.Column('document_type', sa.String(length=100), nullable=False),
        sa.Column('document_name', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='pending', nullable=False),
        sa.Column('uploaded_by_id', sa.UUID(), nullable=False),
        sa.Column('reviewed_by_id', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_reason', sa.Text(), nullable=True),
        sa.Column('verification_status_reason_code', sa.String(length=100), nullable=True),
        sa.Column('verified_checksum', sa.String(length=64), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_documents_company_id'), 'candidate_documents', ['company_id'], unique=False)
    op.create_index(op.f('ix_candidate_documents_application_id'), 'candidate_documents', ['application_id'], unique=False)
    op.create_index(op.f('ix_candidate_documents_candidate_id'), 'candidate_documents', ['candidate_id'], unique=False)

    # 3. Create candidate_messages table
    op.create_table('candidate_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('sender_id', sa.UUID(), nullable=False),
        sa.Column('sender_role', sa.String(length=30), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('attachments_json', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='sent', nullable=False),
        sa.Column('thread_id', sa.UUID(), nullable=True),
        sa.Column('parent_message_id', sa.UUID(), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reactions_json', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_message_id'], ['candidate_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_messages_company_id'), 'candidate_messages', ['company_id'], unique=False)
    op.create_index(op.f('ix_candidate_messages_application_id'), 'candidate_messages', ['application_id'], unique=False)
    op.create_index(op.f('ix_candidate_messages_sender_id'), 'candidate_messages', ['sender_id'], unique=False)
    op.create_index(op.f('ix_candidate_messages_thread_id'), 'candidate_messages', ['thread_id'], unique=False)
    op.create_index(op.f('ix_candidate_messages_parent_message_id'), 'candidate_messages', ['parent_message_id'], unique=False)

    # 4. Create candidate_chat_sessions table
    op.create_table('candidate_chat_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_chat_sessions_candidate_id'), 'candidate_chat_sessions', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_candidate_chat_sessions_application_id'), 'candidate_chat_sessions', ['application_id'], unique=False)

    # 5. Create candidate_ai_chats table
    op.create_table('candidate_ai_chats',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['candidate_chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_ai_chats_session_id'), 'candidate_ai_chats', ['session_id'], unique=False)

    # 6. Create interview_reschedule_requests table
    op.create_table('interview_reschedule_requests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('interview_id', sa.UUID(), nullable=False),
        sa.Column('requested_by_id', sa.UUID(), nullable=False),
        sa.Column('suggested_times', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='pending_review', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interview_reschedule_requests_interview_id'), 'interview_reschedule_requests', ['interview_id'], unique=False)
    op.create_index(op.f('ix_interview_reschedule_requests_requested_by_id'), 'interview_reschedule_requests', ['requested_by_id'], unique=False)

    # 7. Create candidate_profile_revisions table
    op.create_table('candidate_profile_revisions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('profile_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('changed_by', sa.UUID(), nullable=True),
        sa.Column('snapshot', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['profile_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_profile_revisions_profile_id'), 'candidate_profile_revisions', ['profile_id'], unique=False)

    # 8. Modify offers table
    op.add_column('offers', sa.Column('document_path', sa.String(), nullable=True))
    op.add_column('offers', sa.Column('decline_reason', sa.String(), nullable=True))

    # 9. Modify candidate_profiles table
    op.add_column('candidate_profiles', sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True))
    op.add_column('candidate_profiles', sa.Column('experience', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True))
    op.add_column('candidate_profiles', sa.Column('education', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True))
    op.add_column('candidate_profiles', sa.Column('links', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True))
    op.add_column('candidate_profiles', sa.Column('languages', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True))
    op.add_column('candidate_profiles', sa.Column('availability', sa.String(length=255), nullable=True))
    op.add_column('candidate_profiles', sa.Column('salary_expectations', sa.String(length=100), nullable=True))
    op.add_column('candidate_profiles', sa.Column('work_authorization', sa.String(length=100), nullable=True))

    # 10. Enable RLS and add tenant isolation policies for new tables (where company_id exists)
    rls_tables = ['candidate_tasks', 'candidate_documents', 'candidate_messages']
    for table in rls_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            f"FOR ALL "
            f"USING ("
            f"    company_id = NULLIF(current_setting('app.company_id', true), '')::uuid "
            f"    OR current_setting('app.auth_mode', true) = 'true'"
            f") "
            f"WITH CHECK ("
            f"    company_id = NULLIF(current_setting('app.company_id', true), '')::uuid "
            f"    OR current_setting('app.auth_mode', true) = 'true'"
            f")"
        )


def downgrade() -> None:
    # Drop RLS policies
    rls_tables = ['candidate_tasks', 'candidate_documents', 'candidate_messages']
    for table in rls_tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")

    # Remove added columns from candidate_profiles
    op.drop_column('candidate_profiles', 'work_authorization')
    op.drop_column('candidate_profiles', 'salary_expectations')
    op.drop_column('candidate_profiles', 'availability')
    op.drop_column('candidate_profiles', 'languages')
    op.drop_column('candidate_profiles', 'links')
    op.drop_column('candidate_profiles', 'education')
    op.drop_column('candidate_profiles', 'experience')
    op.drop_column('candidate_profiles', 'preferences')

    # Remove added columns from offers
    op.drop_column('offers', 'decline_reason')
    op.drop_column('offers', 'document_path')

    # Drop tables
    op.drop_table('candidate_profile_revisions')
    op.drop_table('interview_reschedule_requests')
    op.drop_table('candidate_ai_chats')
    op.drop_table('candidate_chat_sessions')
    op.drop_table('candidate_messages')
    op.drop_table('candidate_documents')
    op.drop_table('candidate_tasks')
