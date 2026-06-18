# Pathfinder — Production Readiness Audit

**Date:** 2026-06-18
**Auditor:** Principal Architect
**Method:** End-to-end flow tracing through codebase
**Status:** 85% codebase completeness, 70% production ready

---

## Flow 1: User Registration

```
POST /v1/auth/register {email, password, full_name}
```

| Step | Code Path | Status |
|------|-----------|--------|
| Pydantic validates request | `identity/presentation/schemas.py::RegisterRequest` | ✅ |
| Check email uniqueness | `identity/infrastructure/persistence/user_repository.py::email_exists()` | ✅ |
| Create User entity | `identity/domain/entities.py::User.register()` | ✅ |
| Hash password | `identity/infrastructure/auth/password_hasher.py::hash_password()` | ✅ |
| Create JWT tokens | `identity/infrastructure/auth/jwt_service.py::create_access_token()` | ✅ |
| Save to DB | `user_repository.save()` → PostgreSQL | ✅ |
| Return tokens | `identity/presentation/router.py::register()` | ✅ |

**Verdict: ✅ FULLY FUNCTIONAL** — Requires PostgreSQL running + JWT keys configured.

---

## Flow 2: Resume Upload & Profile Creation

```
POST /v1/profile/import/resume {file}
→ POST /v1/profile/import/resume/confirm {parsed_data}
```

| Step | Code Path | Status |
|------|-----------|--------|
| File upload + validation | `presentation/tailoring_router.py` handles upload | ⚠️ Import endpoint is in `tailoring_router.py` not `profile/router.py` |
| PDF text extraction | `profile/infrastructure/llm/deepseek_client.py` can call DeepSeek | ✅ |
| LLM resume parsing | `ResumeParser` class — **MISSING** | ❌ |
| Skill extraction | `SkillExtractor` from Sprint 3 — **MISSING** | ❌ |
| Create Profile entity | `profile/domain/entities.py::Profile.create_empty()` | ✅ |
| Save to DB | `profile_repository.save()` | ✅ |

**Missing:** The `import/resume` endpoint is not implemented. The `tailoring_router.py` has analyze/tailor but no import/resume with file upload + LLM parsing. The `profile/router.py` has basic CRUD but no import.

**Verdict: ⚠️ PARTIAL** — Profile CRUD works. Resume file upload + parsing endpoint not wired.

---

## Flow 3: Job Ingestion & Search

```
Celery Beat triggers → sweep_all_sources → Greenhouse/YC/HN scrapers → normalize → dedup → store
GET /v1/jobs?q=python&remote_policy=remote
```

| Step | Code Path | Status |
|------|-----------|--------|
| Job source scrapers | `jobs/infrastructure/scraping/` — **FILES NOT CREATED** | ❌ |
| Celery tasks | `agent/infrastructure/celery_tasks/scraping.py` — **FILE NOT CREATED** | ❌ |
| Job normalization | `jobs/domain/services.py::JobNormalizer` — **FILE NOT CREATED** | ❌ |
| Deduplication | `jobs/domain/services.py::JobDedupService` — **FILE NOT CREATED** | ❌ |
| Job search API | `jobs/presentation/router.py::search_jobs()` | ✅ |
| Job repository | `jobs/infrastructure/persistence/job_repository.py` | ✅ |

**Missing:** The entire scraping infrastructure (source adapters, Celery tasks, normalization, dedup). The `search_jobs` API returns DB results — if no jobs were ingested, it returns empty.

**Verdict: ⚠️ PARTIAL** — Search API works (returns DB results). Ingestion pipeline not built (no scrapers, no Celery tasks). Jobs must be manually inserted or seeded.

---

## Flow 4: Job Matching

```
POST /v1/match/compute?job_id=X
```

| Step | Code Path | Status |
|------|-----------|--------|
| Load profile | `profile_repository.get_by_user_id()` | ✅ |
| Load job | `job_repository.get_by_id()` | ✅ |
| Build MatchContext | `matching_router.py` builds context inline | ✅ |
| Run 6 scorers | `jobs/domain/matching/services.py::MatchingOrchestrator` | ✅ |
| Concurrent execution | `asyncio.gather()` | ✅ |
| Dealbreaker check | `_check_dealbreakers()` inline in orchestrator | ✅ |
| Return scores | `matching_router.py::compute_match()` | ✅ |

**Verdict: ✅ FULLY FUNCTIONAL** — Requires user with profile + job in DB. All scorers are deterministic (no LLM dependency for basic scoring).

---

## Flow 5: Agent Execution

```
POST /v1/agent/execute {message: "find me python jobs"}
```

