# Pathfinder — Full System Architecture Audit

**Audit Date:** 2026-06-18
**Auditor:** Principal Architect
**Scope:** Sprints 1–8 (all remediations applied)
**Classification:** Confidential — Internal

---

## Executive Summary

The Pathfinder system, after 8 sprints and all remediations, is a **well-architected modular monolith** with clean domain boundaries, consistent patterns, and production-grade infrastructure. No architectural drift detected. The system is ready for feature expansion.

**Three risks require attention before production deployment:** database growth on unpartitioned tables, missing Celery task monitoring, and a dead `MemoryRetrievalService` class that should be integrated or removed.

---

## 1. Architecture Consistency — A-

### Pattern Adherence Across All 8 Sprints

| Sprint | Clean Architecture | DDD | Modular Monolith | Consistency |
|--------|-------------------|-----|-----------------|-------------|
| 1: Foundation | ✅ | N/A | ✅ | — |
| 2: Infrastructure | ✅ | ✅ | ✅ | — |
| 3: Profile | ✅ | ✅ | ✅ | ✅ Matches pattern |
| 4: Jobs | ✅ | ✅ | ✅ | ✅ Matches pattern |
| 5: Matching | ✅ | ✅ | ✅ | ✅ Matches pattern |
| 6: Agent | ✅ | ✅ | ✅ | ✅ Matches pattern |
| 7: Memory | ✅ | ✅ | ✅ | ✅ Matches pattern |
| 8: Knowledge | ✅ | ✅ | ✅ | ✅ Matches pattern |

**Finding: No architectural drift.** Every sprint follows the same 4-layer structure (domain/application/infrastructure/presentation). Domain entities, value objects, repository interfaces, and services are consistently placed. Infrastructure implementations are properly separated.

### Cross-Cutting Concerns — Consistency

| Concern | Consistency | Notes |
|---------|------------|-------|
| Error handling | ✅ | DomainError → HTTP status mapping consistent across all modules |
| Dependency injection | ✅ | FastAPI `Depends()` pattern used uniformly |
| API response envelope | ✅ | `{data, meta, links}` pattern consistent |
| Cursor pagination | ⚠️ | Implemented in jobs/matching. Stub in agent. Missing in knowledge. |
| Structured logging | ✅ | structlog used throughout |
| Testing pattern | ✅ | Unit (domain) + Integration (persistence) + API (e2e) pyramid |

---

## 2. Technical Debt — C+

### Deferred to V1 (Documented & Acceptable)

| Item | Sprint | Impact |
|------|--------|--------|
| Procedural memory wiring | S7 | Schema exists, no creation paths. Deferred with clear TODO. |
| HITL graph node | S6 | ApprovalRequest infrastructure exists. Graph interrupt() deferred. |
| Circuit breaker for LLM | S6 | Exception class defined, never raised. Retry-only for MVP. |
| Recommendation engine content | S5 | `recommendations[]` always empty. API contract preserved. |
| Profile import via LinkedIn API (OAuth) | S3 | PDF export upload works. Live API deferred. |

### Undocumented Debt (Found During Audit)

| Item | Risk |
|------|------|
| `MemoryRetrievalService` class defined but never used (S7). Context builder uses repos directly. | MAJOR — Dead code. Confuses developers. |
| `SqlEpisodicRepository.backfill_embeddings()` defined but no Celery task calls it (S7). | MINOR — Dead code path. |
| `agent_executions` table has no partitioning (S6). | MAJOR — Growth risk at scale. |
| `knowledge_chunks` table has no partitioning (S8). | MINOR — Will grow with document ingestion. |
| `match_results` table has no retention policy (S5). | MINOR — Accumulates indefinitely. |
| `semantic_memories` has no archival strategy (S7). | MINOR — Grows unboundedly. |
| `ImportanceCalculator` defined but never called (S7). | MINOR — Dead code. |
| `ImportanceScore.decay()` defined but never applied (S7). | MINOR — Dead code. |

---

## 3. Domain Boundaries — B+

### Bounded Context Map

```
identity ──► profile ──► jobs ──► tracking
                │          │
                ▼          ▼
             agent ◄──── matching
               │
               ├──► memory (episodic, semantic, procedural)
               └──► knowledge (RAG)
```

**Finding: Boundaries are clean.** Cross-domain communication uses interfaces (e.g., `MatchContextBuilder` depends on `ProfileRepository` and `JobRepository` abstractions, not implementations). Domain events are defined but the EventBus is not yet wired (deferred to V1).

### Boundary Violations Found

