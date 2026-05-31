import pytest
import os
import uuid
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from db.session import tenant_context, get_db
from core.embeddings import EmbeddingService
from models import Company, Candidate, CandidateEmbedding, Job, Application, AuditLog
from models.enums import CompanyStatus, JobStatus, ApplicationStatus
from server import app


@pytest.fixture
def api_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


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
    with tenant_context(tenant_id=str(co_a.id)):
        all_embeddings = list(db_session.scalars(select(CandidateEmbedding)).all())
        embedding_ids = [emb.id for emb in all_embeddings]
        assert embed_a.id in embedding_ids
        assert embed_b.id not in embedding_ids

        direct_hidden = db_session.scalar(select(CandidateEmbedding).where(CandidateEmbedding.id == embed_b.id))
        assert direct_hidden is None

    # 5. Query under Company B context
    with tenant_context(tenant_id=str(co_b.id)):
        all_embeddings = list(db_session.scalars(select(CandidateEmbedding)).all())
        embedding_ids = [emb.id for emb in all_embeddings]
        assert embed_b.id in embedding_ids
        assert embed_a.id not in embedding_ids

        direct_hidden = db_session.scalar(select(CandidateEmbedding).where(CandidateEmbedding.id == embed_a.id))
        assert direct_hidden is None


def test_candidate_match_discovery(api_client, db_session):
    """Verify semantic candidate matches endpoint ranks using average similarity of top N=3 chunks under tenant RLS."""
    # 1. Register Company A & B
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "Discovery A",
        "email": "owner_discover@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Discover Owner"
    })
    token_a = resp_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    comp_a_id = uuid.UUID(resp_a.json()["user"]["company_id"])

    resp_b = api_client.post("/api/v1/auth/register", json={
        "company_name": "Discovery B",
        "email": "owner_discover_b@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Discover Owner B"
    })
    token_b = resp_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    comp_b_id = uuid.UUID(resp_b.json()["user"]["company_id"])

    # 2. Setup job & candidates
    with tenant_context(auth_mode="true"):
        job = Job(
            company_id=comp_a_id,
            title="Python Developer",
            department="Engineering",
            description="Seeking a backend engineer skilled in FastAPI, SQL, and Celery.",
            status=JobStatus.OPEN,
        )
        db_session.add(job)
        db_session.flush()

        # Candidate 1 (Strong match - multiple python chunks)
        cand_strong = Candidate(company_id=comp_a_id, full_name="Jane Python", email="jane@python.com")
        # Candidate 2 (Weak match - unrelated chunks)
        cand_weak = Candidate(company_id=comp_a_id, full_name="John Unrelated", email="john@unrelated.com")
        # Candidate 3 (Company B candidate - isolated)
        cand_isolated = Candidate(company_id=comp_b_id, full_name="Bob Isolated", email="bob@isolated.com")

        db_session.add_all([cand_strong, cand_weak, cand_isolated])
        db_session.commit()

    # 3. Add chunks embeddings
    embedder = EmbeddingService()
    with tenant_context(auth_mode="true"):
        # Strong Candidate embeddings (FastAPI, SQL, Celery)
        db_session.add_all([
            CandidateEmbedding(
                company_id=comp_a_id, candidate_id=cand_strong.id, chunk_index=0,
                chunk_text="FastAPI backend development expert",
                resume_embedding=embedder.generate_embedding("FastAPI backend development expert")
            ),
            CandidateEmbedding(
                company_id=comp_a_id, candidate_id=cand_strong.id, chunk_index=1,
                chunk_text="Writing clean SQL queries and PostgreSQL RLS",
                resume_embedding=embedder.generate_embedding("Writing clean SQL queries and PostgreSQL RLS")
            ),
            CandidateEmbedding(
                company_id=comp_a_id, candidate_id=cand_strong.id, chunk_index=2,
                chunk_text="Celery async workers task scheduling",
                resume_embedding=embedder.generate_embedding("Celery async workers task scheduling")
            )
        ])
        
        # Weak Candidate embeddings (unrelated items)
        db_session.add_all([
            CandidateEmbedding(
                company_id=comp_a_id, candidate_id=cand_weak.id, chunk_index=0,
                chunk_text="Cooking french pastries and baking sourdough",
                resume_embedding=embedder.generate_embedding("Cooking french pastries and baking sourdough")
            )
        ])

        # Isolated Candidate embeddings
        db_session.add(
            CandidateEmbedding(
                company_id=comp_b_id, candidate_id=cand_isolated.id, chunk_index=0,
                chunk_text="FastAPI python backend developer",
                resume_embedding=embedder.generate_embedding("FastAPI python backend developer")
            )
        )
        db_session.commit()

    # 4. Trigger matches endpoint for Company A
    match_resp = api_client.post(f"/api/v1/jobs/{job.id}/candidate-matches", headers=headers_a)
    assert match_resp.status_code == 200
    matches = match_resp.json()

    # Ranked by top N=3 average similarity: Jane Python should rank higher than John Unrelated
    assert len(matches) == 2
    assert matches[0]["candidate_id"] == str(cand_strong.id)
    assert matches[0]["full_name"] == "Jane Python"
    assert matches[1]["candidate_id"] == str(cand_weak.id)
    assert matches[1]["full_name"] == "John Unrelated"

    # Enforce multi-tenant vector RLS boundary: Bob Isolated should not appear in Company A results
    assert str(cand_isolated.id) not in [m["candidate_id"] for m in matches]

    # Verify Company B can trigger matches but gets only Company B candidate
    match_b_resp = api_client.post(f"/api/v1/jobs/{job.id}/candidate-matches", headers=headers_b)
    # Job B is in Company A, B cannot access it (404/403 or blocked RLS)
    assert match_b_resp.status_code == 404

    # Verify ai.discovery_searched event
    with tenant_context(auth_mode="true"):
        audit_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "ai.discovery_searched").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(audit_logs) >= 1
        assert audit_logs[0].metadata_json["candidate_match_count"] == 2