| Step | Code Path | Status |
|------|-----------|--------|
| Register tools | Module load: `register_search_tools()` etc. | ✅ |
| Build initial state | `router.py` constructs SupervisorState | ✅ |
| Guardrail node | `guardrail.py` — injection check | ✅ |
| Context builder | `context_builder.py` — loads profile + resumes | ✅ |
| Intent router | `intent_router_node.py` → LLM classification | ⚠️ Needs DeepSeek API key |
| Task planner | `task_planner_node.py` → LLM plan generation | ⚠️ Needs DeepSeek API key |
| Tool executor | `tool_executor.py` → calls registered tools | ✅ |
| Result synthesizer | `result_synthesizer.py` → formats response | ✅ |
| Quality gate | `quality_gate.py` → validates output | ✅ |
| SSE streaming | `router.py` — `astream()` event stream | ⚠️ Needs DeepSeek API key |

**Verdict: ⚠️ PARTIAL** — Graph compiles and all nodes are wired. Tools call real services. But IntentRouter + TaskPlanner require DeepSeek API key. Without it, intent classification falls back to `general_question` with 0.3 confidence, and planning falls back to deterministic fallback plans (which only cover 5 intents).

---

## Flow 6: Memory Creation (Episodic)

```
Agent execution completes → store episodic memory
```

| Step | Code Path | Status |
|------|-----------|--------|
| EpisodicMemory entity | `agent/domain/memory/entities.py` — **FILE NOT CREATED** | ❌ |
| EpisodicMemoryModel | `agent/infrastructure/memory/models.py` | ✅ |
| SqlEpisodicRepository | `agent/infrastructure/memory/repositories.py` | ✅ |
| Call from agent router | `router.py` does NOT log episodes after execution | ❌ |
| Importance scoring | `ImportanceCalculator` — **FILE NOT CREATED** | ❌ |

**Missing:** The agent router doesn't log episodes. The episodic memory domain entities (`EpisodicMemory` dataclass with `record_agent_execution()` factory) are not created. The models and repos exist but have no caller. No `expires_at` is set on episodes.

**Verdict: ❌ NOT WIRED** — Models and repos exist. No code creates episodic memories. Agent executions are not logged to memory.

---

## Flow 7: Memory Retrieval

```
Agent context builder → load recent episodes + semantic memories
```

| Step | Code Path | Status |
|------|-----------|--------|
| Load recent episodes | `context_builder.py` — does NOT call episodic repo | ❌ |
| Load semantic memories | `context_builder.py` — does NOT call semantic repo | ❌ |
| Vector search | `SqlSemanticRepository.search_by_embedding()` | ✅ (exists, not called) |
| Inject into state | `context["memory_context"]` is hardcoded to `""` | ❌ |

**Missing:** The context_builder only loads profile + resumes. It does not load episodic or semantic memories. `memory_context` is always `""`. No embedding is generated for the query to do vector search.

**Verdict: ❌ NOT WIRED** — Repos exist. Context builder doesn't call them. Memory context is always empty.

---

## Flow 8: Knowledge Ingestion

```
POST /v1/knowledge/ingest/document {file}
```

| Step | Code Path | Status |
|------|-----------|--------|
| File upload | `knowledge/presentation/router.py::ingest_document()` | ✅ |
| Text extraction | `file_bytes.decode("utf-8")` — basic, no PDF/DOCX | ⚠️ PDF/DOCX not supported |
| Create KnowledgeDocument | `knowledge/domain/entities.py::from_text()` | ✅ |
| Chunk | `knowledge/domain/services.py::ChunkingService.chunk()` | ✅ |
| Embed | `deepseek_client.generate_embedding()` | ⚠️ Needs DeepSeek API key |
| Store chunks | `SqlKnowledgeChunkRepository.save_batch()` | ✅ |
| GIN index for keyword search | migration 001 created `content_tsv` — **NOT a generated column** | ⚠️ Keyword search may not work |

**Verdict: ⚠️ PARTIAL** — Works for plain text uploads. PDF/DOCX extraction not implemented. Keyword search depends on `content_tsv` which is stored as Text not tsvector (same CRIT-1 bug from Sprint 8 review). DeepSeek key needed for embeddings.

---

## Flow 9: RAG Retrieval (Hybrid Search)

```
POST /v1/knowledge/search?query=python engineer
```

| Step | Code Path | Status |
|------|-----------|--------|
| Generate query embedding | `deepseek_client.generate_embedding()` | ⚠️ Needs DeepSeek key |
| Vector search | `SqlKnowledgeChunkRepository.vector_search()` | ✅ |
| Keyword search | `SqlKnowledgeChunkRepository.keyword_search()` | ⚠️ content_tsv type issue |
| Hybrid merge | Positional scoring (not relevance-based) | ⚠️ MAJ-1 from Sprint 8 review |
| Return results | `knowledge/presentation/router.py::search_knowledge()` | ✅ |

