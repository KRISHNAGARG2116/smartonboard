# Verification Report: Milestone 6 Phase 1 — BGE Semantic Search Foundations

This document provides complete engineering and compliance verification for the initial foundations of **Milestone 6: AI Semantic Search Subsystem (Phase 1)**.

---

## 1. Executive Summary

We have successfully integrated a high-performance, cost-free, and local AI embedding layer standardizing on the **`BAAI/bge-small-en-v1.5`** model (384 dimensions). This gives our recruitment platform semantic capability with:
- Zero API dependency (complete offline capability)
- Curated vector dimensional standard (384 dimensions)
- Native PostgreSQL `pgvector` HNSW support with a dynamic fallback to standard `FLOAT[]` arrays (perfect for offline development/testing)
- Strict tenant isolation enforced by Row-Level Security (RLS) policies at the database layer
- A strict database unique constraint: `UNIQUE(company_id, candidate_id, chunk_index)`

All Phase 1 goals have been implemented and validated through a rigorous test suite.

---

## 2. Database Schema & Migration Specification

A deterministic database migration (`007`) was executed to construct the `candidate_embeddings` table. It dynamically probes the database system for the compiled `pgvector` C extension and initializes the optimized column type or gracefully falls back.

### Migration `007` Features:
1. **Dynamic Extension Probe**: Checks `pg_available_extensions` for the `vector` extension.
2. **Deterministic Falling Back**: If `pgvector` is not available (such as in standard local/CI PostgreSQL engines), it falls back to native `FLOAT[]` (double-precision arrays), maintaining 100% database query capability and preventing container boot failures.
3. **Optimized Indexes**:
   - Creates a high-performance **HNSW cosine index** (`idx_candidate_embeddings_hnsw` using `vector_cosine_ops`) if pgvector is present.
   - Creates a standard index (`idx_candidate_embeddings_standard` over `candidate_id, chunk_index`) under fallback mode for exact chunk ordering.
4. **Strict RLS Multi-Tenant Policy**:
   ```sql
   ALTER TABLE candidate_embeddings ENABLE ROW LEVEL SECURITY;
   ALTER TABLE candidate_embeddings FORCE ROW LEVEL SECURITY;
   CREATE POLICY tenant_isolation_embeddings ON candidate_embeddings
       FOR ALL USING (company_id = NULLIF(current_setting('app.company_id', true), '')::uuid OR current_setting('app.auth_mode', true) = 'true')
       WITH CHECK (company_id = NULLIF(current_setting('app.company_id', true), '')::uuid OR current_setting('app.auth_mode', true) = 'true');
   ```
5. **Deduplication Constraint**: Inserts a strict `UniqueConstraint` on `(company_id, candidate_id, chunk_index)` to prevent duplicate chunk indexing.

---

## 3. Configurable Embedding Service

The embedding system is encapsulated inside `backend/core/embeddings.py`.

- **Lazy-Loading Model Optimization**: Avoids loading the PyTorch weights on server startup (which blocks testing suites or fast healthcheck boots) by deferring initialization of the `SentenceTransformer` model to the first call of `generate_embedding`.
- **Normalization Standard**: Normalizes embeddings natively (`normalize_embeddings=True`) as BGE models achieve optimal cosine matching and dot-product performance when query and document vectors lie on a unit hypersphere (magnitude = 1.0).
- **Graceful Empty Inputs**: Gracefully returns a 384-dimensional zero vector for empty/whitespace queries.

---

## 4. Verification Test Suite

We authored 3 comprehensive, isolated integration tests inside `tests/test_ai_semantic_search.py`:

1. **`test_embedding_generation`**:
   - Asserts the model correctly loads and processes raw text.
   - Validates that the generated embedding is exactly `384` dimensions.
   - Asserts vector normalization (magnitude equals `1.0`).
   - Asserts that empty/whitespace strings return a `384`-dimensional zero vector.
2. **`test_embedding_persistence`**:
   - Inserts and commits a `CandidateEmbedding` record to the database under standard tenant contexts.
   - Refreshes and asserts the persistence of metadata fields (`embedding_provider="huggingface"`, `embedding_model="BAAI/bge-small-en-v1.5"`, `embedding_version=1`).
   - Asserts that trying to insert a duplicate `chunk_index` for the same candidate triggers an `IntegrityError` (verifying our `UniqueConstraint`).
3. **`test_embedding_rls_isolation`**:
   - Enforces strict tenant barriers.
   - Inserts embeddings for Company A and Company B.
   - Verifies Company A can query **ONLY** Company A's embeddings, and direct select queries targeting Company B's records return `None` due to RLS, and vice versa.

---

## 5. Test Results

### Isolated Semantic Search Tests:
```text
tests/test_ai_semantic_search.py ...                                     [100%]

============================== 3 passed in 13.91s ==============================
```

All 3 foundational AI semantic search tests are fully green.
