# Sprint 8 — Principal AI Engineer Review

**Review Date:** 2026-06-18
**Reviewer:** Principal AI Engineer, RAG Architect, Staff LLM Engineer
**Sprint Reviewed:** Sprint 8 — Knowledge & RAG System
**Documents Audited:** SPRINT_8.md (full implementation)
**Classification:** Confidential — Internal

---

## Verdict: CONDITIONALLY APPROVED — 1 Critical Gap, 3 Major Issues

The Sprint 8 RAG architecture is well-designed. The hybrid retrieval pattern is correct. The chunking strategies are sensible. The agent integration follows the established pattern from Sprint 7. However, one critical gap mirrors the Sprint 7 embedding issue — keyword search is non-functional because `content_tsv` is never populated. Three major issues affect correctness and performance.

---

## Eight Evaluation Questions — Answered First

### Q1: Does retrieved knowledge actually influence agent behavior?

**Answer: Yes — the wiring follows the proven Sprint 7 pattern.**

The `context_builder_node` loads `knowledge_context` from hybrid search results. The `intent_router_node` prepends it to the enriched message. The `task_planner` includes it in `_build_planning_prompt`. The `result_synthesizer` reading path is implied (it reads `memory_context` — `knowledge_context` should be added explicitly but the pattern exists).

Unlike Sprint 7's initial implementation, where memory was loaded but never read, the Sprint 8 code reuses the same consumption pattern that was fixed in Sprint 7 v7.0.2. The wires are connected on arrival.

**Minor gap:** `result_synthesizer_node` explicitly reads `memory_context` for personalization but doesn't explicitly reference `knowledge_context`. Add a knowledge-aware synthesis path (e.g., "Based on the job description, I notice they emphasize...").

### Q2: Are chunk sizes appropriate?

**Answer: Yes — 500 chars with 100-char overlap is correct for this domain.**

Resumes, job descriptions, and application notes are dense factual documents. 500 characters captures 2-3 paragraphs or 1-2 job requirements. The 100-char overlap prevents information from being severed at chunk boundaries — a skill requirement that starts at character 480 of one chunk will appear at the start of the next chunk.

The three strategies (semantic, sentence, fixed) provide appropriate defaults:
- **Semantic** (default): Best for resumes and narrative documents
- **Sentence**: Better for job descriptions with bullet points
- **Fixed**: Fallback for unstructured text

### Q3: Is retrieval quality measurable?

**Answer: Not yet. No evaluation framework exists.**

The system retrieves chunks and scores them, but there's no way to measure whether the retrieved chunks are actually relevant. Add:
- `precision@5`: Of the top 5 retrieved chunks, how many are relevant?
- `recall@20`: Of all relevant chunks in the corpus, how many are retrieved?
- Human relevance judgments on 100 query-document pairs

This is acceptable for MVP — the framework should be built when there's sufficient user data to evaluate against.

### Q4: Is hybrid retrieval implemented correctly?

**Answer: The architecture is correct. The scoring formula is flawed.**

**What's right:** Vector search and keyword search run concurrently via `asyncio.gather`. Results are merged with configurable weights. Both searches respect filters and user isolation.

**What's wrong — positional scoring, not relevance scoring:**

```python
# CURRENT (positional — incorrect):
vector_score = 1.0 - (i / max(len(vector_results), 1))
# Result at position 10 of 50 gets: 1.0 - 0.2 = 0.8
# Result at position 1 of 50 gets: 1.0 - 0.02 = 0.98
# These are arbitrary — they don't reflect actual similarity.

# CORRECT (relevance-based):
# Vector: use actual cosine distance → similarity
# Keyword: use actual ts_rank value
# Normalize both to 0-1, then merge with weights
```

**Fix:** For vector results, compute similarity from the pgvector distance: `similarity = 1.0 - distance`. For keyword results, use `ts_rank` normalized by max rank. This is a 20-line fix.

### Q5: Are embeddings generated reliably?

**Answer: Yes — same pattern as Sprint 7 v7.0.2 (proven).**

The ingestion pipeline loops `generate_embedding()` for each chunk with individual error handling. Failed embeddings leave the chunk stored without embedding — searchable by keyword but not by vector until backfilled. This is the correct graceful degradation pattern.

### Q6: Is re-ranking worth the cost?

**Answer: Yes, for the top-20 → top-5 path. One optimization needed.**

The LLM re-ranking call costs ~200 tokens per query. At 100 agent invocations/day for 100K users, that's ~$20/day in API costs. The value: taking 5 most relevant chunks from 20 candidates significantly improves context quality.