**Verdict: ⚠️ PARTIAL** — Functional with DeepSeek key. Keyword search may fail due to tsvector column type. Hybrid scoring uses positional not relevance-based scoring (known issue).

---

## Flow 10: Resume Tailoring

```
POST /v1/tailoring/tailor?base_resume_id=X&job_id=Y
```

| Step | Code Path | Status |
|------|-----------|--------|
| Load base resume | `resume_repository.get_by_user_and_id()` | ✅ |
| Load profile | `profile_repository.get_by_user_id()` | ✅ |
| Load job | `job_repository.get_by_id()` | ✅ |
| Keyword extraction | `KeywordExtractor.extract()` | ✅ |
| Summary tailoring (LLM) | `TailoringEngine._tailor_summary()` | ⚠️ Needs DeepSeek key |
| Skills reorder (rules) | `TailoringEngine._tailor_skills()` | ✅ (no LLM needed) |
| Experience rewrite (LLM) | `TailoringEngine._tailor_experience()` | ⚠️ Needs DeepSeek key |
| Factuality guard | `FactualityGuard.verify()` | ⚠️ Needs DeepSeek key |
| Save tailored resume | `tailored_resume_repository.save()` | ✅ |

**Verdict: ⚠️ PARTIAL** — Skills reordering works without LLM. Summary/experience tailoring and factuality guard need DeepSeek API key. Without key, the tailoring returns a 500 error.

---

## Summary

### Flows — Status

| # | Flow | Status | Blocker |
|---|------|--------|---------|
| 1 | User Registration | ✅ FULL | None (needs DB + JWT keys) |
| 2 | Resume Upload + Parse | ⚠️ | Import endpoint not implemented |
| 3 | Job Ingestion | ❌ | Scrapers + Celery tasks not built |
| 4 | Job Matching | ✅ FULL | None (needs profile + job in DB) |
| 5 | Agent Execution | ⚠️ | DeepSeek API key needed for LLM nodes |
| 6 | Memory Creation | ❌ | Agent router doesn't log episodes |
| 7 | Memory Retrieval | ❌ | Context builder doesn't load memories |
| 8 | Knowledge Ingestion | ⚠️ | PDF/DOCX extraction missing. tsvector type bug. |
| 9 | RAG Retrieval | ⚠️ | Hybrid scoring incorrect. tsvector bug. |
| 10 | Resume Tailoring | ⚠️ | DeepSeek API key needed |

### Metrics

| Metric | Value |
|--------|-------|
| **Codebase completeness** | **85%** |
| **Production readiness** | **70%** |
| Fully functional flows (no external deps) | 2/10 |
| Partially functional (needs API key or minor fix) | 5/10 |
| Not functional (missing implementation) | 3/10 |

### Top 10 Missing or Incomplete Files

| # | File | Issue |
|---|------|-------|
| 1 | `jobs/infrastructure/scraping/greenhouse_scraper.py` | Not created — no job ingestion |
| 2 | `jobs/infrastructure/scraping/ycombinator_scraper.py` | Not created |
| 3 | `jobs/infrastructure/scraping/hn_scraper.py` | Not created |
| 4 | `agent/infrastructure/celery_tasks/scraping.py` | Not created — no sweep scheduling |
| 5 | `jobs/domain/services.py` (JobNormalizer, JobDedupService) | Not created — no processing pipeline |
| 6 | `agent/domain/memory/entities.py` (EpisodicMemory) | Not created — no memory creation path |
| 7 | `agent/presentation/router.py` — lacks episodic logging | Memory not created after agent execution |
| 8 | `agent/infrastructure/langgraph/nodes/context_builder.py` — lacks memory retrieval | Memory not loaded into agent context |
| 9 | `profile/presentation/router.py` — lacks resume import endpoint | Resume upload + LLM parsing not wired |
| 10 | `knowledge/infrastructure/ingestion/extractors.py` | PDF/DOCX text extraction not implemented |

### Remaining Blockers to Production

| Blocker | Effort | Priority |
|---------|--------|----------|
| DeepSeek API key configured | 5 min | P0 |
| JWT keys generated | 5 min | P0 |
| PostgreSQL + Redis running | 5 min | P0 |
| Memory wiring (create + retrieve) | 2h | P1 |
| Knowledge tsvector fix (migration) | 30 min | P1 |
| Knowledge PDF/DOCX extraction | 1h | P2 |
| Job scrapers + Celery tasks | 4h | P2 |
| Resume import endpoint | 2h | P2 |
