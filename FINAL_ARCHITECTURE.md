# Pathfinder — Final Architecture

**Document Version:** 2.0 — SINGLE SOURCE OF TRUTH
**Date:** 2026-06-18
**Status:** Approved — Supersedes All Previous Architecture Documents
**Author:** Principal Engineer
**Classification:** Confidential — Internal

---

## Document Authority

**This document is the single source of truth for all architecture decisions.**

If any previous document (PRD.md, ARCHITECTURE.md, AGENTS.md, MEMORY.md, DATABASE.md, API.md, CODEBASE.md, IMPLEMENTATION.md) conflicts with this document, **this document wins**. Previous documents remain as reference for detailed design rationale but carry no authority on architecture decisions.

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Deployment Architecture](#2-deployment-architecture)
3. [Agent Architecture](#3-agent-architecture)
4. [Memory Architecture](#4-memory-architecture)
5. [Database Architecture](#5-database-architecture)
6. [API Architecture](#6-api-architecture)
7. [Folder Structure](#7-folder-structure)
8. [Security Architecture](#8-security-architecture)
9. [Observability Architecture](#9-observability-architecture)
10. [Implementation Roadmap](#10-implementation-roadmap)
11. [Technology Stack — Final](#11-technology-stack--final)
12. [MVP / V1 / V2 Scope Matrix](#12-mvp--v1--v2-scope-matrix)

---

## 1. System Architecture

### 1.1 Architectural Style: Modular Monolith

**Decision:** A single deployable FastAPI process containing all bounded contexts as Python modules. No microservices. No service mesh. No inter-service network calls.

**Why:** A solo developer cannot operate 12 microservices. The modular monolith enforces the same domain boundaries via import rules, not network boundaries. Extraction to independent services is a V2 concern when a team exists.

**Boundary enforcement:** Each module exports a public API via `__init__.py`. Cross-module imports only through those public surfaces. Enforced by `import-linter` in CI.

### 1.2 System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PATHFINDER SYSTEM                                   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        EXTERNAL USERS                                  │   │
│  │  Browser → Cloudflare DNS → VM Public IP (HTTPS, port 443 → 8000)     │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                            │
│  ┌──────────────────────────────┴───────────────────────────────────────┐   │
│  │                    SINGLE VIRTUAL MACHINE                              │   │
│  │                    (8 vCPU, 32 GB RAM, 200 GB SSD)                     │   │
│  │                                                                        │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │   │
│  │  │                     DOCKER COMPOSE                                │  │   │
│  │  │                                                                   │  │   │
│  │  │  ┌──────────────────────────────────────────────────────────┐    │  │   │
│  │  │  │  fastapi (1 container)                                     │    │  │   │
│  │  │  │  - REST API (FastAPI + Uvicorn, 4 workers)                │    │  │   │
│  │  │  │  - Agent Orchestrator (LangGraph, in-process)              │    │  │   │
│  │  │  │  - All business logic (6 modules, in-process)              │    │  │   │
│  │  │  │  - SSE streaming for agent responses                       │    │  │   │
│  │  │  │  - WebSocket for real-time notifications                   │    │  │   │
│  │  │  └──────────────────────────────────────────────────────────┘    │  │   │
│  │  │                                                                   │  │   │
│  │  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐        │  │   │
│  │  │  │ celery-       │  │ celery-       │  │ celery-beat   │        │  │   │
│  │  │  │ worker-scrape │  │ worker-llm    │  │ (scheduler)   │        │  │   │
│  │  │  │ (1 worker)    │  │ (3 workers)   │  │ (1 process)   │        │  │   │
│  │  │  └───────────────┘  └───────────────┘  └───────────────┘        │  │   │
│  │  │                                                                   │  │   │
│  │  │  ┌───────────────────────────────┐  ┌───────────────────────┐    │  │   │
│  │  │  │ PostgreSQL 16 + pgvector      │  │ Redis 7 (single node)  │    │  │   │
│  │  │  │ (1 instance, shared)          │  │ Cache + Queue + PubSub │    │  │   │
│  │  │  └───────────────────────────────┘  └───────────────────────┘    │  │   │
│  │  │                                                                   │  │   │
│  │  │  ┌───────────────────────────────┐                               │  │   │
│  │  │  │ /data volume (local files)    │                               │  │   │
│  │  │  │ Resumes, PDFs, exports        │                               │  │   │
│  │  │  └───────────────────────────────┘                               │  │   │
│  │  └───────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     EXTERNAL SERVICES                                 │   │
│  │  DeepSeek API (primary LLM) · OpenAI API (fallback)                   │   │
│  │  Google OAuth · Resend (email) · Sentry (errors) · BetterStack (uptime)│  │
│  │  Greenhouse API · YC Jobs API · HN API (job sources)                   │  │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Internal Module Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FASTAPI PROCESS — INTERNAL STRUCTURE                       │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        PRESENTATION LAYER                              │   │
│  │  FastAPI routers, middleware, WebSocket handlers, SSE, dependencies    │   │
│  │  Calls: Application layer only                                        │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                            │
│  ┌──────────────────────────────┴───────────────────────────────────────┐   │
│  │                        APPLICATION LAYER                               │   │
│  │  Command/Query handlers, DTOs, use case orchestration                  │   │
│  │  Calls: Domain layer + Port interfaces                                │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                            │
│  ┌──────────────────────────────┴───────────────────────────────────────┐   │
│  │                          DOMAIN LAYER                                  │   │
│  │  Entities, Value Objects, Aggregates, Domain Services, Domain Events   │   │
│  │  Repository interfaces (abstract), Port interfaces (abstract)          │   │
│  │  ZERO external imports. Pure Python only.                              │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │ (interfaces implemented by...)            │
│  ┌──────────────────────────────┴───────────────────────────────────────┐   │
│  │                      INFRASTRUCTURE LAYER                              │   │
│  │  SQLAlchemy repos, Redis adapters, DeepSeek client, Celery tasks      │   │
│  │  LangGraph graphs, PDF renderer, Email sender, File storage           │   │
│  │  Implements: Domain interfaces                                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  6 MODULES (each with above 4 layers):                                       │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │identity│ │profile │ │  jobs  │ │tracking│ │ agent  │ │ shared │        │
│  │        │ │        │ │        │ │        │ │        │ │        │        │
│  │Auth    │ │Profile │ │JobPost │ │Appli-  │ │Super-  │ │Domain  │        │
│  │Users   │ │Resume  │ │Company │ │ cation │ │ visor  │ │prims   │        │
│  │Prefs   │ │CoverLtr│ │Match   │ │Intervw │ │Memory  │ │DB/Redis│        │
│  │        │ │DocGen  │ │Scrape  │ │FollowUp│ │Tools   │ │Config  │        │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Module Dependency Rules

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ALLOWED:                                                                    │
│  ────────                                                                    │
│  presentation → application           ✅  (calls handlers)                    │
│  application → domain                 ✅  (orchestrates domain logic)         │
│  infrastructure → domain              ✅  (implements domain interfaces)      │
│  domain → shared/domain               ✅  (uses shared primitives)            │
│  module_A → module_B (via interface)  ✅  (interface defined in module_B)    │
│                                                                              │
│  FORBIDDEN:                                                                  │
│  ──────────                                                                  │
│  domain → application                 ❌                                     │
│  domain → infrastructure              ❌                                     │
│  domain → presentation                ❌                                     │
│  application → infrastructure         ❌  (depends on Ports, never on infra) │
│  presentation → domain                ❌  (must go through application)      │
│  presentation → infrastructure        ❌                                     │
│  module_A → module_B (direct import)  ❌  (must use public API or interface) │
│                                                                              │
│  ENFORCEMENT: import-linter config in CI. Violations fail the build.         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Deployment Architecture

### 2.1 MVP — Single VM, Docker Compose

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ENVIRONMENT: Production VM                                                   │
│  ───────────────────────────                                                  │
│  Provider:     Hetzner CX42 / DigitalOcean Droplet / Railway Pro              │
│  Specs:        8 vCPU, 32 GB RAM, 200 GB NVMe SSD                             │
│  OS:           Ubuntu 24.04 LTS                                               │
│  Cost:         ~$60-120/month                                                 │
│                                                                              │
│  DEPLOYMENT:                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 1. git push main → GitHub Actions builds Docker image                 │   │
│  │ 2. SSH into VM → docker compose pull → docker compose up -d           │   │
│  │ 3. Alembic upgrade head (auto-runs in container entrypoint)            │   │
│  │ 4. Health check: GET /v1/health/ready → 200 = live                     │   │
│  │                                                                       │   │
│  │ ROLLBACK:                                                              │   │
│  │ 1. git revert → docker compose up -d (previous image tag)              │   │
│  │ 2. Alembic downgrade -1 (if migration was deployed separately)        │   │
│  │                                                                       │   │
│  │ BACKUPS:                                                               │   │
│  │ 1. pg_dump -Fc nightly → /data/backups/ (local)                       │   │
│  │ 2. rsync /data/backups/ → S3 (cross-region) nightly                   │   │
│  │ 3. WAL archiving to S3 (continuous)                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DOCKER COMPOSE SERVICES:                                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ fastapi:         uvicorn, 4 workers, port 8000                        │   │
│  │ celery-scrape:   1 worker, queue: scraping                             │   │
│  │ celery-llm:      3 workers, queue: llm_tasks                           │   │
│  │ celery-beat:     1 process, scheduler                                   │   │
│  │ postgres:        PostgreSQL 16 + pgvector, port 5432                    │   │
│  │ redis:           Redis 7, port 6379                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  NETWORK:                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Cloudflare DNS → VM IP → Nginx (inside VM, port 443→8000)             │   │
│  │ SSL: Cloudflare Origin CA (full encryption)                           │   │
│  │ Firewall: Only ports 443, 22 (from trusted IPs) open                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 V1 — Managed Platform

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  V1 DEPLOYMENT (Post-MVP, when team grows or user count > 50K)               │
│  ─────────────────────────────────────────────────────────────────────────── │
│  Platform:     Railway / Render / Fly.io (managed containers)                │
│  Database:     Managed PostgreSQL (Supabase / Railway / RDS)                 │
│  Cache:        Managed Redis (Upstash / Railway)                              │
│  Files:        S3 / R2 (object storage)                                       │
│  Monitoring:   Sentry + BetterStack + Grafana Cloud                          │
│                                                                              │
│  Key change: Offload DB/Redis/file management to providers.                  │
│  Still a single deployable. No microservices.                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 V2 — Kubernetes (Team Scale)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  V2 DEPLOYMENT (Team of 4+, user count > 500K)                               │
│  ───────────────────────────────────────────────────────────────────────     │
│  Platform:     GKE / EKS (managed Kubernetes)                                 │
│  Database:     Cloud SQL / RDS with read replicas                             │
│  Cache:        ElastiCache / Memorystore (managed Redis)                      │
│  Vector:       Dedicated pgvector read replica (if needed)                    │
│  CDN:          CloudFront / Cloud CDN for static + generated PDFs             │
│                                                                              │
│  Services extracted (only if independently scaled):                           │
│  - Agent Orchestrator (GPU nodes if on-prem models)                           │
│  - Job Discovery (independent scraping workers)                               │
│  - Notification Service (high-throughput push)                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent Architecture

### 3.1 MVP — Supervisor Agent with Tools

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MVP AGENT ARCHITECTURE                                     │
│                     ─────────────────────                                      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     POST /v1/agent/execute                             │   │
│  │                                                                       │   │
│  │  ┌────────────────────────────────────────────────────────────────┐  │   │
│  │  │                   SUPERVISOR AGENT                               │  │   │
│  │  │                   (LangGraph StateGraph)                         │  │   │
│  │  │                                                                  │  │   │
│  │  │  Nodes:                                                          │  │   │
│  │  │  1. Guardrail (safety, rate limit, tier check)                   │  │   │
│  │  │  2. Context Builder (load profile + prefs + recent history)      │  │   │
│  │  │  3. Intent Router (LLM: classify → intent)                       │  │   │
│  │  │  4. Task Planner (decompose → execution plan)                    │  │   │
│  │  │  5. Tool Executor (call tools in sequence/parallel)              │  │   │
│  │  │  6. Result Synthesizer (merge → format → explain)                │  │   │
│  │  │  7. Human Gate (pause if approval needed)                        │  │   │
│  │  │  8. Quality Gate (factuality check on generated content)          │  │   │
│  │  │                                                                  │  │   │
│  │  │  TOOLS (flat registry — called via function calling):            │  │   │
│  │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │  │   │
│  │  │  │ parse_resume │ │ search_jobs  │ │ compute_match│             │  │   │
│  │  │  └──────────────┘ └──────────────┘ └──────────────┘             │  │   │
│  │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │  │   │
│  │  │  │tailor_resume │ │generate_cover│ │ prep_intervw│             │  │   │
│  │  │  │              │ │   _letter    │ │              │             │  │   │
│  │  │  └──────────────┘ └──────────────┘ └──────────────┘             │  │   │
│  │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │  │   │
│  │  │  │apply_to_job  │ │generate_follow│ store_memory │             │  │   │
│  │  │  │              │ │    _up       │ │              │             │  │   │
│  │  │  └──────────────┘ └──────────────┘ └──────────────┘             │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  PARALLEL PATH: Direct endpoints (no agent overhead)                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ POST /v1/match                    → Direct matching (bypasses agent)  │   │
│  │ POST /v1/documents/tailor-resume  → Direct tailoring                  │   │
│  │ POST /v1/documents/generate-cover-letter → Direct CL generation       │   │
│  │ POST /v1/interviews/{id}/prep     → Direct interview prep             │   │
│  │                                                                       │   │
│  │ These serve the 80% use case: single, specific operations.            │   │
│  │ The agent endpoint serves the 20%: multi-step, exploratory requests.  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 V1 — Specialized Agent Subgraphs

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     V1 AGENT ARCHITECTURE                                      │
│                     ─────────────────────                                      │
│                                                                              │
│  Upgrade from flat tools to specialized subgraphs:                            │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Supervisor routes to 6 subgraphs (not 10 — 4 are still direct calls):│   │
│  │                                                                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │ Profile  │ │ Matching │ │ Resume   │ │ Cover    │ │ Interview│  │   │
│  │  │ Agent    │ │ Agent    │ │ Agent    │ │ Letter   │ │ Agent    │  │   │
│  │  │          │ │          │ │          │ │ Agent    │ │          │  │   │
│  │  │ Parse    │ │ Multi-dim│ │ Tailor   │ │ Generate │ │ Prep     │  │   │
│  │  │ Enrich   │ │ scoring  │ │ Diff     │ │ Research │ │ Mock     │  │   │
│  │  │ Import   │ │ Explain  │ │ ATS      │ │ Tone     │ │ Feedback │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  │                                                                       │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │                      MEMORY AGENT                              │    │   │
│  │  │  (System agent — called by Supervisor before every invocation) │    │   │
│  │  │  Context assembly, episodic logging, semantic retrieval        │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  │  Each agent = LangGraph subgraph with its own state, tools, prompts.  │   │
│  │  Full checkpointing between agent invocations.                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 V2 — Autonomous Multi-Agent

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  V2: Add remaining agents + autonomous orchestration:                        │
│  - Career Coach Agent (skill gap analysis, learning plans)                   │
│  - Application Tracking Agent (status detection via email)                    │
│  - Follow-up Agent (auto-send with user config)                               │
│  - Autopilot mode (auto-apply for match >85%)                                 │
│  - Proactive monitoring (job discovery without user trigger)                  │
│  - Cross-agent learning (matching weights → tailoring strategy)               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Memory Architecture

### 4.1 Final Memory Model (Consistent with MEMORY.md, with simplifications)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MEMORY ARCHITECTURE                                        │
│                                                                              │
│  7 MEMORY TYPES (MVP implements types 1-5. Types 6-7 are V1):                │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ # │ TYPE              │ STORAGE    │ RETENTION    │ MVP │ PURPOSE     │   │
│  │ ──┼──────────────────┼───────────┼────────────┼─────┼──────────── │   │
│  │ 1 │ Short-Term Memory │ Redis      │ Session (24h)│ ✅  │ Current     │   │
│  │   │                   │            │              │     │ conversation│   │
│  │ 2 │ Episodic Memory   │ PostgreSQL │ 90d hot      │ ✅  │ What        │   │
│  │   │                   │(partitioned)│ 730d archive │     │ happened    │   │
│  │ 3 │ Semantic Memory   │ PostgreSQL │ Indefinite   │ ✅  │ What it     │   │
│  │   │                   │ + pgvector │              │     │ means       │   │
│  │ 4 │ User Preferences  │ PostgreSQL │ Indefinite   │ ✅  │ What user   │   │
│  │   │                   │ (versioned)│              │     │ wants       │   │
│  │ 5 │ Career History    │ PostgreSQL │ Indefinite   │ ✅  │ Professional│   │
│  │   │                   │            │              │     │ timeline    │   │
│  │ 6 │ Procedural Memory │ PostgreSQL │ Indefinite   │ V1  │ How to act  │   │
│  │ 7 │ Market Knowledge  │ PostgreSQL │ Indefinite   │ V1  │ Job market  │   │
│  │   │                   │ + pgvector │              │     │ facts       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  CONSOLIDATION (MVP: DAILY. V1: Every 6 hours):                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Runs at 03:00 UTC daily (Celery Beat cron).                           │   │
│  │                                                                       │   │
│  │ For each active user:                                                 │   │
│  │ 1. Fetch episodes since last consolidation                            │   │
│  │ 2. LLM extracts patterns, preferences, insights                       │   │
│  │ 3. Update semantic memories (UPSERT with evidence tracking)            │   │
│  │ 4. Update preference weights (Bayesian)                                │   │
│  │ 5. Update career narrative (incremental append)                        │   │
│  │ 6. Mark episodes as consolidated                                      │   │
│  │                                                                       │   │
│  │ MVP: One LLM call per user per day. ~$0.002/user/day.                 │   │
│  │ Rush consolidation: Offer received → immediate (within 60 seconds).   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  CONTEXT ASSEMBLY (on every agent invocation):                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 1. Always load: profile, preferences, career summary, active pipeline │   │
│  │ 2. Vector search: top-10 semantic memories relevant to intent         │   │
│  │ 3. Recent episodes: last 20 interactions                              │   │
│  │ 4. Assemble within 8K token budget                                     │   │
│  │ 5. Deduplicate (cosine > 0.85 → keep higher importance)               │   │
│  │ 6. Return ContextPackage to agent                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DETAIL: See MEMORY.md for full memory type schemas, lifecycle states,       │
│  ranking formulas, compression strategies, and retrieval algorithms.         │
│  The architecture in MEMORY.md is CORRECT and PRESERVED.                    │
│  Only the consolidation frequency is reduced from 6h→24h for MVP.           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Database Architecture

### 5.1 Final Schema (Consistent with DATABASE.md, with simplifications)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DATABASE ARCHITECTURE                                      │
│                                                                              │
│  SINGLE POSTGRESQL INSTANCE — 6 SCHEMAS:                                     │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ SCHEMA       │ MODULE    │ KEY TABLES (MVP)                           │   │
│  │ ────────────┼──────────┼─────────────────────────────────────────── │   │
│  │ identity     │ identity │ tenants, users, sessions, api_keys,         │   │
│  │              │          │ user_preferences                            │   │
│  │ profile      │ profile  │ profiles, resumes, cover_letters            │   │
│  │ jobs         │ jobs     │ job_postings, companies, job_sources,       │   │
│  │              │          │ job_enrichments                             │   │
│  │ tracking     │ tracking │ applications, interviews, offers,           │   │
│  │              │          │ application_tasks, application_comm         │   │
│  │ memory       │ agent    │ episodic_memories, semantic_memories,       │   │
│  │              │          │ career_timeline, skill_evolution,           │   │
│  │              │          │ consolidation_runs, memory_stats            │   │
│  │ audit        │ shared   │ agent_executions, audit_logs                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  CRITICAL INDEXES (MVP — 15 indexes. Add more when profiling shows need):    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 1.  users: UNIQUE (tenant_id, email)                                  │   │
│  │ 2.  users: (oauth_provider, oauth_subject)                            │   │
│  │ 3.  sessions: (user_id, is_revoked)                                   │   │
│  │ 4.  profiles: UNIQUE (user_id) — one profile per user                 │   │
│  │ 5.  job_postings: UNIQUE (canonical_job_id)                           │   │
│  │ 6.  job_postings: (is_active, first_seen_at DESC)                     │   │
│  │ 7.  job_postings: (company_id)                                        │   │
│  │ 8.  job_postings: HNSW (job_embedding vector_cosine_ops)              │   │
│  │ 9.  applications: (user_id, status)                                   │   │
│  │ 10. applications: UNIQUE (user_id, job_id)                            │   │
│  │ 11. episodic_memories: (user_id, created_at DESC)                     │   │
│  │ 12. episodic_memories: HNSW (embedding vector_cosine_ops)             │   │
│  │ 13. semantic_memories: (user_id, memory_type)                         │   │
│  │ 14. semantic_memories: HNSW (embedding vector_cosine_ops)             │   │
│  │ 15. user_preferences: (user_id, is_current) WHERE is_current = true   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  PARTITIONING:                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ episodic_memories: RANGE (created_at) — daily, 90-day hot retention  │   │
│  │ audit_logs:         RANGE (created_at) — daily, 90-day hot retention  │   │
│  │ agent_executions:   RANGE (created_at) — monthly, 90-day hot          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  HNSW CONFIGURATION:                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ m = 16, ef_construction = 200, ef_search = 100 (default)              │   │
│  │ All vector columns use cosine distance operator.                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DETAIL: See DATABASE.md for full table definitions, column types,           │
│  ENUM catalogs, foreign key maps, backup strategy, and migration rules.      │
│  DATABASE.md is CORRECT in its detailed design. Only the index count          │
│  is reduced from 30 to 15 for MVP. Add indexes when queries demand them.     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Multi-Tenancy

All tenant-scoped tables include `tenant_id UUID NOT NULL`. Isolation is enforced at three layers: application (WHERE clause on every query), connection pool (`SET app.tenant_id`), and database (Row-Level Security as defense-in-depth). Free-tier individual users are their own tenant. Enterprise tenants (universities, bootcamps) have multiple users under one tenant.

---

## 6. API Architecture

### 6.1 Final API Design (Consistent with API.md, with additions)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     API ARCHITECTURE                                           │
│                                                                              │
│  BASE:     https://api.pathfinder.com/v1                                     │
│  FORMAT:   JSON. Cursor-based pagination on all lists.                       │
│  AUTH:     JWT Bearer token (15 min) + httpOnly Refresh cookie (7 days).     │
│                                                                              │
│  ENDPOINT GROUPS:                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ GROUP            │ ENDPOINTS │ MVP │ KEY FEATURES                     │   │
│  │ ────────────────┼──────────┼─────┼───────────────────────────────── │   │
│  │ Auth             │ 10        │ All │ Register, login, refresh, OAuth,  │   │
│  │                  │           │     │ verify-email, forgot/reset pwd,  │   │
│  │                  │           │     │ export-data, delete-account,     │   │
│  │                  │           │     │ api-keys (list/create/delete)    │   │
│  │ Profile          │ 7         │ All │ Import resume/LinkedIn/GitHub,   │   │
│  │                  │           │     │ CRUD profile, version history    │   │
│  │ Resumes          │ 7         │ All │ CRUD resume, templates, download │   │
│  │ Jobs             │ 5         │ All │ Search (15 filters), detail,     │   │
│  │                  │           │     │ similar, companies search/detail │   │
│  │ Match            │ 2         │ All │ Compute matches, submit feedback │   │
│  │ Documents        │ 6         │ All │ Tailor resume, generate CL,      │   │
│  │                  │           │     │ accept/reject, download           │   │
│  │ Applications     │ 8         │ All │ CRUD, status transitions, tasks, │   │
│  │                  │           │     │ communications                   │   │
│  │ Interviews       │ 4         │ All │ Schedule, log outcome, AI prep   │   │
│  │ Agent            │ 5         │ All │ Execute (SSE streaming),         │   │
│  │                  │           │     │ approvals, execution history,    │   │
│  │                  │           │     │ feedback                         │   │
│  │ Preferences      │ 5         │ All │ CRUD, versions, dealbreakers     │   │
│  │ Analytics        │ 3         │ All │ Pipeline, agent usage, market    │   │
│  │ Goals & Learning │ 4         │ V1  │ Goals CRUD, learning plans       │   │
│  │ Notifications    │ 3         │ V1  │ Preferences, digest, history     │   │
│  │ Webhooks         │ 2         │ V1  │ CRUD webhook registrations       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  CRITICAL ADDITIONS (identified in review, missing from API.md):             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ POST /v1/auth/export-data              → GDPR data export (async)     │   │
│  │ GET  /v1/auth/export-data/{id}         → Download export              │   │
│  │ POST /v1/auth/delete-account           → Initiate 30-day deletion     │   │
│  │ GET  /v1/auth/api-keys                 → List API keys                │   │
│  │ POST /v1/auth/api-keys                 → Create API key               │   │
│  │ DELETE /v1/auth/api-keys/{id}          → Revoke API key               │   │
│  │ GET  /v1/health/live                   → Liveness probe               │   │
│  │ GET  /v1/health/ready                  → Readiness probe              │   │
│  │                                                                       │   │
│  │ ALL POST/PUT/PATCH: Idempotency-Key header supported.                 │   │
│  │ ALL file upload endpoints: ClamAV scan before processing.             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DIRECT ENDPOINTS vs AGENT ENDPOINT:                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Direct:    /v1/match, /v1/documents/*, /v1/interviews/*/prep         │   │
│  │            → Single operation. Low latency. No agent overhead.        │   │
│  │ Agent:     /v1/agent/execute                                          │   │
│  │            → Multi-step natural language. Agent plans + orchestrates. │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DETAIL: See API.md for full request/response schemas, error codes,          │
│  validation rules, and rate limiting tables. API.md is CORRECT and           │
│  PRESERVED. The 9 endpoints above are ADDITIONS to API.md.                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Folder Structure

### 7.1 Final Codebase Layout

```
pathfinder/
├── pyproject.toml
├── Dockerfile
├── Dockerfile.dev
├── docker-compose.yml
├── .env.example
├── alembic.ini
├── alembic/
│   └── versions/
│
├── scripts/
│   ├── seed_dev_data.py
│   └── run_consolidation.py
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── identity/
│   │   ├── profile/
│   │   ├── jobs/
│   │   ├── tracking/
│   │   └── agent/
│   ├── integration/
│   │   ├── persistence/
│   │   ├── llm/
│   │   └── api/
│   └── e2e/
│
└── src/
    ├── __init__.py
    │
    ├── shared/                        # Cross-cutting. Depends on NOTHING.
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── base_entity.py
    │   │   ├── base_value_object.py
    │   │   ├── base_repository.py
    │   │   ├── base_domain_event.py
    │   │   ├── identifiers.py         # UserId, JobId, TenantId, etc.
    │   │   ├── result.py              # Result[T] monad
    │   │   ├── money.py
    │   │   ├── location.py
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── ports/                 # Shared abstract interfaces
    │   │   │   ├── logger_port.py
    │   │   │   ├── event_bus_port.py
    │   │   │   ├── unit_of_work.py
    │   │   │   └── clock_port.py
    │   │   └── pagination.py
    │   └── infrastructure/
    │       ├── database.py            # SQLAlchemy engine + session
    │       ├── redis.py               # Redis connection pool
    │       ├── clock.py
    │       ├── logging_config.py
    │       └── middleware/             # FastAPI middleware
    │           ├── auth.py
    │           ├── rate_limit.py
    │           ├── audit.py
    │           └── request_id.py
    │
    ├── identity/                      # Users, Auth, API Keys, Preferences
    │   ├── __init__.py                # Public API surface
    │   ├── domain/
    │   │   ├── entities.py            # User, Tenant, ApiKey
    │   │   ├── value_objects.py
    │   │   ├── repositories.py        # Abstract
    │   │   ├── services.py            # PasswordHasher, TokenService
    │   │   ├── events.py
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── ports/
    │   │   ├── commands.py
    │   │   ├── queries.py
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── persistence/
    │   │   │   ├── models.py          # SQLAlchemy ORM
    │   │   │   ├── user_repository.py
    │   │   │   └── preference_repository.py
    │   │   └── auth/
    │   │       ├── jwt_service.py
    │   │       ├── password_hasher.py
    │   │       └── google_oauth.py
    │   └── presentation/
    │       ├── router.py              # /v1/auth/*, /v1/preferences/*
    │       ├── schemas.py             # Pydantic request/response
    │       └── dependencies.py        # FastAPI Depends() wiring
    │
    ├── profile/                       # Profile, Resume, CoverLetter, Document Gen
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── entities.py            # Profile, Resume, CoverLetter
    │   │   ├── value_objects.py       # Skill, WorkExperience, Education
    │   │   ├── repositories.py
    │   │   ├── services.py            # ResumeTailoringService, CoverLetterService
    │   │   ├── events.py
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── ports/
    │   │   │   ├── llm_port.py
    │   │   │   ├── resume_parser_port.py
    │   │   │   ├── pdf_renderer_port.py
    │   │   │   └── embedding_port.py
    │   │   ├── commands.py
    │   │   ├── queries.py
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── persistence/
    │   │   │   ├── models.py
    │   │   │   ├── profile_repository.py
    │   │   │   └── resume_repository.py
    │   │   ├── llm/
    │   │   │   ├── deepseek_client.py
    │   │   │   ├── openai_client.py
    │   │   │   ├── llm_factory.py
    │   │   │   └── prompts/
    │   │   │       ├── resume_parsing.py
    │   │   │       ├── resume_tailoring.py
    │   │   │       ├── cover_letter.py
    │   │   │       └── factuality_check.py
    │   │   ├── parsing/
    │   │   │   ├── pdf_extractor.py
    │   │   │   ├── docx_extractor.py
    │   │   │   └── resume_parser.py
    │   │   └── rendering/
    │   │       ├── pdf_renderer.py
    │   │       └── ats_simulator.py
    │   └── presentation/
    │       ├── router.py              # /v1/profile/*, /v1/resumes/*, /v1/documents/*
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── jobs/                          # Jobs, Companies, Matching, Scraping
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── entities.py            # JobPosting, Company, JobSource
    │   │   ├── value_objects.py
    │   │   ├── repositories.py
    │   │   ├── services.py            # MatchingEngine, DedupService, EnrichmentService
    │   │   ├── events.py
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── ports/
    │   │   │   ├── job_scraper_port.py
    │   │   │   ├── embedding_port.py
    │   │   │   └── web_search_port.py
    │   │   ├── commands.py
    │   │   ├── queries.py
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── persistence/
    │   │   │   ├── models.py
    │   │   │   ├── job_repository.py
    │   │   │   └── company_repository.py
    │   │   ├── scraping/
    │   │   │   ├── greenhouse_scraper.py
    │   │   │   ├── ycombinator_scraper.py
    │   │   │   ├── hn_scraper.py
    │   │   │   └── scraper_registry.py
    │   │   ├── matching/
    │   │   │   ├── vector_matcher.py
    │   │   │   ├── skill_matcher.py
    │   │   │   ├── experience_matcher.py
    │   │   │   └── explainer.py
    │   │   └── enrichment/
    │   │       └── llm_enricher.py
    │   └── presentation/
    │       ├── router.py              # /v1/jobs/*, /v1/companies/*, /v1/match/*
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── tracking/                      # Applications, Interviews, Communications
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── entities.py            # Application, Interview, Offer, Communication
    │   │   ├── value_objects.py
    │   │   ├── repositories.py
    │   │   ├── services.py            # StatusTransitionValidator, FollowUpGenerator
    │   │   ├── events.py
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── ports/
    │   │   │   ├── email_port.py
    │   │   │   └── llm_port.py
    │   │   ├── commands.py
    │   │   ├── queries.py
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── persistence/
    │   │   │   ├── models.py
    │   │   │   └── application_repository.py
    │   │   └── email/
    │   │       └── resend_sender.py
    │   └── presentation/
    │       ├── router.py              # /v1/applications/*, /v1/interviews/*
    │       ├── schemas.py
    │       └── dependencies.py
    │
    └── agent/                         # LangGraph, Memory, Tools, Consolidation
        ├── __init__.py
        ├── domain/
        │   ├── entities.py            # AgentExecution, ApprovalRequest
        │   ├── value_objects.py       # Intent, ExecutionStatus
        │   ├── repositories.py        # AgentExecutionRepository, MemoryRepository
        │   ├── services.py            # ContextAssembler, PreferenceLearner
        │   ├── events.py
        │   └── exceptions.py
        ├── application/
        │   ├── ports/
        │   │   ├── llm_port.py
        │   │   └── embedding_port.py
        │   ├── commands.py
        │   ├── queries.py
        │   └── handlers.py
        ├── infrastructure/
        │   ├── persistence/
        │   │   ├── models.py          # Memory ORM models
        │   │   ├── memory_repository.py
        │   │   └── agent_execution_repository.py
        │   ├── langgraph/
        │   │   ├── supervisor_graph.py
        │   │   ├── state.py            # TypedDict state schemas
        │   │   ├── nodes/
        │   │   │   ├── guardrail.py
        │   │   │   ├── context_builder.py
        │   │   │   ├── intent_router.py
        │   │   │   ├── task_planner.py
        │   │   │   ├── tool_executor.py
        │   │   │   ├── result_synthesizer.py
        │   │   │   ├── human_gate.py
        │   │   │   └── quality_gate.py
        │   │   ├── tools/
        │   │   │   ├── tool_registry.py
        │   │   │   ├── profile_tools.py
        │   │   │   ├── job_tools.py
        │   │   │   ├── document_tools.py
        │   │   │   ├── tracking_tools.py
        │   │   │   └── memory_tools.py
        │   │   └── checkpointer.py
        │   ├── llm/
        │   │   ├── deepseek_client.py
        │   │   ├── openai_client.py
        │   │   ├── llm_factory.py      # With circuit breaker + fallback
        │   │   └── circuit_breaker.py  # V1 — MVP just retries
        │   ├── memory/
        │   │   ├── episodic_store.py
        │   │   ├── semantic_store.py
        │   │   ├── context_assembler.py
        │   │   ├── ranking.py
        │   │   └── consolidation.py
        │   └── celery_tasks/
        │       ├── scraping.py
        │       ├── enrichment.py
        │       ├── embedding.py
        │       └── consolidation.py
        └── presentation/
            ├── router.py              # /v1/agent/*
            ├── schemas.py
            ├── sse_handler.py
            └── dependencies.py
```

### 7.2 Naming Conventions (Key Rules)

| Element | Convention | Example |
|---------|-----------|---------|
| Entity file | `entities.py` | `domain/entities.py` |
| Repository (abstract) | `repositories.py` | `domain/repositories.py` |
| Repository (concrete) | `{name}_repository.py` | `user_repository.py` |
| Port interface | `{name}_port.py` | `llm_port.py` |
| Port implementation | `{tech}_{port_name}.py` | `deepseek_client.py` |
| FastAPI router | `router.py` | `presentation/router.py` |
| Pydantic schemas | `schemas.py` | `presentation/schemas.py` |
| ORM models | `models.py` | `infrastructure/persistence/models.py` |
| DI wiring | `dependencies.py` | `presentation/dependencies.py` |
| LangGraph nodes | `{name}.py` | `nodes/guardrail.py` |
| Celery tasks | `{domain}.py` | `celery_tasks/scraping.py` |
| Test files | `test_{what}.py` | `test_user_entity.py` |
| Entity class | `Noun` | `User`, `JobPosting` |
| Repository abstract | `{Entity}Repository` | `UserRepository` |
| Repository concrete | `Sql{Entity}Repository` | `SqlUserRepository` |
| Port interface | `{Capability}Port` | `LLMPort` |
| Command DTO | `{Verb}{Noun}Command` | `CreateApplicationCommand` |
| Domain event | `{Noun}{PastTenseVerb}` | `ApplicationSubmitted` |

---

## 8. Security Architecture

### 8.1 Defense Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: EDGE                                                                │
│  ───────────────                                                              │
│  · Cloudflare DNS + SSL (Full encryption)                                     │
│  · Nginx on VM: rate limiting (100 req/s/IP), TLS termination                 │
│  · Firewall: Only 443 + 22 (trusted IPs) open                                 │
│                                                                              │
│  LAYER 2: APPLICATION                                                         │
│  ───────────────────                                                          │
│  · JWT RS256 (access 15min) + httpOnly Refresh Cookie (7 days, rotated)      │
│  · API Key auth (X-API-Key header) for programmatic access                    │
│  · Google OAuth (PKCE flow)                                                   │
│  · CORS: explicit origins only (no wildcard)                                  │
│  · Rate limiting: Redis sliding window, per-tier limits                       │
│  · Input validation: Pydantic strict mode, all inputs                         │
│  · Idempotency-Key on all mutations (~ key reuse attacks)                     │
│  · File upload: allowlist (PDF/DOCX/TXT), 10MB max, ClamAV scan              │
│                                                                              │
│  LAYER 3: DATA                                                                │
│  ─────────────                                                                │
│  · Passwords: Argon2id hashing                                                │
│  · PII: Field-level encryption (email, phone, full_name in profile)          │
│  · Database: TLS in transit, AES-256 at rest                                  │
│  · Tenant isolation: RLS + application WHERE clause                           │
│  · Audit log: immutable append-only, every agent action + user action         │
│                                                                              │
│  LAYER 4: LLM                                                                 │
│  ────────────                                                                 │
│  · Prompt injection: user text wrapped in <user_data> tags, system guard      │
│  · Output validation: structured outputs against JSON Schema                  │
│  · Hallucination prevention: post-generation factuality check                 │
│  · Content safety: input/output moderation (DeepSeek built-in)                │
│  · Data minimization: only essential context sent to LLM                      │
│  · No training: DeepSeek API data processing agreement (opt-out)             │
│                                                                              │
│  LAYER 5: OPERATIONS                                                          │
│  ──────────────────                                                          │
│  · Dependencies: Dependabot + pip-audit in CI                                │
│  · Containers: non-root user, distroless base                                 │
│  · Secrets: never in code. Environment variables or Vault.                   │
│  · PII redaction in logs: PII never sent to Sentry/CloudWatch                │
│  · Session anti-theft: Refresh token reuse → revoke entire family            │
│  · Data export: GDPR/CCPA user data export + deletion APIs                   │
│  · Penetration test: Before public launch                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Observability Architecture

### 9.1 Three Pillars

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LOGGING                                                                      │
│  ───────                                                                      │
│  · Library: structlog (JSON in production, console in development)            │
│  · Every log line: timestamp, level, request_id, user_id, module, message    │
│  · PII redaction: email/phone/name masked before log emission                 │
│  · Agent execution: metadata-only in logs (no input_context/output payloads)  │
│  · Storage: Stdout → Docker log driver → CloudWatch / Loki (V1)              │
│                                                                              │
│  METRICS                                                                      │
│  ───────                                                                      │
│  · Library: prometheus_client (FastAPI instrumentator)                        │
│  · Endpoint: GET /v1/metrics (Prometheus scrape)                              │
│  · RED metrics (per endpoint): Rate, Errors, Duration                         │
│  · Business metrics: applications_submitted, matches_computed, resumes_generated│
│  · LLM metrics: tokens_used, cost_usd, latency_ms (per model, per agent)     │
│  · Dashboard: Grafana (V1: Grafana Cloud free tier)                           │
│  · MVP fallback: /v1/metrics JSON for manual inspection                      │
│                                                                              │
│  ERROR TRACKING                                                               │
│  ──────────────                                                               │
│  · Library: Sentry SDK                                                        │
│  · All unhandled exceptions → Sentry with request context                    │
│  · PII stripping before sending to Sentry                                     │
│  · Alert: Error rate > 5% → PagerDuty / email                                 │
│                                                                              │
│  UPTIME MONITORING                                                            │
│  ─────────────────                                                            │
│  · BetterStack / UptimeRobot: GET /v1/health/ready every 60 seconds          │
│  · Alert: 3 consecutive failures → notification                               │
│                                                                              │
│  HEALTH ENDPOINTS                                                             │
│  ────────────────                                                             │
│  · GET /v1/health/live  → Process alive? (always 200 if running)             │
│  · GET /v1/health/ready → DB + Redis reachable? (200 if healthy)             │
│  · GET /v1/health       → Detailed component status (dev/debug)              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Implementation Roadmap

### 10.1 Phase Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE │ WEEKS │ FOCUS                    │ KEY SHIP                         │
│  ──────┼───────┼─────────────────────────┼───────────────────────────────── │
│   0    │  1–2  │ Foundation               │ CI/CD, Auth, DB, Docker.         │
│        │       │                           │ Health check.                    │
│   1    │  3–4  │ Profile & Identity       │ Resume upload → parsed profile.  │
│        │       │                           │ Preferences + resume management.│
│   2    │  5–6  │ Job Discovery            │ 3 scrapers + search + enrichment. │
│        │       │                           │ Celery sweeps operational.       │
│   3    │   7   │ Matching Engine          │ 6-dimension scoring + explain.    │
│   4    │   8   │ Document Generation      │ Resume tailoring + cover letters. │
│        │       │                           │ Zero hallucination. HITL gates.  │
│   5    │   9   │ Application Pipeline     │ Tracking + interviews + follow-ups│
│        │       │                           │ ← CORE LOOP CLOSED               │
│   6    │ 10–11 │ Agent Orchestration      │ LangGraph Supervisor + tools.     │
│        │       │                           │ SSE streaming. HITL.             │
│   7    │  12   │ Production Hardening     │ Tests, monitoring, deploy.        │
│        │       │                           │ v0.1.0-mvp SHIPPED.              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Critical Path

```
  Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5
                                                          │
                                                    Phase 6 ──► Phase 7
```

### 10.3 MVP Completion Criteria (Go/No-Go)

All 8 criteria must pass before MVP is considered complete:

- [ ] User can upload a resume → structured profile within 10 seconds
- [ ] At least 500 jobs discoverable across 3 sources
- [ ] Job search returns relevant results < 300ms
- [ ] Matching produces explainable scores for any profile + job pair
- [ ] Resume tailoring generates factually accurate output (zero hallucinations)
- [ ] Full application lifecycle: save → apply → interview → offer → accept
- [ ] Agent endpoint handles multi-step natural language requests
- [ ] Production deployment passes health checks + load test (100 concurrent users)

---

## 11. Technology Stack — Final

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER              │ TECHNOLOGY                  │ MVP │ V1   │ V2          │
│  ──────────────────┼────────────────────────────┼─────┼──────┼──────────── │
│  Language           │ Python 3.12+               │ ✅  │ ✅   │ ✅          │
│  Web Framework      │ FastAPI + Uvicorn           │ ✅  │ ✅   │ ✅          │
│  Agent Framework    │ LangGraph                   │ ✅  │ ✅   │ ✅          │
│  Primary LLM        │ DeepSeek API                │ ✅  │ ✅   │ ✅          │
│  Fallback LLM       │ OpenAI GPT-4o               │ ✅  │ ✅   │ ✅          │
│  Database           │ PostgreSQL 16               │ ✅  │ ✅   │ ✅          │
│  Vector Search      │ pgvector (HNSW)             │ ✅  │ ✅   │ ✅          │
│  Cache / Queue      │ Redis 7                     │ ✅  │ ✅   │ ✅          │
│  Background Tasks   │ Celery + Celery Beat        │ ✅  │ ✅   │ ✅          │
│  File Storage       │ Local /data volume          │ ✅  │ -    │ -           │
│  File Storage       │ S3 / R2                     │ -   │ ✅   │ ✅          │
│  Container          │ Docker                      │ ✅  │ ✅   │ ✅          │
│  Orchestration      │ Docker Compose              │ ✅  │ ✅   │ -           │
│  Orchestration      │ Kubernetes                  │ -   │ -    │ ✅          │
│  Auth               │ JWT (self-issued RS256)     │ ✅  │ ✅   │ ✅          │
│  OAuth              │ Google                      │ ✅  │ ✅   │ ✅          │
│  OAuth              │ GitHub                      │ -   │ ✅   │ ✅          │
│  Email              │ Resend                      │ ✅  │ ✅   │ ✅          │
│  Monitoring         │ Sentry + structlog          │ ✅  │ ✅   │ ✅          │
│  Monitoring         │ Prometheus + Grafana        │ -   │ ✅   │ ✅          │
│  Uptime             │ BetterStack                 │ ✅  │ ✅   │ ✅          │
│  CI/CD              │ GitHub Actions              │ ✅  │ ✅   │ ✅          │
│  IaC                │ Manual / Ansible            │ ✅  │ -    │ -           │
│  IaC                │ Terraform                   │ -   │ ✅   │ ✅          │
│  Frontend (Web)     │ Swagger UI (auto-generated) │ ✅  │ -    │ -           │
│  Frontend (Web)     │ Next.js 15                  │ -   │ ✅   │ ✅          │
│  Frontend (Mobile)  │ React Native / Flutter      │ -   │ -    │ ✅          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. MVP / V1 / V2 Scope Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FEATURE                        │ MVP               │ V1         │ V2        │
│  ──────────────────────────────┼──────────────────┼─────────────┼────────── │
│  Resume parsing (PDF/DOCX)      │ ✅                │ ✅          │ ✅        │
│  LinkedIn / GitHub import       │ ✅                │ ✅          │ ✅        │
│  Profile management             │ ✅                │ ✅          │ ✅        │
│  User preferences               │ ✅                │ ✅          │ ✅        │
│  Job discovery (3 sources)      │ ✅                │ 10 sources   │ 30+       │
│  Job search + filters           │ ✅                │ ✅          │ ✅        │
│  Job enrichment (LLM)           │ ✅                │ ✅          │ ✅        │
│  Job deduplication              │ ✅                │ ✅          │ ✅        │
│  Semantic matching (6 dims)     │ ✅                │ ✅          │ ✅        │
│  Match explanations             │ ✅                │ ✅          │ ✅        │
│  Resume tailoring               │ ✅                │ ✅          │ ✅        │
│  Cover letter generation        │ ✅                │ ✅          │ ✅        │
│  HITL approval gates            │ ✅                │ ✅          │ Autopilot │
│  Application tracking           │ ✅                │ ✅          │ ✅        │
│  Interview scheduling           │ ✅                │ ✅          │ ✅        │
│  Interview prep (questions)     │ ✅                │ ✅          │ ✅        │
│  Follow-up emails               │ ✅                │ ✅          │ ✅        │
│  Pipeline analytics (basic)     │ ✅                │ ✅          │ ✅        │
│  Agent orchestration            │ 1 Supervisor+tools │ 6 subgraphs │ 10 agents │
│  SSE streaming                  │ ✅                │ ✅          │ ✅        │
│  Episodic memory                │ ✅                │ ✅          │ ✅        │
│  Semantic memory                │ ✅                │ ✅          │ ✅        │
│  Memory consolidation (daily)   │ ✅                │ 6-hourly    │ 6-hourly  │
│  User preference learning       │ ✅ (implicit)     │ ✅          │ ✅        │
│  Google OAuth                   │ ✅                │ ✅          │ ✅        │
│  GitHub OAuth                   │ -                 │ ✅          │ ✅        │
│  API Keys                       │ ✅                │ ✅          │ ✅        │
│  GDPR export / delete           │ ✅                │ ✅          │ ✅        │
│  Health check endpoints         │ ✅                │ ✅          │ ✅        │
│  Idempotency keys               │ ✅                │ ✅          │ ✅        │
│  ──────────────────────────────┼──────────────────┼─────────────┼────────── │
│  Procedural memory              │ -                 │ ✅          │ ✅        │
│  Market knowledge               │ -                 │ ✅          │ ✅        │
│  Career coach (skill gaps)      │ -                 │ ✅          │ ✅        │
│  Learning plans                 │ -                 │ ✅          │ ✅        │
│  Company enrichment (Crunchbase)│ -                 │ ✅          │ ✅        │
│  Email integration (Gmail)      │ -                 │ ✅          │ ✅        │
│  Calendar integration           │ -                 │ ✅          │ ✅        │
│  Webhooks                       │ -                 │ ✅          │ ✅        │
│  Advanced analytics             │ -                 │ ✅          │ ✅        │
│  Push notifications             │ -                 │ ✅          │ ✅        │
│  Circuit breaker                │ -                 │ ✅          │ ✅        │
│  Next.js frontend               │ -                 │ ✅          │ ✅        │
│  Graceful degradation tiers     │ -                 │ ✅          │ ✅        │
│  ──────────────────────────────┼──────────────────┼─────────────┼────────── │
│  Mock interview simulator       │ -                 │ -           │ ✅        │
│  Autopilot mode                 │ -                 │ -           │ ✅        │
│  Referral detection             │ -                 │ -           │ ✅        │
│  Offer comparison tool          │ -                 │ -           │ ✅        │
│  Mobile apps                    │ -                 │ -           │ ✅        │
│  Browser extension              │ -                 │ -           │ ✅        │
│  Multi-language                 │ -                 │ -           │ ✅        │
│  Kubernetes deployment          │ -                 │ -           │ ✅        │
│  Microservices extraction       │ -                 │ -           │ ✅        │
│  Enterprise dashboard           │ -                 │ -           │ ✅        │
│  Cross-region deployment        │ -                 │ -           │ ✅        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Document Relationships

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  FINAL_ARCHITECTURE.md  ◄── SINGLE SOURCE OF TRUTH                           │
│  ─────────────────────                                                       │
│  This document. Overrides all others on architecture decisions.              │
│                                                                              │
│  SUPPORTING DOCUMENTS (preserved for detailed reference):                    │
│  ───────────────────────────────────────────────────────                     │
│  PRD.md              — Product requirements. Scope authority. CORRECT.       │
│  ARCHITECTURE.md      — Detailed design rationale. REFERENCE ONLY.           │
│  AGENTS.md            — Agent specifications. V1 target. CORRECT at depth.   │
│  MEMORY.md            — Memory type schemas, algorithms. CORRECT at depth.   │
│  DATABASE.md          — Table definitions, SQL patterns. CORRECT at depth.   │
│  API.md               — Endpoint schemas, error codes. CORRECT (with adds).  │
│  CODEBASE.md          — Folder conventions, patterns. MERGED INTO THIS DOC.  │
│  IMPLEMENTATION.md    — Day-by-day plan. CORRECT (with 3-source adjustment). │
│  REVIEW.md            — Audit findings. RESOLVED BY THIS DOCUMENT.           │
│                                                                              │
│  CONFLICT RESOLUTION: Final_Architecture > Supporting > None.                │
│  If FINAL_ARCHITECTURE.md says X and supporting doc says Y → X wins.        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

> *"The architect's job is not to make decisions. It is to make as few decisions as possible, and to defer the rest to the last responsible moment. This document makes the decisions that cannot be deferred."*

**End of Final Architecture Document**