**Optimization:** Cache re-ranking results for identical (query_hash, top_chunk_ids_hash) pairs with a 1-hour Redis TTL. This reduces costs by ~40% for repeated queries.

### Q7: Will this scale to 100k users?

**Answer: Yes, with the same caveats as Sprint 7.**

- **Vector search:** HNSW index on 3072d vectors. Sub-10ms for top-50. Scales linearly with concurrent queries.
- **Keyword search:** GIN index on tsvector. Sub-5ms. Scales well.
- **Ingestion:** Embedding generation is the bottleneck. 5 chunks × 100ms per embedding = 500ms per document. This should be async (Celery), not synchronous in the request handler.
- **Storage:** 100K users × 50 chunks = 5M rows. pgvector with HNSW handles this comfortably.

### Q8: Are hallucination risks reduced?

**Answer: Yes — RAG is the primary hallucination mitigation.**

By injecting relevant document chunks into the agent's context, the LLM has factual grounding for its responses. When a user asks "What does the job require?", the LLM sees the actual job description text in `knowledge_context` rather than relying on training data. This is the correct application of RAG.

**One gap:** There's no explicit instruction in the LLM prompts to prefer retrieved knowledge over parametric knowledge. Add to the system prompts: "Prefer information from the provided context over your training data. If the context contradicts your knowledge, trust the context."

---

## Detailed Audit Findings

### 1. Document Ingestion Pipeline — B+

**What's right:** Clean 3-step pipeline: extract → chunk → embed → store. Supports PDF, DOCX, TXT, Markdown. Error isolation per chunk. Document-level metadata tracking.

### 2. Chunking Strategy — B+

**What's right:** Three strategies. Semantic (paragraph boundary) is the correct default for this domain. Overlap prevents boundary severing. Target size is appropriate.

**MIN-1: No token-count-based splitting.** The 500-char target is a proxy for tokens but 500 chars of Python code ≠ 500 chars of English prose in token count. Use `tiktoken` for accurate chunk sizing in V1.

### 3. Embedding Generation — B

**What's right:** Individual error handling per chunk. Failed embeddings leave chunk stored for keyword search. 3072d vector dimension validated.

**MIN-2: Embedding model version not stored per chunk.** If the embedding model changes (e.g., DeepSeek upgrades from v2 to v3), old chunks have incompatible embeddings. The `embedding_model` field exists on `KnowledgeDocument` but not on `KnowledgeChunk`. Store it per chunk for future re-embedding migration.

### 4. pgvector Schema — B-

**CRIT-1: `content_tsv` is stored as Text, never populated, and queried as tsvector.**

```python
# Model declares:
content_tsv: Mapped[str | None] = mapped_column(Text, nullable=True)

# Keyword search queries:
KnowledgeChunkModel.content_tsv.op("@@")(ts_query)

# But NO code ever sets content_tsv = to_tsvector('english', content)
```

The column type should be `TSVector`, not `Text`. The GIN index `idx_kchunk_tsv` was created on a Text column, which means it's a regular B-tree on text, not a GIN on tsvector. `@@` operator on a Text column will either error or produce incorrect results.

**This is the exact same class of bug as Sprint 7's embedding issue — infrastructure exists but the data is never populated.**

**Fix:** Change the column to a generated column:
```sql
ALTER TABLE knowledge_chunks 
  ADD COLUMN content_tsv tsvector 
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;
```
Then rebuild the GIN index on the tsvector column. This is a migration change.

### 5. HNSW Indexing — B+

**What's right:** m=16, ef_construction=200. Cosine distance operator. Same proven config as semantic_memories. Separate from the tsvector GIN index — vector and keyword search use different index types, which is correct.

### 6. Hybrid Retrieval Quality — C+

**MAJ-1: Positional scoring instead of relevance scoring (see Q4).**

### 7. Re-ranking Quality — B

**What's right:** LLM-based relevance scoring. Structured system prompt. Graceful fallback to score-based. Capped at top-5 output.

**MIN-3: No prompt instructs the LLM to use retrieved context over training data (see Q8).**

### 8. Metadata Filtering — B

**What's right:** Filter by `source_type` and `job_id`. JSONB path queries. User isolation via `user_id` in WHERE clause.

**MIN-4: Tag filtering is declared but not implemented.** The `ChunkMetadata.tags` field exists and the `RetrievalQuery.filters` dict accepts arbitrary keys, but the repository's `_apply_filters` only handles `source_type` and `job_id`. Tag filtering is a documented gap.

### 9. Context Assembly — B

