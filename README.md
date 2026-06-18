# Pathfinder — Autonomous AI Career Agent

> **Status:** Architecture Approved. Ready for Implementation.
> **Architecture Version:** 2.0 FINAL (2026-06-18)

## Overview

**Pathfinder** is a production-grade Autonomous AI Career Agent that helps technical professionals throughout their entire job search journey. It is not a chatbot. It is a persistent, proactive, personal career operating system.

### Core Capabilities

| Capability | Description |
|------------|-------------|
| **Profile Understanding** | Parse resumes, LinkedIn, GitHub — build rich semantic user model |
| **Continuous Job Discovery** | 10–300+ sources, 24/7 sweeping, intelligent deduplication |
| **Semantic Matching** | Multi-dimensional scoring with explainable rationale |
| **Resume Tailoring** | ATS-optimized, job-specific, diff-reviewable, hallucination-free |
| **Cover Letter Generation** | Personalized, evidence-backed, tone-customizable |
| **Application Tracking** | Kanban pipeline, task management, document vault |
| **Interview Preparation** | Company-specific guides, STAR answers, question banks, mock interviews |
| **Communication Agent** | Follow-ups, thank-yous, outreach, recruiter responses |
| **Skill Gap Analysis** | Identify gaps, generate learning plans, track progress |
| **Long-Term Memory** | Persistent user model that improves with every interaction |
| **Proactive Operation** | Push notifications, digests, deadline nudges, passive monitoring, autopilot |

### Target Personas

- **Priya** — Fresher (0–1 YOE), B.Tech CS, seeking first engineering role
- **David** — Mid-career SWE (8 YOE), full-stack, seeking Staff Engineer path
- **Aisha** — Data Engineer (5 YOE), seeking product-company transition
- **Marcus** — AI/ML Engineer (6 YOE + PhD), seeking top-tier research roles
- **Linh** — Career changer (consulting → engineering), bootcamp grad

### Phase Roadmap

| Phase | Timeline | Goal |
|-------|----------|------|
| **MVP** ("Pathfinder Core") | Weeks 1–14 | Prove core loop — profile → discover → match → tailor → apply → track |
| **V1** ("Pathfinder Pro") | Months 3–9 | Expand to 200+ sources, add learning engine, email integration, agent architecture |
| **V2** ("Pathfinder Scale") | Months 9–21 | Scale to 100K+ users, mobile apps, autopilot, mock interviews, enterprise |
| **V3** ("Pathfinder Network") | Year 3 | Two-sided marketplace — candidates + employers + educators |
| **V4** ("Pathfinder Intelligence") | Years 4–5 | Labor market intelligence layer — global career OS |

### Business Model

| Tier | Price | Target |
|------|-------|--------|
| Free | $0/mo | Freshers — limited applications, basic features |
| Pro | $29/mo | Active seekers — unlimited applications, advanced features |
| Premium | $79/mo | Career accelerators — autopilot, priority discovery, coaching |
| Enterprise | Custom | Universities, bootcamps, outplacement firms |

## Repository Structure