def test_resume_rag_answering(api_client, db_session):
    """Verify resume Q&A (RAG) assistant answers grounded questions and blocks below-threshold queries."""
    # 1. Register Company A
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "RAG Co",
        "email": "owner_rag@corp.com",
        "password": "super-secure-password-123",
        "full_name": "RAG Owner"
    })
    token_a = resp_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    comp_a_id = uuid.UUID(resp_a.json()["user"]["company_id"])

    # 2. Setup job, candidate, application
    with tenant_context(auth_mode="true"):
        job = Job(
            company_id=comp_a_id,
            title="FastAPI Dev",
            department="Engineering",
            description="FastAPI python",
            status=JobStatus.OPEN,
        )
        db_session.add(job)
        db_session.flush()

        candidate = Candidate(company_id=comp_a_id, full_name="Jane Dev", email="jane@dev.com")
        db_session.add(candidate)
        db_session.flush()

        application = Application(
            company_id=comp_a_id, job_id=job.id, candidate_id=candidate.id, status=ApplicationStatus.SCREENING
        )
        db_session.add(application)
        db_session.commit()

        # Add resume embedding
        embedder = EmbeddingService()
        db_session.add(
            CandidateEmbedding(
                company_id=comp_a_id, candidate_id=candidate.id, chunk_index=0,
                chunk_text="5 years experience in Python and FastAPI and pgvector.",
                resume_embedding=embedder.generate_embedding("5 years experience in Python and FastAPI and pgvector.")
            )
        )
        db_session.commit()

    # 3. Test Similarity Threshold Grounded Refusal
    # Answering an entirely unrelated question should fail context thresholds (all chunks score < 0.35)
    with patch("core.embeddings.EmbeddingService.compute_similarity", return_value=0.2):
        unrelated_resp = api_client.post(
            f"/api/v1/applications/{application.id}/qa",
            json={"question": "What is the candidate's favorite recipe for chocolate chip cookies?"},
            headers=headers_a
        )
    assert unrelated_resp.status_code == 200
    unrelated_data = unrelated_resp.json()
    assert "apologize" in unrelated_data["answer"].lower()
    assert unrelated_data["source_chunks"] == []

    # Verify audit log recorded blocked answer
    with tenant_context(auth_mode="true"):
        audit_logs = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "ai.rag_answer_generated").order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(audit_logs) >= 1
        assert audit_logs[0].metadata_json["source_chunk_count"] == 0
        assert audit_logs[0].metadata_json["threshold_blocked"] is True

    # 4. Test Valid Q&A with Mocked ChatGroq RAG invoke
    mock_llm_response = MagicMock()
    mock_llm_response.content = "Jane Dev has 5 years of experience in Python and FastAPI."

    with patch("langchain_groq.ChatGroq.invoke") as mock_invoke:
        mock_invoke.return_value = mock_llm_response

        valid_resp = api_client.post(
            f"/api/v1/applications/{application.id}/qa",
            json={"question": "What is the candidate's Python and FastAPI experience?"},
            headers=headers_a
        )
        assert valid_resp.status_code == 200
        valid_data = valid_resp.json()
        assert valid_data["answer"] == "Jane Dev has 5 years of experience in Python and FastAPI."
        assert len(valid_data["source_chunks"]) == 1
        assert valid_data["source_chunks"][0]["chunk_index"] == 0
        assert valid_data["source_chunks"][0]["similarity_score"] >= 0.35

        # Verify RAG answer metadata generated audit event in DB (without answer leak)
        with tenant_context(auth_mode="true"):
            answer_logs = db_session.scalars(
                select(AuditLog).where(
                    AuditLog.action == "ai.rag_answer_generated",
                    AuditLog.resource_id == str(application.id)
                ).order_by(AuditLog.timestamp.desc())
            ).all()
            assert len(answer_logs) >= 1
            assert answer_logs[0].metadata_json["source_chunk_count"] == 1
            assert answer_logs[0].metadata_json["threshold_blocked"] is False
            # Check answer content is completely omitted in metadata
            assert "Jane Dev" not in str(answer_logs[0].metadata_json)