**What's right:** Top-5 chunks formatted as `[Source: name] content...` blocks. Concatenated with newlines. Injected as `knowledge_context`.

**MAJ-2: No token budget for knowledge_context.** Memory context has a 2,000 token budget (from Sprint 7). Knowledge context has no budget. If 5 chunks are 500 chars each plus metadata, that's ~3,000 chars ≈ 750 tokens. Combined with memory (2,000) + profile + LLM prompt, this pushes against the 8K context window for cheaper models.

**Fix:** Add token counting and trim knowledge_context to fit within a 1,500 token budget. Prioritize chunks with higher `score` values.

### 10. Agent Integration — B+

**What's right:** Follows the proven Sprint 7 pattern. `knowledge_context` flows from context_builder → state → LLM nodes. The consumption path is established.

**MIN-5: `result_synthesizer_node` doesn't explicitly reference `knowledge_context`.** The other two LLM nodes (intent_router, task_planner) do. Add knowledge-aware suggestions in the synthesizer: "Based on the job description, the key requirements are..."

### 11. Token Efficiency — C+

**MAJ-2 (duplicate): No token budget.**

**MIN-6: No context compression for long chunks.** Chunks are capped at retrieval (`.content[:500]`) but the full chunk can be up to 600 characters with the overlap. For dense documents, consider LLM-based compression: "Summarize this chunk in 1 sentence for context injection."

### 12. Cost Efficiency — B

**What's right:** Embedding generation is one-per-chunk (not real-time — ingestion only). LLM re-ranking is lightweight (~200 tokens). Hybrid search uses database indexes (no API cost).

**MAJ-3: Auto-indexing on profile save is synchronous (see Q7).** Profile save → triggers `pipeline.ingest()` → waits for chunking + embedding → responds. This adds 2-5 seconds to the profile endpoint. Move to Celery background task.

### 13. Retrieval Latency — B

Estimated latencies:
- Vector search (HNSW, top-50): < 10ms
- Keyword search (GIN, top-50): < 5ms
- Concurrent execution: max(10ms, 5ms) = ~10ms
- Merge + score: < 1ms
- LLM re-rank (top-20 → 5): ~200ms
- **Total: ~215ms** — well within the 500ms target.

### 14. Security — B+

**What's right:** All queries scoped to `user_id`. Document ownership enforced. No cross-user knowledge access.

### 15. Multi-Tenant Isolation — B+

**What's right:** `user_id` on every chunk and document. Deletion by user cascades. No tenant can access another tenant's knowledge.

### 16. Knowledge Lifecycle — B-

**What's right:** Ingest → index → search → re-index → delete. Document-level tracking with `is_indexed` flag.

**MAJ-4: No deduplication on re-ingestion (see below).**

**MIN-7: `DELETE /v1/knowledge/documents/{id}` deletes chunks but not the document itself.** The document row remains as an orphan. Should be: delete chunks → delete document (cascade would handle this if the FK had `ON DELETE CASCADE`).

### 17. GDPR Deletion — B

**What's right:** `delete_by_user` method on chunk repository removes all chunks. Document repository has a `delete` method.

**MIN-8: No cascading document deletion.** Deleting a user should cascade: user → knowledge_documents → knowledge_chunks. Verify the FK constraints have `ON DELETE CASCADE`.

### 18. Testing Coverage — C+

**What's right:** Chunking tests cover edge cases. Entity tests verify domain behavior. Ingestion integration test exists.

**Missing:**
- No hybrid retrieval quality test (MAJ-1 prevents meaningful testing)
- No re-ranking test
- No agent integration test proving knowledge influences behavior
- No keyword search test (CRIT-1 prevents functional testing)
- No metadata filtering test

---

## Issue Summary

| ID | Severity | Area | Issue |
|----|----------|------|-------|
| CRIT-1 | CRITICAL | Schema | `content_tsv` never populated — keyword search returns empty |
| MAJ-1 | MAJOR | Retrieval | Positional scoring instead of relevance scoring in hybrid merge |
| MAJ-2 | MAJOR | Context | No token budget for knowledge_context |
| MAJ-3 | MAJOR | Ingestion | Auto-indexing synchronous in request handler (blocks profile save) |
| MAJ-4 | MAJOR | Lifecycle | No dedup on re-ingestion — duplicate knowledge accumulates |
| MIN-1 | MINOR | Chunking | Char-based sizing, not token-based |
| MIN-2 | MINOR | Embeddings | Model version not stored per chunk |
| MIN-3 | MINOR | Re-ranking | No context-over-training preference instruction |
| MIN-4 | MINOR | Metadata | Tag filtering declared but not implemented |
| MIN-5 | MINOR | Agent | Result synthesizer doesn't reference knowledge_context |
| MIN-6 | MINOR | Context | No compression for long chunks |
| MIN-7 | MINOR | API | Document row not deleted with chunks |
| MIN-8 | MINOR | GDPR | Cascading delete not verified |

