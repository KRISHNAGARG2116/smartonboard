"""CRM and Match Intelligence migration

Revision ID: phase_c3_crm
Revises: 8f532545783b
Create Date: 2026-07-10 15:35:00
"""
import uuid
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "phase_c3_crm"
down_revision: Union[str, None] = "8f532545783b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Alter existing tables
    op.add_column("jobs", sa.Column("job_version", sa.Integer(), server_default="1", nullable=False))
    op.add_column("candidate_profiles", sa.Column("resume_version", sa.Integer(), server_default="1", nullable=False))
    op.add_column("saved_searches", sa.Column("search_type", sa.String(length=50), server_default="saved", nullable=False))
    op.add_column("saved_searches", sa.Column("last_searched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))

    # 2. Create talent_pools table
    op.create_table(
        "talent_pools",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=50), server_default="#6b7280", nullable=False),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("visibility", sa.String(length=50), server_default="public", nullable=False),
        sa.Column("dynamic_rules", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=True),
        sa.Column("rule_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_archived", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_talent_pools_company_id", "talent_pools", ["company_id"], unique=False)

    # 3. Create talent_pool_rule_histories table
    op.create_table(
        "talent_pool_rule_histories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("talent_pool_id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("dynamic_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rule_version", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["talent_pool_id"], ["talent_pools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_talent_pool_rule_histories_company_id", "talent_pool_rule_histories", ["company_id"], unique=False)
    op.create_index("ix_talent_pool_rule_histories_talent_pool_id", "talent_pool_rule_histories", ["talent_pool_id"], unique=False)

    # 4. Create talent_pool_memberships table
    op.create_table(
        "talent_pool_memberships",
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("talent_pool_id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("added_by", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=50), server_default="manual", nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["talent_pool_id"], ["talent_pools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("candidate_id", "talent_pool_id"),
    )
    op.create_index("ix_talent_pool_memberships_company_id", "talent_pool_memberships", ["company_id"], unique=False)

    # 5. Create candidate_relationships table
    op.create_table(
        "candidate_relationships",
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("secondary_owner_id", sa.UUID(), nullable=True),
        sa.Column("watchers", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("crm_stage", sa.String(length=50), server_default="new_lead", nullable=False),
        sa.Column("relationship_status", sa.String(length=50), server_default="contacted", nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_favorite", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("ignore_ai_match", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("engagement_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("engagement_details", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["secondary_owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("candidate_id"),
    )
    op.create_index("ix_candidate_relationships_company_id", "candidate_relationships", ["company_id"], unique=False)

    # 6. Create candidate_activities table
    op.create_table(
        "candidate_activities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("recruiter_id", sa.UUID(), nullable=True),
        sa.Column("activity_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recruiter_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_candidate_activities_company_id", "candidate_activities", ["company_id"], unique=False)
    op.create_index("ix_candidate_activities_candidate_id", "candidate_activities", ["candidate_id"], unique=False)

    # 7. Create outreach_sequences table
    op.create_table(
        "outreach_sequences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outreach_sequences_company_id", "outreach_sequences", ["company_id"], unique=False)

    # 8. Create candidate_sequence_enrollments table
    op.create_table(
        "candidate_sequence_enrollments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("sequence_id", sa.UUID(), nullable=False),
        sa.Column("current_step_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="enrolled", nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sequence_id"], ["outreach_sequences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_candidate_sequence_enrollments_company_id", "candidate_sequence_enrollments", ["company_id"], unique=False)

    # 9. Create candidate_merge_logs table
    op.create_table(
        "candidate_merge_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("merged_candidate_id", sa.UUID(), nullable=False),
        sa.Column("surviving_candidate_id", sa.UUID(), nullable=False),
        sa.Column("merged_by", sa.UUID(), nullable=False),
        sa.Column("merged_candidate_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("merged_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["merged_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_candidate_merge_logs_company_id", "candidate_merge_logs", ["company_id"], unique=False)

    # 10. Create match_feedbacks table
    op.create_table(
        "match_feedbacks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("recruiter_id", sa.UUID(), nullable=False),
        sa.Column("rating", sa.String(length=20), nullable=False),
        sa.Column("feedback_reason", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recruiter_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_match_feedbacks_company_id", "match_feedbacks", ["company_id"], unique=False)

    # 11. Create cached_match_scores table
    op.create_table(
        "cached_match_scores",
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("resume_version", sa.Integer(), nullable=False),
        sa.Column("job_version", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("confidence_explanation", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explanation_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("generated_by_model", sa.String(length=100), nullable=False),
        sa.Column("last_computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("computation_duration_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("candidate_id", "job_id"),
    )

    # 12. Create match_score_histories table
    op.create_table(
        "match_score_histories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("resume_version", sa.Integer(), nullable=False),
        sa.Column("job_version", sa.Integer(), nullable=False),
        sa.Column("explanation_version", sa.Integer(), nullable=False),
        sa.Column("generated_by_model", sa.String(length=100), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_match_score_histories_candidate_id", "match_score_histories", ["candidate_id"], unique=False)
    op.create_index("ix_match_score_histories_job_id", "match_score_histories", ["job_id"], unique=False)

    # 13. Seed User CRM Permissions
    permissions_data = [
        {"id": uuid.uuid4(), "name": "view_talent_crm", "description": "Access the Talent CRM Workspace"},
        {"id": uuid.uuid4(), "name": "manage_talent_pools", "description": "Create, modify, and delete talent pools"},
        {"id": uuid.uuid4(), "name": "manage_candidate_relationships", "description": "Update candidate relationships stages and details"},
        {"id": uuid.uuid4(), "name": "run_ai_rediscovery", "description": "Execute AI rediscovery pipelines against jobs"},
        {"id": uuid.uuid4(), "name": "export_talent_search", "description": "Export candidate lists from NL and structured search"},
    ]
    for perm in permissions_data:
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, name, description, created_at) "
                "VALUES (:id, :name, :description, now()) ON CONFLICT (name) DO NOTHING"
            ).bindparams(id=perm["id"], name=perm["name"], description=perm["description"])
        )

    # 14. Enable Row Level Security (RLS) on new tables and add policies
    new_rls_tables = [
        "talent_pools",
        "talent_pool_rule_histories",
        "talent_pool_memberships",
        "candidate_relationships",
        "candidate_activities",
        "outreach_sequences",
        "candidate_sequence_enrollments",
        "candidate_merge_logs",
        "match_feedbacks",
    ]
    for table in new_rls_tables:
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
    # 1. Drop RLS policies
    new_rls_tables = [
        "talent_pools",
        "talent_pool_rule_histories",
        "talent_pool_memberships",
        "candidate_relationships",
        "candidate_activities",
        "outreach_sequences",
        "candidate_sequence_enrollments",
        "candidate_merge_logs",
        "match_feedbacks",
    ]
    for table in new_rls_tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")

    # 2. Drop new tables
    op.drop_table("match_score_histories")
    op.drop_table("cached_match_scores")
    op.drop_table("match_feedbacks")
    op.drop_table("candidate_merge_logs")
    op.drop_table("candidate_sequence_enrollments")
    op.drop_table("outreach_sequences")
    op.drop_table("candidate_activities")
    op.drop_table("candidate_relationships")
    op.drop_table("talent_pool_memberships")
    op.drop_table("talent_pool_rule_histories")
    op.drop_table("talent_pools")

    # 3. Clean up added permissions
    op.execute(
        sa.text(
            "DELETE FROM permissions WHERE name IN "
            "('view_talent_crm', 'manage_talent_pools', 'manage_candidate_relationships', 'run_ai_rediscovery', 'export_talent_search')"
        )
    )

    # 4. Remove columns from existing tables
    op.drop_column("saved_searches", "last_searched_at")
    op.drop_column("saved_searches", "search_type")
    op.drop_column("candidate_profiles", "resume_version")
    op.drop_column("jobs", "job_version")