def test_candidates_compare(api_client, db_session):
    """Verify that the POST /api/v1/candidates/compare endpoint invokes ChatGroq and logs comparative event."""
    # 1. Register Company
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Compare Co",
        "email": "owner_compare@corp.com",
        "password": "super-secure-password-123",
        "full_name": "Compare Owner"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    comp_id = uuid.UUID(resp.json()["user"]["company_id"])

    # 2. Setup Candidates
    with tenant_context(auth_mode="true"):
        cand_1 = Candidate(company_id=comp_id, full_name="Candidate One", email="one@corp.com")
        cand_2 = Candidate(company_id=comp_id, full_name="Candidate Two", email="two@corp.com")
        db_session.add_all([cand_1, cand_2])
        db_session.commit()

    mock_llm_response = MagicMock()
    mock_llm_response.content = "# Candidate Comparison Report\n- Candidate One is strong."

    with patch("langchain_groq.ChatGroq.invoke") as mock_invoke:
        mock_invoke.return_value = mock_llm_response

        # 3. Call candidates compare endpoint
        payload = {
            "candidate_ids": [str(cand_1.id), str(cand_2.id)],
            "job_description": "Need a senior backend engineer."
        }
        comp_resp = api_client.post("/api/v1/candidates/compare", json=payload, headers=headers)
        assert comp_resp.status_code == 200
        comp_data = comp_resp.json()
        assert "Candidate One" in comp_data["comparison_report"]

        # Verify ai.candidates_compared audit log in DB
        with tenant_context(auth_mode="true"):
            compare_logs = db_session.scalars(
                select(AuditLog).where(AuditLog.action == "ai.candidates_compared").order_by(AuditLog.timestamp.desc())
            ).all()
            assert len(compare_logs) == 1
            assert compare_logs[0].metadata_json["compared_candidate_count"] == 2