```
D:\JOB search Agent\
├── README.md              ← You are here
├── PRD.md                 ← Complete Product Requirements Document
├── ARCHITECTURE.md         ← Complete production architecture (10 deliverables)
├── AGENTS.md                ← Multi-agent system design (LangGraph)
├── MEMORY.md                ← Production-grade memory architecture (7 memory types)
├── DATABASE.md              ← Complete database schema (PostgreSQL + pgvector)
├── API.md                   ← Complete REST API design (FastAPI)
├── CODEBASE.md              ← Production codebase architecture
├── IMPLEMENTATION.md         ← Phase-wise implementation plan (12 weeks)
├── REVIEW.md                ← Principal Engineer architecture review
├── FINAL_ARCHITECTURE.md    ← SINGLE SOURCE OF TRUTH — supersedes all above
├── EPICS_AND_TASKS.md       ← Detailed implementation breakdown (119 tasks)
├── SPRINT_1.md              ← Sprint 1: Foundation (step-by-step)
├── SPRINT_2.md              ← Sprint 2: Core Infrastructure (with code)
├── SPRINT_3.md              ← Sprint 3: Profile & Resume Domain (with code)
├── SPRINT_4.md              ← Sprint 4: Job Discovery Domain (with code)
├── SPRINT_4_REVIEW.md        ← Sprint 4 Principal Engineer Review
├── SPRINT_4_REMEDIATION.md   ← Sprint 4 Remediation Release (v4.0.1)
├── SPRINT_5.md              ← Sprint 5: Job Matching Domain (with code)
├── SPRINT_5_REVIEW.md        ← Sprint 5 Principal Engineer Review
├── SPRINT_5_REMEDIATION.md    ← Sprint 5 Remediation (v5.0.1)
├── SPRINT_6.md              ← Sprint 6: Agent Foundation (with code)
├── SPRINT_6_REVIEW.md        ← Sprint 6 Principal AI Engineer Review
├── SPRINT_6_REMEDIATION.md   ← Sprint 6 Remediation (v6.0.1)
├── SPRINT_7.md              ← Sprint 7: Memory System (with code)
├── SPRINT_7_REVIEW.md        ← Sprint 7 Principal AI Engineer Review
├── SPRINT_7_REMEDIATION.md   ← Sprint 7 Remediation (v7.0.1)
├── SPRINT_7_REMEDIATION_REVIEW.md ← Sprint 7 Remediation Final Review
├── SPRINT_7_FINAL.md        ← Sprint 7 Finalization (v7.0.2) ★ APPROVED
├── SPRINT_8.md              ← Sprint 8: Knowledge & RAG System (with code)
├── SPRINT_8_REVIEW.md        ← Sprint 8 Principal AI Engineer Review
├── SPRINT_8_REMEDIATION.md   ← Sprint 8 Remediation (v8.0.1) ★ APPROVED
├── ARCHITECTURE_AUDIT.md    ← Full System Architecture Audit (Sprints 1-8)
├── SPRINT_9.md              ← Sprint 9: Resume Tailoring Engine (with code)
├── docs/                    ← Additional documentation (to be added)
├── design/                 ← Design files, wireframes, mockups (to be added)
└── src/                    ← Source code (to be added — MVP development)
```

## Key Documents

