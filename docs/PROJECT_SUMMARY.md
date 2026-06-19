# Pathfinder — Autonomous AI Career Agent

## What Pathfinder Is

Pathfinder is a **production-grade Autonomous AI Career Agent** that helps software engineers, data engineers, AI/ML engineers, and career changers navigate their entire job search — from discovery through offer acceptance. It is not a chatbot. It is a persistent, proactive multi-agent AI system with long-term memory, knowledge retrieval, and autonomous decision-making.

## Problem Solved

Job seekers spend 11–25 hours/week across 15+ disconnected tools. Employers deploy AI-powered ATS screening and recruiter automation. Job seekers are armed with a PDF and hope. **Pathfinder closes this asymmetry** — giving candidates AI-powered discovery, matching, tailoring, tracking, and coaching that operates 24/7 on their behalf.

## Architecture Overview

**Modular Monolith** — FastAPI + PostgreSQL + pgvector + Redis + Docker. Clean Architecture with Domain-Driven Design across 9 bounded contexts. LangGraph Supervisor Agent with 7 tools orchestrates multi-step workflows. 36 API endpoints with graceful degradation when the LLM is unavailable.

## Key Technical Challenges Solved

| Challenge | Solution |
|-----------|----------|
| **Zero-hallucination resume generation** | Post-generation factuality guard with LLM verification. Every claim checked against profile. Fail-open on guard failure. |
| **LLM dependency resilience** | Circuit breaker (5 failures → open, 30s recovery). Deterministic fallback plans for all 11 agent intents. Regex-based keyword extraction without LLM. |
| **Hybrid search at scale** | pgvector HNSW (cosine similarity) + PostgreSQL tsvector GIN (full-text) with weighted fusion. Keyword path works without embeddings. |
| **Multi-dimensional matching** | 6 concurrent scorers (skills, experience, education, location, preference, culture) via asyncio.gather. Dealbreaker short-circuit before scoring. Completeness penalty prevents inflated scores. |
| **Stateful agent with persistence** | LangGraph PostgresSaver checkpoints after every graph node. State survives process restart. Token budget enforcement (2,000 memory + 1,500 knowledge tokens). |
| **Long-term memory consolidation** | Daily Celery job: unconsolidated episodes → LLM extraction → semantic memory UPSERT with evidence tracking and confidence scoring. |
| **Production observability** | Prometheus metrics (12 counters/histograms/gauges). structlog JSON logging. Sentry error tracking. Request ID propagation (UUIDv7). |

## Scale Assumptions

- **100K registered users**, 10K daily active
- 500K agent invocations/day, 500K episodic memories/day
- 100K job listings indexed, 10K matches computed/hour
- Single VM deployment (Docker Compose) at MVP. Managed PostgreSQL + Redis at scale.

## AI Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Agent Orchestration** | LangGraph StateGraph (7 nodes) | Intent routing, task planning, tool execution, quality gating |
| **Intent Classification** | DeepSeek LLM (with keyword pre-filter) | 11 intent taxonomy with confidence scoring |
| **Task Planning** | DeepSeek LLM (with deterministic fallback) | Multi-step execution plan generation |
| **Matching Engine** | 6 deterministic scorers + concurrent execution | Skills, experience, education, location, preference, culture |
| **Resume Tailoring** | DeepSeek LLM + Factuality Guard | Summary rewrite, skills reorder, experience optimization |
| **Memory Consolidation** | DeepSeek LLM (daily batch) | Episode → semantic fact extraction |
| **Knowledge Retrieval** | pgvector HNSW + PostgreSQL tsvector | Hybrid vector+keyword search with re-ranking |
| **Embedding Generation** | DeepSeek Embedding API (3072d) | Document chunks, semantic memories, job descriptions |

## Why Production-Grade

- **Zero crash endpoints** — all 36 endpoints return valid responses with graceful degradation
- **Circuit breaker** — 5 consecutive LLM failures → circuit opens → deterministic fallback
- **Structured logging** — JSON logs with request ID propagation for observability
- **Rate limiting** — Redis sliding window, tier-based (100/300/1000 req/min)
- **Security** — JWT RS256 + refresh rotation + token blacklisting + prompt injection detection
- **Database** — HNSW indexes, GIN tsvector indexes, daily partitioning, automated migrations
- **Testing** — 84 tests (30 unit, 54 integration/E2E with DB skip)
- **Deployment** — Single `docker compose up`, health checks, Prometheus metrics
- **Documentation** — API spec, architecture docs, deployment guide, backup/recovery runbook
