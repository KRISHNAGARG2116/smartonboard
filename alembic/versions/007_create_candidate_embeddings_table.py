"""create_candidate_embeddings_table

Revision ID: 007
Revises: 006
Create Date: 2026-05-31 16:48:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Check if pgvector extension is available on the PostgreSQL system
    connection = op.get_bind()
    has_vector = False
    try:
        result = connection.execute(sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")).scalar()
        if result == 1:
            has_vector = True
    except Exception:
        pass

    if has_vector:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        from pgvector.sqlalchemy import Vector
        embedding_col = Vector(384) # Standardized to BAAI/bge-small-en-v1.5 384 dim
    else:
        print("WARNING: pgvector C extension not available on this system. Falling back to native FLOAT[] array storage.")
        embedding_col = sa.ARRAY(sa.Float)

    # 2. Create candidate_embeddings table
    op.create_table('candidate_embeddings',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        sa.Column('resume_embedding', embedding_col, nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('embedding_provider', sa.String(length=50), nullable=False, server_default='huggingface'),
        sa.Column('embedding_model', sa.String(length=100), nullable=False, server_default='BAAI/bge-small-en-v1.5'),
        sa.Column('embedding_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'candidate_id', 'chunk_index', name='uq_candidate_embeddings_company_candidate_chunk')
    )
    op.create_index(op.f('ix_candidate_embeddings_candidate_id'), 'candidate_embeddings', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_candidate_embeddings_company_id'), 'candidate_embeddings', ['company_id'], unique=False)

    # 3. Create HNSW index only if pgvector is available
    if has_vector:
        op.execute(
            "CREATE INDEX idx_candidate_embeddings_hnsw ON candidate_embeddings "
            "USING hnsw (resume_embedding vector_cosine_ops)"
        )
    else:
        # Standard index for fast exact chunk lookups
        op.create_index('idx_candidate_embeddings_standard', 'candidate_embeddings', ['candidate_id', 'chunk_index'])

    # 4. Enable Row Level Security (RLS) on candidate_embeddings
    op.execute("ALTER TABLE candidate_embeddings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE candidate_embeddings FORCE ROW LEVEL SECURITY")

    # 5. Create multi-tenant isolation policy on candidate_embeddings
    op.execute("""
        CREATE POLICY tenant_isolation_embeddings ON candidate_embeddings
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
    # Drop RLS policy
    op.execute("DROP POLICY IF EXISTS tenant_isolation_embeddings ON candidate_embeddings")

    # Drop index
    op.execute("DROP INDEX IF EXISTS idx_candidate_embeddings_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_candidate_embeddings_standard")

    # Drop table
    op.drop_index(op.f('ix_candidate_embeddings_company_id'), table_name='candidate_embeddings')
    op.drop_index(op.f('ix_candidate_embeddings_candidate_id'), table_name='candidate_embeddings')
    op.drop_table('candidate_embeddings')