- **[PRD.md](./PRD.md)** — Full Product Requirements Document (v1.0). Executive summary, personas, user journeys, 120+ functional requirements, non-functional requirements, success metrics, MVP/V1/V2 scope, risk register, and roadmap through V4.
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — Complete Production Architecture (v1.0). High-level and low-level architecture, service boundaries, communication patterns, scalability design for 100K users, caching strategy, storage strategy, security architecture (defense-in-depth), failure recovery, and deployment architecture.
- **[AGENTS.md](./AGENTS.md)** — Multi-Agent System Design (v1.0). 10 specialized agents with purpose, inputs, outputs, tools, memory, failure handling, and evaluation. Supervisor agent, LangGraph orchestration, state definitions, retry mechanisms, circuit breakers, and HITL approval workflows.
- **[MEMORY.md](./MEMORY.md)** — Production-Grade Memory Architecture (v1.0). 7 memory types (STM, LTM, episodic, semantic, procedural, preference, career history). Full lifecycle, 5 retrieval routes, ranking formula, 4 compression strategies, 4-level summarization pipeline, versioning, deletion cascade, complete PostgreSQL+pgvector schema design, and 5 retrieval algorithms.
- **[DATABASE.md](./DATABASE.md)** — Complete Database Schema (v1.0). ER diagram, 30+ table definitions, FK map, 30 indexes, partitioning, query optimization, backup strategy, migration rules.
- **[API.md](./API.md)** — Complete REST API Design (v1.0). 80+ endpoints across 14 domains with full request/response schemas, error codes, validation rules, rate limiting, SSE streaming, HITL approval flow.
- **[CODEBASE.md](./CODEBASE.md)** — Production Codebase Architecture (v1.0). Clean Architecture + DDD. Full folder structure, layer rules, naming conventions, 12 design patterns, DI strategy.
- **[IMPLEMENTATION.md](./IMPLEMENTATION.md)** — Phase-Wise Implementation Plan (v1.0). Solo developer, 12 weeks, 7 phases. Day-by-day tasks, deliverables, risks, testing, acceptance criteria.
- **[REVIEW.md](./REVIEW.md)** — Principal Engineer Architecture Review (v1.0). Audit findings: 3 contradictions, 7 over-engineering, 7 missing, 5 simplifications.
- **[FINAL_ARCHITECTURE.md](./FINAL_ARCHITECTURE.md)** — ⭐ **SINGLE SOURCE OF TRUTH** (v2.0). Resolves all contradictions. 10 deliverables. Clear MVP/V1/V2 separation. This document overrides all others.
- **[EPICS_AND_TASKS.md](./EPICS_AND_TASKS.md)** — Detailed Implementation Breakdown (v1.0). 8 epics, 119 tasks, 448 hours. Execution order.
- **[SPRINT_1.md](./SPRINT_1.md)** — Sprint 1: Foundation (v1.0). Project skeleton, Docker, folder structure, dependencies.
- **[SPRINT_2.md](./SPRINT_2.md)** — Sprint 2: Core Infrastructure (v1.0). Full code: PostgreSQL, Alembic, Redis, Repository, UoW, Domain entities, Auth, JWT. 35+ tests.
- **[SPRINT_3.md](./SPRINT_3.md)** — Sprint 3: Profile & Resume Domain (v1.0). Full code: Profile entity, Resume entity, Skill extraction, Resume parsing (PDF/DOCX via LLM), DeepSeek client, API endpoints, tests.
- **[SPRINT_4.md](./SPRINT_4.md)** — Sprint 4: Job Discovery Domain (v1.0). Full code: 3 source adapters, pluggable framework, normalization, dedup, search API, Celery. 24+ tests.
- **[SPRINT_4_REVIEW.md](./SPRINT_4_REVIEW.md)** — Sprint 4 Principal Engineer Review. 3 critical, 5 major, 8 minor issues.
- **[SPRINT_4_REMEDIATION.md](./SPRINT_4_REMEDIATION.md)** — Sprint 4 Remediation Release (v4.0.1). All 10 issues fixed. Production-ready. 16 new tests.
- **[SPRINT_5.md](./SPRINT_5.md)** — Sprint 5: Job Matching Domain (v1.0). 6 dimension scorers, LLM explainability, skill gap analysis, 6 API endpoints.
- **[SPRINT_5_REVIEW.md](./SPRINT_5_REVIEW.md)** — Sprint 5 PE Review. 4 major, 15 minor. APPROVED with mandatory fixes.
- **[SPRINT_5_REMEDIATION.md](./SPRINT_5_REMEDIATION.md)** — Sprint 5 Remediation (v5.0.1). All 4 mandatory fixes applied. PRODUCTION READY.
- **[SPRINT_6.md](./SPRINT_6.md)** — Sprint 6: Agent Foundation (v1.0). LangGraph Supervisor Agent with 7 tools. Intent routing, SSE streaming, HITL approvals.
- **[SPRINT_6_REVIEW.md](./SPRINT_6_REVIEW.md)** — Sprint 6 PE Review. 2 critical, 6 major, 20 minor. Agentic quality: Level 2.
- **[SPRINT_6_REMEDIATION.md](./SPRINT_6_REMEDIATION.md)** — Sprint 6 Remediation (v6.0.1). All 8 issues resolved. APPROVED.
- **[SPRINT_7.md](./SPRINT_7.md)** — Sprint 7: Memory System (v1.0). Episodic, Semantic, Procedural memory. pgvector. Consolidation.
- **[SPRINT_7_REVIEW.md](./SPRINT_7_REVIEW.md)** — Sprint 7 PE Review. 5 critical, 7 major. NOT APPROVED.
- **[SPRINT_7_REMEDIATION.md](./SPRINT_7_REMEDIATION.md)** — Sprint 7 Remediation (v7.0.1). All 12 issues resolved.
- **[SPRINT_7_REMEDIATION_REVIEW.md](./SPRINT_7_REMEDIATION_REVIEW.md)** — Final validation. 4 wiring gaps.
- **[SPRINT_7_FINAL.md](./SPRINT_7_FINAL.md)** — Sprint 7 Finalization (v7.0.2). All gaps closed. ★ APPROVED.
- **[SPRINT_8.md](./SPRINT_8.md)** — Sprint 8: Knowledge & RAG System (v1.0). Document ingestion, chunking, hybrid retrieval, re-ranking, agent integration.
- **[SPRINT_8_REVIEW.md](./SPRINT_8_REVIEW.md)** — Sprint 8 PE Review. 1 critical, 4 major.
- **[SPRINT_8_REMEDIATION.md](./SPRINT_8_REMEDIATION.md)** — Sprint 8 Remediation (v8.0.1). ★ APPROVED.
- **[ARCHITECTURE_AUDIT.md](./ARCHITECTURE_AUDIT.md)** — Full System Audit (Sprints 1–8). B+ overall. ★ APPROVED.
- **[SPRINT_9.md](./SPRINT_9.md)** — Sprint 9: Resume Tailoring Engine (v1.0). LLM-based tailoring with factuality guardrails, keyword optimization, diff tracking, version management.

## Getting Involved

This project is in the planning phase. Review the PRD for product decisions and ARCHITECTURE.md for technical decisions.

---

*"The best time to look for a job is when you don't need one. The second best time is with Pathfinder."*