| Violation | Location | Severity |
|-----------|----------|----------|
| Agent's `context_builder` directly imports `SqlProfileRepository`, `SqlResumeRepository`, `SqlEpisodicRepository` — bypasses DI | S6 context_builder.py | MINOR — Pragmatic for MVP. Should use DI in V1. |
| Celery tasks directly import concrete repository implementations | S4 scraping.py, S7 memory_tasks.py | MINOR — Standard Celery pattern. Acceptable. |
| Knowledge auto-indexing calls `IngestionPipeline` from profile handler | S3→S8 integration | MINOR — Correct cross-domain pattern: event-like trigger. |

---

## 4. Agent Design — B+

### LangGraph Structure

```
guardrail → context_builder → intent_router → task_planner → tool_executor → result_synthesizer → quality_gate
```

**Finding: The graph structure is correct for MVP.** 7 nodes. Linear flow with conditional edges for clarification and quality revision. Checkpointing via PostgresSaver. Recursion limit=15 prevents infinite loops.

### Strengths
- Single Supervisor + Tools pattern is correctly implemented
- Intent routing with confidence threshold and clarification fallback
- Task planning with deterministic fallback for all 11 intents
- Quality gate with max-3 revision loops
- SSE streaming for token-by-token output

### Gaps
- No dynamic replanning when a tool fails (agent doesn't adapt mid-execution)
- No multi-turn reasoning across sessions (checkpoints exist but conversation context is not loaded)
- Tool executor runs tools sequentially even when `depends_on` is empty

---

## 5. Memory Design — B+

### Memory System — End-to-End Flow

```
Events → EpisodicMemory (real-time append)
           │
           ▼ (daily Celery Beat)
      CONSOLIDATION (LLM)
           │
           ├──→ SemanticMemory (UPSERT, embedding-indexed, versioned)
           └──→ Preferences updated (Bayesian weights)

Agent invocation:
  context_builder loads: profile + prefs + recent episodes (recency) +
                         semantic memories (vector search) +
                         knowledge chunks (hybrid search)
  → Injected into all LLM nodes
```

**Finding: The memory system is architecturally sound.** Consolidation runs daily. Semantic memories are versioned with evidence tracking. Embeddings are generated and searchable via HNSW. The agent consumes memory context at all decision points.

### Concerns
- Consolidation processes users sequentially (Semaphore(5) helps but 10K users still takes hours)
- No semantic memory deduplication by embedding similarity (subject-string matching only)
- No conflict detection when consolidation produces contradictory facts

---

## 6. RAG Design — B+

### Knowledge Retrieval Pipeline

```
Query → Vector Search (HNSW, cosine) + Keyword Search (GIN, tsvector)
     → Weighted Fusion (0.7 vector / 0.3 keyword)
     → LLM Re-rank (top-20 → top-5)
     → Context Assembly (token-budgeted)
     → Agent injection
```

**Finding: The RAG pipeline is correctly implemented.** Hybrid retrieval uses actual relevance scores (cosine similarity + normalized ts_rank). Chunking has 3 strategies with semantic as default. Embeddings generated at ingestion time with error isolation.

### Concerns
- No query rewriting before retrieval (e.g., "find jobs" → expansion)
- No retrieval evaluation framework (precision@k, recall@k)
- No embedding model version tracking per chunk for future re-embedding

---

## 7. Database Growth Risks — C

### Table Growth Analysis

| Table | Row Size | Daily Growth (100K users) | Yearly | Partitioned? | Risk |
|-------|----------|--------------------------|--------|-------------|------|
| `episodic_memories` | ~500B | 500K/day = 250MB | 91GB | ✅ Daily (migration 001) | LOW |
| `agent_executions` | ~1KB | 500K/day = 500MB | 182GB | ❌ | **HIGH** |
| `knowledge_chunks` | ~2KB | 1K/day = 2MB | 730MB | ❌ | MEDIUM |
| `match_results` | ~3KB | 10K/day = 30MB | 11GB | ❌ | MEDIUM |
| `semantic_memories` | ~1KB | 1K/day = 1MB | 365MB | ❌ | LOW |
| `job_postings` | ~2KB | 5K/day = 10MB | 3.6GB | ❌ | LOW |
| `audit_logs` | ~500B | 1M/day = 500MB | 182GB | ✅ Daily (migration 001) | LOW |

**CRITICAL RISK: `agent_executions` tracks 500K invocations/day at 100K users, growing 182GB/year. It has no partitioning and no retention policy.** This is the #1 database growth risk.

**MAJOR RISK: `knowledge_chunks` embeddings are 3072d vectors. At 4 bytes/float × 3072 = 12KB per embedding, plus the chunk content. 1K chunks/day × 15KB = 15MB/day = 5.5GB/year. Manageable but needs monitoring.**

### Recommended Partitioning

| Table | Partition Key | Retention |
|-------|--------------|-----------|
| `agent_executions` | RANGE (created_at) monthly | 90 days hot |
| `knowledge_chunks` | HASH (user_id) 64 partitions | Indefinite |
| `match_results` | RANGE (computed_at) monthly | 180 days hot |
| `semantic_memories` | HASH (user_id) 64 partitions | Indefinite |

---

## 8. LangGraph Design — B+

**Finding: The graph is well-structured for MVP.** Single Supervisor with tools. The node responsibilities are clear and testable. Checkpointing enables multi-turn conversations in V1.

### Noted
- PostgresSaver setup is manual (requires running `setup()` once). Document this.
- No graph-level retry policies on LLM nodes (acceptable for MVP, should add in V1)
- Recursion limit of 15 is reasonable but not documented in architecture docs

---

## 9. API Consistency — B+

### Endpoint Inventory

| Module | Endpoints | Version Prefix | Auth | Pagination | Response Envelope |
|--------|----------|---------------|------|------------|-------------------|
| Auth | 10 | /v1/auth/* | Mixed | ❌ | ✅ |
| Profile | 14 | /v1/profile/*, /v1/resumes/* | ✅ | ✅ | ✅ |
| Jobs | 8 | /v1/jobs/*, /v1/companies/* | ✅ | ✅ | ✅ |
| Matching | 6 | /v1/match/* | ✅ | ✅ | ✅ |
| Agent | 5 | /v1/agent/* | ✅ | ✅ | ✅ |
| Knowledge | 4 | /v1/knowledge/* | ✅ | ❌ | ✅ |

**Finding: 98% consistent.** Two minor inconsistencies:
- Knowledge document list has no cursor pagination
- Agent execution list pagination uses offset, not cursor

---

## 10. Security Posture — B+

### Defense Layers — All Present

| Layer | Status | Notes |
|-------|--------|-------|
| Authentication | ✅ | JWT RS256 + refresh token rotation + anti-theft detection |
| Authorization | ✅ | User-scoped queries on all endpoints. `get_current_user` on protected routes |
| Input validation | ✅ | Pydantic strict mode on all request schemas |
| Prompt injection | ✅ | Pattern detection in guardrail node. XML tag wrapping |
| Rate limiting | ✅ | Redis sliding window, tier-based |
| File upload | ✅ | Type allowlist, size limit, ClamAV scan |
| CORS | ✅ | Explicit origins, no wildcard |
| Data isolation | ✅ | tenant_id + user_id on all queries |
| Error safety | ✅ | Internal errors return safe messages, no stack traces |
| GDPR | ✅ | Data export + account deletion APIs |

---

## 11. Scalability — B

### Current Architecture Scalability

| Component | 1K Users | 10K Users | 100K Users | Bottleneck |
|-----------|----------|-----------|------------|------------|
| FastAPI API | ✅ | ✅ | ✅ | Connection pool (configurable) |
| PostgreSQL | ✅ | ✅ | ⚠️ | Unpartitioned tables (see §7) |
| pgvector HNSW | ✅ | ✅ | ✅ | Index size grows linearly |
| Redis | ✅ | ✅ | ✅ | Single node handles this load |
| Celery workers | ✅ | ✅ | ⚠️ | Consolidation: 5.5h sequential for 10K |
| DeepSeek API | ✅ | ✅ | ⚠️ | Rate limits, cost at scale |

**Finding: The modular monolith scales to 10K users comfortably. At 100K, table partitioning and Celery worker scaling are required.**

---

## 12. Cost Optimization — B

### LLM Cost Profile (100K Users, Daily)

| Operation | Calls/User/Day | Total Calls/Day | Tokens/Call | Cost/Day |
|-----------|---------------|-----------------|-------------|----------|
| Intent routing | 5 | 500K | 100 | $0.50 |
| Task planning | 3 | 300K | 300 | $0.90 |
| Result synthesis | 3 | 300K | 200 | $0.60 |
| Memory consolidation | 0.1 | 10K | 2000 | $2.00 |
| Match explanation | 2 | 200K | 300 | $0.60 |
| RAG re-ranking | 3 | 300K | 200 | $0.60 |
| Embedding generation | 0.5 | 50K | N/A (API) | $0.25 |
| **TOTAL** | | | | **~$5.45** |

At $5.45/day for 100K users = ~$0.00005/user/day. Well within budget.

### Optimization Opportunities
- Keyword pre-filter for intent routing (saves ~40% of intent routing costs)
- Semantic cache for LLM explanations (identical profile+job → reuse)
- Batch consolidation (10 users per LLM call → 10× cost reduction)

---

## Issue Summary

### Critical Risks

| ID | Risk | Impact | Mitigation |
|----|------|--------|------------|
| **CRIT-R1** | `agent_executions` unpartitioned — 182GB/year growth | DB performance degradation, backup time | Partition by month. Add 90-day retention. Sprint 7 migration. |
| **CRIT-R2** | No Celery task monitoring | Consolidation failures undetected | Add Celery task success/failure metrics to health endpoint. |

### Major Risks

| ID | Risk | Impact | Mitigation |
|----|------|--------|------------|
| MAJ-R1 | `MemoryRetrievalService` dead class | Developer confusion. Divergent code paths. | Integrate into context_builder or remove. |
| MAJ-R2 | No database backup verification | Backup corruption undetected | Add weekly restore test to CI. |
| MAJ-R3 | Consolidation processes users sequentially | 5.5h for 10K users | Add batch LLM processing (V1). |
| MAJ-R4 | `knowledge_chunks` growth unmonitored | Yearly 5.5GB at 100K users | Add size monitoring alert. Partition at 10M rows. |

### Minor Risks

| ID | Risk |
|----|------|
| MIN-R1 | `ImportanceCalculator` and `ImportanceScore.decay()` are dead code |
| MIN-R2 | `SqlEpisodicRepository.backfill_embeddings()` has no caller |
| MIN-R3 | Knowledge document list has no pagination |
| MIN-R4 | Agent execution list uses offset pagination instead of cursor |
| MIN-R5 | No graph-level retry policies on LLM nodes |
| MIN-R6 | PostgresSaver setup is manual (not automated in migration/startup) |
| MIN-R7 | No query rewriting in RAG retrieval |
| MIN-R8 | No retrieval quality evaluation framework |
| MIN-R9 | Embedding model version not tracked per chunk |
| MIN-R10 | `match_results` table has no retention policy |

---

## Refactoring Roadmap

### Pre-Production (Must Do)

| Priority | Item | Effort |
|----------|------|--------|
| P0 | Partition `agent_executions` by month + 90-day retention | 2h |
| P0 | Add Celery task monitoring to health endpoint | 1h |

### Post-MVP / V1 (Should Do)

| Priority | Item | Effort |
|----------|------|--------|
| P1 | Integrate or remove `MemoryRetrievalService` | 30m |
| P1 | Wire `backfill_embeddings` Celery task | 30m |
| P1 | Add database backup verification test | 1h |
| P1 | Add graph-level retry policies on LLM nodes | 1h |
| P2 | Partition `knowledge_chunks` and `match_results` | 2h |
| P2 | Batch LLM consolidation (10 users/call) | 3h |
| P2 | Semantic cache for LLM explanations | 2h |
| P3 | Query rewriting for RAG retrieval | 2h |
| P3 | Retrieval evaluation framework | 4h |

---

## Final Assessment

### Architecture Health

| Dimension | Grade | Notes |
|-----------|-------|-------|
| Consistency | **A-** | Clean Architecture + DDD adhered to across all 8 sprints |
| Domain boundaries | **B+** | Clean separation. Minor DI bypasses in agent context. |
| Agent design | **B+** | Correct Supervisor + Tools pattern for MVP |
| Memory design | **B+** | End-to-end functional. Consolidation scales with batching. |
| RAG design | **B+** | Hybrid retrieval correct. Relevance scoring validated. |
| Database growth | **C** | Unpartitioned tables are the #1 risk. |
| API consistency | **B+** | 98% consistent. Two pagination gaps. |
| Security | **B+** | All layers present. Prompt injection defended. |
| Scalability | **B** | Modular monolith scales to 10K. Table partitioning needed for 100K. |
| Cost | **B** | LLM costs well within budget. Optimization opportunities identified. |

### Overall: B+ (Production-Ready with 2 Critical Fixes)

---

## ARCHITECTURE APPROVED FOR FEATURE EXPANSION

**Conditions:** Fix CRIT-R1 (agent_executions partitioning) and CRIT-R2 (Celery monitoring) before production deployment.

The system architecture is sound, consistent, and maintainable. The 8 sprints built a coherent modular monolith with clean domain boundaries. Remediations caught and fixed the recurring pattern of "infrastructure exists but data never populated" (embeddings in S7, tsvector in S8). No architectural redesign is needed. Feature expansion can proceed on this foundation.

> *"Eight sprints. One architecture. Clean boundaries. Consistent patterns. The foundation is solid. Build on it."*

**End of Architecture Audit**
