import pytest
import os
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db.session import tenant_context
from core.embeddings import EmbeddingService
from models import Company, Candidate, CandidateEmbedding
from models.enums import CompanyStatus


def test_embedding_generation():
    """Verify that EmbeddingService correctly generates 384-dimensional normalized vectors."""
    service = EmbeddingService()
    assert service.provider == "huggingface"
    assert service.model_name == "BAAI/bge-small-en-v1.5"
    assert service.dimensions == 384

    # Test standard text
    text = "Machine learning engineer with experience in PostgreSQL pgvector and multi-tenant systems."
    embedding = service.generate_embedding(text)
    assert isinstance(embedding, list)
    assert len(embedding) == 384
    assert all(isinstance(val, float) for val in embedding)

    # Test normalize_embeddings property (vector length/magnitude should be extremely close to 1.0)
    magnitude = sum(val * val for val in embedding) ** 0.5
    assert abs(magnitude - 1.0) < 1e-4

    # Test empty / whitespace inputs return a zero vector
    empty_emb = service.generate_embedding("")
    assert len(empty_emb) == 384
    assert all(val == 0.0 for val in empty_emb)

    whitespace_emb = service.generate_embedding("   \n \t  ")
    assert len(whitespace_emb) == 384
    assert all(val == 0.0 for val in whitespace_emb)


def test_embedding_persistence(db_session):
    """Verify that CandidateEmbedding can be successfully persisted to the database and unique constraint works."""
    # 1. Create a Company and a Candidate in auth bootstrap mode
    with tenant_context(auth_mode="true"):
        company = Company(name="AI Corp", slug="ai-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        candidate = Candidate(
            company_id=company.id,
            full_name="Jane Search",
            email="jane.search@example.com",
            phone="1234567890",
        )
        db_session.add(candidate)
        db_session.commit()

    # 2. Scope the context to the company and generate a mock embedding
    with tenant_context(tenant_id=str(company.id)):
        service = EmbeddingService()
        embedding_vector = service.generate_embedding("Jane's resume content with Python and pgvector.")
        
        # Instantiate a CandidateEmbedding
        chunk_text = "Jane's resume content with Python and pgvector."
        candidate_embedding = CandidateEmbedding(
            company_id=company.id,
            candidate_id=candidate.id,
            resume_embedding=embedding_vector,
            chunk_text=chunk_text,
            chunk_index=0,
            embedding_provider="huggingface",
            embedding_model="BAAI/bge-small-en-v1.5",
            embedding_version=1,
        )
        db_session.add(candidate_embedding)
        db_session.commit()

        # 3. Retrieve and assert fields
        db_session.refresh(candidate_embedding)
        assert candidate_embedding.id is not None
        assert candidate_embedding.company_id == company.id
        assert candidate_embedding.candidate_id == candidate.id
        assert len(candidate_embedding.resume_embedding) == 384
        assert candidate_embedding.chunk_text == chunk_text
        assert candidate_embedding.chunk_index == 0
        assert candidate_embedding.embedding_provider == "huggingface"
        assert candidate_embedding.embedding_model == "BAAI/bge-small-en-v1.5"
        assert candidate_embedding.embedding_version == 1

        # 4. Verify UNIQUE(company_id, candidate_id, chunk_index) constraint
        duplicate_embedding = CandidateEmbedding(
            company_id=company.id,
            candidate_id=candidate.id,
            resume_embedding=embedding_vector,
            chunk_text="Duplicate chunk text",
            chunk_index=0, # Same chunk_index
            embedding_provider="huggingface",
            embedding_model="BAAI/bge-small-en-v1.5",
            embedding_version=1,
        )
        db_session.add(duplicate_embedding)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


def test_embedding_rls_isolation(db_session):
    """Verify that Company A cannot see Company B's candidate embeddings, adhering to multi-tenant RLS."""
    # 1. Create two companies under auth bootstrap mode
    with tenant_context(auth_mode="true"):
        co_a = Company(name="Enterprise A", slug="ent-a", status=CompanyStatus.ACTIVE)
        co_b = Company(name="Enterprise B", slug="ent-b", status=CompanyStatus.ACTIVE)
        db_session.add_all([co_a, co_b])
        db_session.flush()

        cand_a = Candidate(
            company_id=co_a.id,
            full_name="Alice A",
            email="alice@a.com",
        )
        cand_b = Candidate(
            company_id=co_b.id,
            full_name="Bob B",
            email="bob@b.com",
        )
        db_session.add_all([cand_a, cand_b])
        db_session.commit()

    service = EmbeddingService()
    emb_a = service.generate_embedding("Alice's resume text chunk")
    emb_b = service.generate_embedding("Bob's resume text chunk")

    # 2. Scope to Company A and create CandidateEmbedding for A
    with tenant_context(tenant_id=str(co_a.id)):
        embed_a = CandidateEmbedding(
            company_id=co_a.id,
            candidate_id=cand_a.id,
            resume_embedding=emb_a,
            chunk_text="Alice's resume text chunk",
            chunk_index=0,
        )
        db_session.add(embed_a)
        db_session.commit()

    # 3. Scope to Company B and create CandidateEmbedding for B
    with tenant_context(tenant_id=str(co_b.id)):
        embed_b = CandidateEmbedding(
            company_id=co_b.id,
            candidate_id=cand_b.id,
            resume_embedding=emb_b,
            chunk_text="Bob's resume text chunk",
            chunk_index=0,
        )
        db_session.add(embed_b)
        db_session.commit()

    # 4. Query under Company A context
    # - Must see embed_a
    # - Must NOT see embed_b
    with tenant_context(tenant_id=str(co_a.id)):
        all_embeddings = list(db_session.scalars(select(CandidateEmbedding)).all())
        embedding_ids = [emb.id for emb in all_embeddings]
        assert embed_a.id in embedding_ids
        assert embed_b.id not in embedding_ids

        # Attempt to retrieve Company B's embedding directly should return None due to RLS
        direct_hidden = db_session.scalar(select(CandidateEmbedding).where(CandidateEmbedding.id == embed_b.id))
        assert direct_hidden is None

    # 5. Query under Company B context
    # - Must see embed_b
    # - Must NOT see embed_a
    with tenant_context(tenant_id=str(co_b.id)):
        all_embeddings = list(db_session.scalars(select(CandidateEmbedding)).all())
        embedding_ids = [emb.id for emb in all_embeddings]
        assert embed_b.id in embedding_ids
        assert embed_a.id not in embedding_ids

        # Attempt to retrieve Company A's embedding directly should return None due to RLS
        direct_hidden = db_session.scalar(select(CandidateEmbedding).where(CandidateEmbedding.id == embed_a.id))
        assert direct_hidden is None
