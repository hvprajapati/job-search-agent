# Pathfinder — Engineering Achievements

## By the Numbers

| Metric | Value |
|--------|-------|
| **Python source files** | 98 |
| **Lines of code** | ~12,000 |
| **Bounded contexts** | 9 (identity, profile, jobs, matching, tracking, agent, memory, knowledge, shared) |
| **API endpoints** | 36 (100% functional, 0 stubs) |
| **LangGraph nodes** | 7 (guardrail, context_builder, intent_router, task_planner, tool_executor, result_synthesizer, quality_gate) |
| **Agent tools** | 7 (search_jobs, get_job_detail, compute_match, get_recommendations, get_profile, get_resumes, tailor_resume) |
| **Agent intents** | 11 (with deterministic fallback plans for all) |
| **Matching dimensions** | 6 (skills, experience, education, location, preference, culture) |
| **Memory types** | 3 (episodic, semantic, procedural) |
| **Job sources** | 3 (Greenhouse 34 companies, Y Combinator, Hacker News) |
| **SQLAlchemy models** | 8 (across all bounded contexts) |
| **Repository implementations** | 10 |
| **Alembic migrations** | 3 |
| **Tests** | 84 (30 unit, 54 integration/E2E) |
| **Celery tasks** | 4 (sweep_all_sources, mark_stale_jobs, cleanup_expired_episodes, consolidate_memories) |
| **Database tables** | 25+ |
| **HNSW indexes** | 4 (jobs, semantic_memories, episodic_memories, knowledge_chunks) |
| **GIN indexes** | 2 (job_postings tsvector, knowledge_chunks tsvector) |
| **Middleware layers** | 5 (auth, rate_limit, request_id, security_headers, cors) |
| **Prometheus metrics** | 12 (counters, histograms, gauges) |

## Technical Depth

| Capability | Implementation |
|-----------|---------------|
| **Agent Framework** | LangGraph StateGraph with PostgresSaver checkpointing |
| **LLM Resilience** | Circuit breaker (5 failures → open), deterministic fallbacks, graceful degradation |
| **Vector Search** | pgvector HNSW (cosine distance, m=16, ef_construction=200) |
| **Full-Text Search** | PostgreSQL tsvector with GIN index, generated columns |
| **Hybrid Retrieval** | Vector + keyword weighted fusion (configurable 0.7/0.3 split) |
| **Concurrent Execution** | asyncio.gather for matching scorers, knowledge retrieval |
| **Memory Consolidation** | Daily LLM-driven: episodes → structured facts with evidence tracking |
| **Factuality Verification** | Post-generation LLM guard with JSON schema validation |
| **Token Budgeting** | tiktoken counting, 2000 memory + 1500 knowledge token budgets |
| **State Persistence** | LangGraph checkpoint after every node, survives process restart |
| **Error Recovery** | Domain exception hierarchy → HTTP status mapping, PII-safe messages |

## Production Hardening

| Feature | Implementation |
|---------|---------------|
| **Authentication** | JWT RS256, 15min access + 7d refresh rotation, token blacklisting |
| **Rate Limiting** | Redis sliding window, tier-based (100/300/1000 req/min) |
| **Security Headers** | HSTS, CSP, X-Frame-Options, X-Content-Type-Options |
| **Prompt Injection Defense** | Pattern detection + XML tag wrapping |
| **Request Tracing** | UUIDv7 per request, propagated through all log lines |
| **Structured Logging** | structlog JSON (prod) / console (dev), PII redaction |
| **Health Checks** | /live, /ready (DB+Redis+LLM), /health (detailed) |
| **Metrics** | 12 Prometheus metrics, Grafana dashboard ready |
| **Error Tracking** | Sentry integration with PII stripping |
| **Migrations** | Alembic async, backward-compatible, CONCURRENTLY indexes |
| **Backup** | pg_dump daily, WAL archiving, monthly restore verification |

## Solo Engineering Metrics

| Metric | Value |
|--------|-------|
| **Build duration** | 12 weeks |
| **Git commits** | 7+ |
| **Architecture documents** | 10+ (PRD, API, architecture, deployment, monitoring, backup) |
| **Design decisions documented** | 50+ (interview guide) |
| **Portfolio assets** | 6 (project summary, resume descriptions, interview guide, recruiter pitch, system diagrams, achievements) |
