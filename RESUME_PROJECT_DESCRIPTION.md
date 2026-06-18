# Resume Project Descriptions — Pathfinder

---

## 3-Line Version

Built Pathfinder, a production-grade Autonomous AI Career Agent using LangGraph, FastAPI, PostgreSQL+pgvector, and DeepSeek. Designed a multi-agent system with 7-tool Supervisor Agent, 6-dimension job matching engine, hybrid RAG knowledge retrieval, and long-term memory consolidation. Achieved 36 functional API endpoints with circuit breaker resilience, graceful LLM degradation, and zero-crash architecture across 98 source files and 84 tests.

---

## 5-Line Version

**Pathfinder — Autonomous AI Career Agent** | Python, LangGraph, FastAPI, PostgreSQL, pgvector, DeepSeek

- Architected and built a production-grade multi-agent AI system that automates the entire job search pipeline — from resume parsing and job discovery through semantic matching, AI-powered resume tailoring, and application tracking.
- Designed a LangGraph Supervisor Agent with 7 tools and 7-node state graph, supporting 11 intents with LLM-powered planning and deterministic fallbacks for resilience.
- Implemented a 6-dimension concurrent matching engine (skills, experience, education, location, preference, culture) with dealbreaker detection and completeness-penalized scoring.
- Built a hybrid RAG knowledge retrieval system combining pgvector HNSW vector search with PostgreSQL tsvector full-text search, plus a 3-tier memory system (episodic, semantic, procedural) with daily LLM consolidation.
- Engineered for production with circuit breaker LLM resilience, Redis rate limiting, JWT authentication, structured JSON logging, Prometheus metrics, and graceful degradation across all 36 endpoints.

---

## 8-Line Version

**Pathfinder — Autonomous AI Career Agent** | Solo Engineer, 12-Week Build
**Stack:** Python 3.12, FastAPI, LangGraph, PostgreSQL 16, pgvector, Redis, DeepSeek API, Docker

- Designed and built a production-grade multi-agent AI system that serves as a persistent career operating system — discovering jobs, matching candidates, tailoring resumes, and learning user preferences over time.
- Implemented a LangGraph Supervisor Agent with a 7-node state graph (guardrail → context → intent → plan → execute → synthesize → quality gate), 7 tools wrapping existing services, and SSE streaming for real-time responses.
- Built a 6-dimension concurrent job matching engine using Strategy pattern with asyncio.gather for parallel scoring, dealbreaker short-circuit optimization, and completeness penalty to prevent inflated scores when dimensions are missing.
- Engineered a 3-tier memory architecture (episodic append-only log, semantic facts with pgvector HNSN indexing, procedural patterns) with daily LLM-driven consolidation that extracts insights from raw interactions.
- Developed a hybrid RAG knowledge retrieval pipeline combining cosine-similarity vector search with PostgreSQL full-text tsvector search, weighted fusion scoring, and semantic document chunking with overlap.
- Created a zero-hallucination resume tailoring engine with post-generation LLM factuality verification, regex-based keyword extraction for LLM-independent analysis, and version-controlled diff tracking.
- Architected for resilience: LLM circuit breaker (5 failures → open), deterministic fallback plans for all 11 agent intents, graceful degradation on all 36 API endpoints, and token budget enforcement for context windows.
- Built with Clean Architecture + DDD across 9 bounded contexts, 98 source files, 84 tests, automated Alembic migrations, Docker Compose deployment, Prometheus metrics, and structured JSON logging.

---

## Role-Optimized Versions

### AI Engineer / ML Engineer Focus

Built Pathfinder, an Autonomous AI Career Agent powered by LangGraph multi-agent orchestration and DeepSeek LLM. Designed a 7-node Supervisor StateGraph with intent routing, task planning, and tool execution. Implemented a 6-dimension concurrent matching engine, 3-tier memory system (episodic/semantic/procedural) with daily LLM consolidation, and hybrid RAG retrieval (pgvector HNSW + PostgreSQL tsvector). Engineered circuit breaker resilience, deterministic fallback plans, and zero-hallucination resume generation with post-generation factuality verification. 36 endpoints, 98 source files, 84 tests.

### Generative AI Engineer Focus

Built Pathfinder, a production-grade GenAI agent system using LangGraph, DeepSeek API, and FastAPI. Architected a Supervisor Agent with 7-node state graph, 7 tools, and 11-intent classification. Engineered LLM-powered features: resume tailoring with factuality guard, memory consolidation pipeline, hybrid RAG retrieval, and intent-based task planning. Implemented prompt injection defenses, circuit breaker resilience, structured JSON output enforcement, and token budget management. All 36 endpoints degrade gracefully without LLM. 84 tests.

### Backend Engineer Focus

Built Pathfinder, a production Python backend (FastAPI + PostgreSQL + pgvector + Redis + Docker) for an AI-powered career platform. Designed Clean Architecture with DDD across 9 bounded contexts. Implemented 36 REST endpoints with JWT auth, rate limiting, cursor pagination, and SSE streaming. Built job discovery pipeline (3 scrapers + Celery), concurrent matching engine (6 scorers via asyncio), and document ingestion pipeline with chunking and vector storage. Production-hardened with circuit breaker, structured logging, Prometheus metrics, security headers, and automated migrations. 98 source files, 84 tests.