---

## RAG Best Practice Recommendations

1. **Use generated tsvector columns, not Text.** PostgreSQL's `GENERATED ALWAYS AS (to_tsvector(...)) STORED` is the correct pattern. Text columns with GIN indexes don't support `@@` correctly. This is the CRIT-1 fix.

2. **Score by relevance, not position.** Use actual cosine similarity (1.0 - distance) for vector results and normalized `ts_rank` for keyword results. Merge with weighted arithmetic mean.

3. **Move ingestion to background jobs.** Document ingestion (chunking + embedding) should be a Celery task. The API returns 202 Accepted with a job ID. The user polls or receives a webhook when indexing is complete.

4. **Add a context-over-training instruction.** Every LLM prompt that includes retrieved knowledge should explicitly state: "Prefer information from the provided context. If the context contradicts your training data, trust the context." This is the standard RAG safety pattern.

5. **Store embedding model version per chunk.** When the embedding model is upgraded, chunks with the old model version can be identified and re-embedded. Without this, old chunks become increasingly irrelevant as the model evolves.

6. **Implement retrieval evaluation.** Track `precision@5` and `recall@20` using implicit feedback (did the user click/apply after seeing these results?) as ground truth. This is how you know if RAG is actually working.

7. **Add query rewriting.** Before retrieval, expand the user query with related terms. "python jobs" → "python developer positions software engineer". This improves recall without sacrificing precision.

---

## Remediation Requirements

### Must-Fix Before Production (4 hours)

| Fix | Effort |
|-----|--------|
| **CRIT-1:** Change content_tsv to generated tsvector column + rebuild GIN index | 1.5h |
| **MAJ-1:** Fix hybrid scoring to use relevance scores, not positional | 1h |
| **MAJ-2:** Add token budget for knowledge_context (1,500 tokens) | 30 min |
| **MAJ-3:** Move auto-indexing to Celery background task | 1h |

### Should-Fix Before Sprint 9 (2 hours)

| Fix | Effort |
|-----|--------|
| MAJ-4: Check for existing document before re-ingestion (UPSERT pattern) | 30 min |
| MIN-5: Add knowledge_context awareness to result_synthesizer | 30 min |
| MIN-7: Fix document deletion cascade | 15 min |
| MIN-3: Add context-over-training instruction to LLM prompts | 30 min |

---

## Production Readiness Assessment

| Criterion | Status | Notes |
|-----------|--------|-------|
| **Ingestion pipeline** | ✅ | Extract → chunk → embed → store |
| **Chunking** | ✅ | 3 strategies, appropriate sizes |
| **Embedding generation** | ✅ | Same proven pattern as Sprint 7 |
| **Keyword search** | ❌ CRIT-1 | tsvector never populated |
| **Hybrid retrieval** | ⚠️ MAJ-1 | Positional scoring incorrect |
| **Re-ranking** | ✅ | LLM-based with graceful fallback |
| **Agent integration** | ✅ | Follows proven Sprint 7 pattern |
| **Token budget** | ❌ MAJ-2 | Unbounded knowledge context |
| **Ingestion performance** | ❌ MAJ-3 | Blocks profile save endpoint |
| **Lifecycle** | ⚠️ MAJ-4 | Re-ingestion creates duplicates |
| **Security** | ✅ | User isolation on all queries |
| **Testing** | ⚠️ | Core paths covered, gaps documented |

---

## SPRINT 8 CONDITIONALLY APPROVED FOR PRODUCTION

**Condition:** Fix CRIT-1 (tsvector population), MAJ-1 (relevance scoring), MAJ-2 (token budget), MAJ-3 (async ingestion). These are ~4 hours of targeted fixes.

The RAG architecture is correct. The hybrid retrieval pattern is well-designed. The embedding generation is reliable (proven pattern from Sprint 7). The agent integration follows established wiring. The critical issue is the same class of bug as Sprint 7's initial embedding gap — infrastructure exists but data is never populated. Fix it and ship.

> *"RAG architecture: correct. tsvector: empty. Fixes: mechanical. After remediation, the agent retrieves what it needs to know, when it needs to know it."*

**End of Sprint 8 Review**
