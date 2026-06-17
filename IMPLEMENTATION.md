# Pathfinder — Phase-Wise Implementation Plan

**Document Version:** 1.0
**Date:** 2026-06-18
**Role:** Engineering Manager
**Developer:** Solo (Full-Stack Senior Engineer)
**Timeline:** 12 Weeks (3 Months)
**Target:** Production MVP
**Classification:** Confidential — Internal

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Phase 0: Foundation](#2-phase-0-foundation)
3. [Phase 1: Profile & Identity](#3-phase-1-profile--identity)
4. [Phase 2: Job Discovery](#4-phase-2-job-discovery)
5. [Phase 3: Matching Engine](#5-phase-3-matching-engine)
6. [Phase 4: Document Generation](#6-phase-4-document-generation)
7. [Phase 5: Application Pipeline](#7-phase-5-application-pipeline)
8. [Phase 6: Agent Orchestration](#8-phase-6-agent-orchestration)
9. [Phase 7: Production Hardening](#9-phase-7-production-hardening)
10. [Risk Register](#10-risk-register)
11. [Weekly Burn-Down Summary](#11-weekly-burn-down-summary)

---

## 1. Executive Summary

### 1.1 The Challenge

One developer. Twelve weeks. A production-grade AI career agent. The temptation is to build everything shallow. The discipline is to build the core deep — a working vertical slice that delivers real value, with the architecture to expand later.

### 1.2 Strategy

| Principle | Application |
|-----------|-------------|
| **Vertical-first** | Complete one feature end-to-end before starting the next. Demo-able at every phase boundary. |
| **Simple until proven complex** | No microservices. Modular monolith. No Kubernetes. Docker Compose on a VM. |
| **Bought before built** | Auth (Clerk/Auth0). Email (Resend). File storage (S3). LLM (DeepSeek API). Never build what you can rent. |
| **Good enough > perfect** | Working code shipped Friday beats perfect code shipped never. Refactor in Phase 7. |
| **Test the happy path first** | Core flows tested with integration tests. Edge cases documented, prioritized, fixed later. |
| **Ship every Friday** | Something deployable at the end of every week. Momentum is everything for a solo dev. |

### 1.3 What Gets Cut (Deferred to Post-MVP)

| Feature | Reason |
|---------|--------|
| Native mobile apps | Web responsive first |
| Full LangGraph multi-agent | Single-agent with tool calling for MVP; multi-agent in V1 |
| Email integration (Gmail OAuth) | Manual status updates for MVP |
| Calendar integration | Manual interview logging |
| Advanced analytics dashboard | Basic pipeline view only |
| Mock interview simulator | Question prep only |
| Skill gap analysis + learning plans | Career coach deferred |
| Company enrichment (Crunchbase) | Manual company data |
| Referral detection | Deferred |
| Browser extension | Deferred |
| Multi-language support | English only |

### 1.4 What Ships

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MVP CORE LOOP                                        │
│                                                                              │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│   │ PROFILE  │───►│ DISCOVER │───►│  MATCH   │───►│  TAILOR  │             │
│   │          │    │          │    │          │    │          │             │
│   │ Resume   │    │ 10 job   │    │ Semantic │    │ Resume + │             │
│   │ upload   │    │ sources  │    │ +keyword │    │ Cover    │             │
│   │ + parse  │    │          │    │ scoring  │    │ Letter   │             │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘             │
│        │                                               │                    │
│        │              ┌──────────┐                     │                    │
│        └──────────────│  TRACK   │◄────────────────────┘                    │
│                       │          │                                          │
│                       │ Kanban   │                                          │
│                       │ pipeline │                                          │
│                       │ +follow- │                                          │
│                       │ ups      │                                          │
│                       └──────────┘                                          │
│                                                                              │
│   SUPPORTING: Auth, Interview prep (questions only), Task management         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.5 Phase Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WEEK  │ 1  │ 2  │ 3  │ 4  │ 5  │ 6  │ 7  │ 8  │ 9  │ 10 │ 11 │ 12 │      │
│  ──────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤      │
│  PHASE │ 0: FOUNDATION  │ 1: PROFILE │ 2: JOBS │3:MATCH│4:DOC │5:PIPE│      │
│        │                │             │         │       │      │      │      │
│  PHASE │                │             │         │       │ 6: AGENT ORCH  │      │
│        │                │             │         │       │                │      │
│  PHASE │                │             │         │       │ 7: HARDENING  │      │
│  ──────┴────────────────┴─────────────┴─────────┴───────┴──────────────┘      │
│                                                                              │
│  WEEKLY DEPLOYABLE: Every Friday. Something demonstrable ships.              │
│  PHASE GATES:     Go/No-Go at each phase boundary before proceeding.         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 0: Foundation

**Duration:** Week 1–2 (10 working days)
**Goal:** Everything needed before a single line of business logic is written. At the end of Phase 0, a stranger can clone the repo, run `docker compose up`, and hit a health-check endpoint with a database behind it.

### 2.1 Features

- Project scaffolding with Clean Architecture boundaries
- Database schema creation and migration tooling
- Authentication system (register, login, JWT)
- CI/CD pipeline (lint, type-check, test, build)
- Development environment with Docker Compose
- Health checks and basic monitoring

### 2.2 Tasks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WEEK 1                                                                      │
│  ────────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DAY 1–2: Project Scaffolding                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Initialize Python project with Poetry/pyproject.toml               │   │
│  │ ☐ Create full folder structure (all 14 bounded contexts, empty)      │   │
│  │ ☐ Install dependencies: fastapi, uvicorn, sqlalchemy, asyncpg,       │   │
│  │   pgvector, redis, langgraph, pydantic, pydantic-settings,           │   │
│  │   httpx, structlog, tenacity                                         │   │
│  │ ☐ Install dev dependencies: pytest, black, ruff, mypy, faker         │   │
│  │ ☐ Configure black (line-length=100), ruff (strict rules),            │   │
│  │   mypy (strict=true)                                                 │   │
│  │ ☐ Create .editorconfig, .gitignore                                   │   │
│  │ ☐ Write shared/domain/ primitives:                                   │   │
│  │   - base_entity.py (id, created_at, updated_at)                      │   │
│  │   - base_value_object.py (frozen, __eq__ by value)                   │   │
│  │   - base_repository.py (generic ABC)                                 │   │
│  │   - identifiers.py (UserId, TenantId, JobId, ApplicationId)          │   │
│  │   - result.py (Result[T] monad — success/failure)                    │   │
│  │   - exceptions.py (DomainError, NotFoundError, ValidationError)      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 3–4: Database Setup                                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Write Docker Compose: PostgreSQL 16 + pgvector, Redis 7, MinIO     │   │
│  │ ☐ Write Dockerfile.dev (Python 3.12, hot-reload)                     │   │
│  │ ☐ Configure SQLAlchemy async engine + session factory                 │   │
│  │ ☐ Write Alembic configuration + initial migration                     │   │
│  │ ☐ Create core tables migration:                                       │   │
│  │   - tenants, users, sessions, api_keys                                │   │
│  │ ☐ Create shared/infrastructure/database.py (engine, get_session)     │   │
│  │ ☐ Create shared/infrastructure/redis.py (connection pool)            │   │
│  │ ☐ Verify: docker compose up → DB accepts connections → Redis pings   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 5: Auth System                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Implement identity/domain/: User entity, Email VO, exceptions      │   │
│  │ ☐ Implement identity/infrastructure/:                                 │   │
│  │   - user_repository.py (SQLAlchemy)                                   │   │
│  │   - password_hasher.py (Argon2)                                       │   │
│  │   - jwt_service.py (RS256, access + refresh)                          │   │
│  │   - ORM models                                                         │   │
│  │ ☐ Implement identity/presentation/:                                    │   │
│  │   - POST /v1/auth/register                                             │   │
│  │   - POST /v1/auth/login                                                │   │
│  │   - POST /v1/auth/refresh                                              │   │
│  │   - Auth middleware (Depends)                                          │   │
│  │ ☐ Write 5 unit tests for User entity + Email VO                        │   │
│  │ ☐ Write 3 integration tests for register/login flow                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  WEEK 2                                                                      │
│  ────────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DAY 6–7: CI/CD & Infrastructure                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ GitHub Actions workflow:                                            │   │
│  │   - Lint (ruff)                                                       │   │
│  │   - Type check (mypy)                                                 │   │
│  │   - Unit tests (pytest)                                               │   │
│  │   - Integration tests (docker compose up postgres, run tests)         │   │
│  │   - Build Docker image                                                │   │
│  │ ☐ Dockerfile (production): multi-stage, non-root user                  │   │
│  │ ☐ Configure structlog (JSON in prod, console in dev)                   │   │
│  │ ☐ Health check endpoint: GET /v1/health (DB + Redis status)           │   │
│  │ ☐ Sentry integration (error tracking)                                  │   │
│  │ ☐ Prometheus metrics endpoint: GET /v1/metrics                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 8–9: Configuration & Error Handling                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ pydantic Settings class with all env vars (DB, Redis, LLM, JWT)    │   │
│  │ ☐ .env.example with all required variables documented                 │   │
│  │ ☐ Global exception handlers (map domain errors → HTTP status)         │   │
│  │ ☐ Request ID middleware (UUIDv7 per request, response header)         │   │
│  │ ☐ CORS middleware (configurable origins)                               │   │
│  │ ☐ Rate limiting middleware (Redis sliding window)                      │   │
│  │ ☐ Audit logging middleware                                            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 10: Polish & Gate Review                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Write README: setup instructions, architecture overview             │   │
│  │ ☐ Verify all CI checks pass on main branch                             │   │
│  │ ☐ Deploy to staging VM (fly.io / Railway / Hetzner VPS)               │   │
│  │ ☐ Run smoke tests against staging                                     │   │
│  │ ☐ PHASE GATE REVIEW: Go/No-Go decision                                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Deliverables

| Deliverable | Acceptance Criteria |
|-------------|-------------------|
| **GitHub repo** | Clean commit history. All CI checks green. README complete. |
| **Docker Compose** | `docker compose up` → PostgreSQL, Redis, MinIO, API server all running |
| **Auth API** | Register, login, refresh token, logout all working. JWT RS256. |
| **Database** | All core tables created. Alembic up/down works. |
| **CI/CD** | Lint, type-check, unit tests, integration tests all passing on push |
| **Health endpoint** | GET /v1/health returns 200 with DB/Redis status |

### 2.4 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Library version conflicts (pgvector + SQLAlchemy async) | High | Pin exact versions. Test integration on Day 3. |
| Docker networking issues on Windows | Medium | Test on target OS by Day 2. Use host networking if needed. |
| JWT key generation complexity | Low | Use openssl CLI. Document in README. |

### 2.5 Testing

```
┌─────────────────────────────────────────────────────────────────────┐
│  UNIT TESTS (target: 15)                                             │
│  · User entity: creation, email validation, tier defaults            │
│  · Email value object: valid/invalid formats, equality               │
│  · Result monad: success, failure, map, flat_map                     │
│  · Password hasher: hash, verify, different passwords                │
│                                                                      │
│  INTEGRATION TESTS (target: 8)                                       │
│  · POST /v1/auth/register → 201 + user in DB                         │
│  · POST /v1/auth/register duplicate email → 409                      │
│  · POST /v1/auth/login valid → 200 + tokens                          │
│  · POST /v1/auth/login invalid → 401                                 │
│  · POST /v1/auth/refresh → 200 + new tokens                          │
│  · POST /v1/auth/refresh reused token → 401 (anti-theft)             │
│  · GET /v1/health → 200 + db:ok, redis:ok                            │
│  · Protected route without auth → 401                                │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.6 Acceptance Criteria

- [ ] `docker compose up` builds and runs without errors on a clean checkout
- [ ] All 15 unit tests pass in < 2 seconds
- [ ] All 8 integration tests pass in < 30 seconds
- [ ] `ruff check` returns zero errors
- [ ] `mypy src/` returns zero errors with strict mode
- [ ] Health endpoint returns 200 with DB and Redis status
- [ ] Staging deployment accessible via HTTPS
- [ ] Auth flow works end-to-end (register → login → access protected route)

---

## 3. Phase 1: Profile & Identity

**Duration:** Week 3–4 (10 working days)
**Goal:** Users can upload their resume, get a structured profile, manage their skills and experience, and set preferences. This is the foundation all AI features depend on.

### 3.1 Features

- Resume upload and LLM parsing
- Profile CRUD (work history, education, skills, projects)
- Profile version history
- User preferences management
- Skill extraction with proficiency inference

### 3.2 Tasks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WEEK 3                                                                      │
│  ────────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DAY 11–12: Database & Domain                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Migration: profiles, resumes, user_preferences tables              │   │
│  │ ☐ Migration: career_timeline, skill_evolution tables                 │   │
│  │ ☐ profile/domain/: Profile entity, WorkExperience, Education,        │   │
│  │   Skill value objects, SkillProficiency enum                         │   │
│  │ ☐ profile/domain/: ProfileRepository (abstract)                      │   │
│  │ ☐ profile/domain/exceptions.py                                       │   │
│  │ ☐ profile/infrastructure/persistence/: SQLAlchemy models + repo      │   │
│  │ ☐ Unit tests: Profile entity, skill proficiency validation           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 13–14: Resume Parsing (DeepSeek Integration)                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ documents/infrastructure/llm/: DeepSeek API adapter                │   │
│  │   - Async client with httpx                                          │   │
│  │   - Structured output via JSON mode                                   │   │
│  │   - Token counting + cost tracking                                    │   │
│  │   - Timeout (30s) + retry (3× with backoff) + circuit breaker         │   │
│  │ ☐ Create resume parsing prompt template (system + user)               │   │
│  │   - Input: raw resume text (PDF → text via PyPDF2)                    │   │
│  │   - Output: structured JSON (work history, education, skills, etc.)   │   │
│  │ ☐ profile/infrastructure/parsing/resume_parser.py                     │   │
│  │ ☐ profile/presentation/:                                              │   │
│  │   - POST /v1/profile/import/resume (multipart file upload)            │   │
│  │   - GET /v1/profile (with expand)                                     │   │
│  │   - PUT /v1/profile                                                    │   │
│  │   - PATCH /v1/profile                                                 │   │
│  │ ☐ Integration test: upload real resume PDF → verify parsed output     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 15: Profile Enrichment & Skills                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Skill extraction from parsed resume + LLM proficiency inference    │   │
│  │ ☐ POST /v1/profile/import/github (fetch public repos, languages)     │   │
│  │ ☐ POST /v1/profile/import/linkedin (PDF export upload)               │   │
│  │ ☐ Profile embedding generation (DeepSeek embedding API)               │   │
│  │ ☐ Skill embeddings storage in pgvector                                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  WEEK 4                                                                      │
│  ────────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DAY 16–17: Resume Management                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ documents/domain/: Resume entity, resume value objects              │   │
│  │ ☐ documents/infrastructure/persistence/: Resume repository + models   │   │
│  │ ☐ documents/presentation/:                                            │   │
│  │   - GET /v1/resumes (list)                                            │   │
│  │   - POST /v1/resumes (create base resume)                             │   │
│  │   - GET /v1/resumes/{id} (get with content)                           │   │
│  │   - PUT /v1/resumes/{id} (update)                                     │   │
│  │   - DELETE /v1/resumes/{id} (delete, with active-app check)           │   │
│  │   - GET /v1/resumes/templates (list available templates)              │   │
│  │   - GET /v1/resumes/{id}/download (PDF)                               │   │
│  │ ☐ Basic PDF rendering (WeasyPrint / LaTeX template)                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 18–19: User Preferences                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ identity/application/: preference commands, queries, handlers       │   │
│  │ ☐ identity/presentation/:                                             │   │
│  │   - GET /v1/preferences (current, with version + confidence)          │   │
│  │   - PUT /v1/preferences (full replace)                                │   │
│  │   - PATCH /v1/preferences (partial update)                            │   │
│  │   - GET /v1/preferences/versions (history)                            │   │
│  │   - POST /v1/preferences/dealbreakers (add)                           │   │
│  │   - DELETE /v1/preferences/dealbreakers/{index}                       │   │
│  │ ☐ Preference versioning: new row on each significant change           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 20: Integration & Gate                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ End-to-end test: register → upload resume → view profile →          │   │
│  │   create base resume → set preferences                                │   │
│  │ ☐ Manual QA: upload 5 real resume PDFs of varying formats             │   │
│  │ ☐ Fix parsing issues found                                            │   │
│  │ ☐ PHASE GATE REVIEW: Go/No-Go                                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Deliverables

| Deliverable | Acceptance Criteria |
|-------------|-------------------|
| **Resume parsing** | Upload PDF → structured profile with >80% field accuracy on 5 test resumes |
| **Profile API** | Full CRUD with version history. Embedding regenerates on update. |
| **Resume management** | Create base resume, list, view, update, delete, download as PDF |
| **User preferences** | Set role, compensation, location, culture preferences with version history |

### 3.4 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| DeepSeek parsing quality varies by resume format | High | Build fallback parser (regex-based extraction). Test with 10 varied resumes. |
| PDF text extraction fails on scanned/image resumes | Medium | Accept DOCX/TXT as alternatives. Add clear error message for scanned PDFs. |
| Embedding API costs surprise at scale | Low | Cache embeddings. Track cost per user. Add cost limits. |

### 3.5 Testing

```
┌─────────────────────────────────────────────────────────────────────┐
│  UNIT TESTS (target: 25)                                             │
│  · Profile entity: creation, add work experience, add skill          │
│  · SkillProficiency VO: valid enum values, ordering                  │
│  · WorkExperience: date validation (start < end)                     │
│  · ResumeParser (mocked LLM): returns structured data from text      │
│  · Preference update: weight validation (must sum to 1.0)            │
│                                                                      │
│  INTEGRATION TESTS (target: 15)                                      │
│  · Upload PDF → parse → profile created with work history            │
│  · Upload corrupted file → 400 error                                 │
│  · Upload non-PDF → 400 error                                        │
│  · PUT profile → version incremented → embedding regenerated         │
│  · PATCH profile → only changed fields updated                       │
│  · GET profile with expand=skills → skills included                  │
│  · Create base resume → PDF download works                           │
│  · Delete resume linked to active app → 409                          │
│  · Set preferences → weights validated → version incremented         │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.6 Acceptance Criteria

- [ ] Upload a real resume PDF → parsed profile appears within 10 seconds
- [ ] Profile persists across logout/login
- [ ] Skill extraction identifies at least 80% of skills present in resume
- [ ] PDF resume download produces a clean, ATS-readable document
- [ ] User preferences save and immediately affect subsequent API responses
- [ ] All API endpoints return documented status codes for error cases

---

## 4. Phase 2: Job Discovery

**Duration:** Week 5–6 (10 working days)
**Goal:** Jobs flow into the system continuously. Users can search and browse. The job database is fresh, deduplicated, and enriched.

### 4.1 Features

- Multi-source job scraping (10 initial sources)
- Job deduplication (exact + fuzzy)
- Job enrichment (LLM-based: tech stack, seniority, salary extraction)
- Job search API (keyword + filters + vector)
- Background job discovery sweeps (Celery + Celery Beat)

### 4.2 Tasks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WEEK 5                                                                      │
│  ────────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DAY 21–22: Database & Domain                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Migration: job_postings, companies, job_sources, job_enrichments    │   │
│  │ ☐ jobs/domain/: JobPosting entity, Company entity, value objects      │   │
│  │   (SalaryRange, JobLocation, RemotePolicy)                             │   │
│  │ ☐ jobs/domain/: JobRepository, CompanyRepository (abstract)           │   │
│  │ ☐ jobs/domain/: JobDeduplicationService                               │   │
│  │ ☐ jobs/infrastructure/persistence/: SQLAlchemy models + repos         │   │
│  │ ☐ Unit tests: JobPosting entity, dedup logic                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 23–24: Scraping Infrastructure                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ jobs/infrastructure/scraping/base_scraper.py (abstract)            │   │
│  │ ☐ Implement 5 scrapers (Day 23–24):                                   │   │
│  │   1. Greenhouse board scraper (public API + HTML fallback)            │   │
│  │   2. Lever board scraper (public API)                                  │   │
│  │   3. Y Combinator jobs (JSON API)                                     │   │
│  │   4. Hacker News "Who's Hiring" (HTML parse + regex)                  │   │
│  │   5. Wellfound (AngelList) (public listings)                          │   │
│  │ ☐ scraper_registry.py (register all scrapers)                         │   │
│  │ ☐ Rate limiting per scraper (respect robots.txt, add delays)          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 25: Scraping (continued) + Deduplication                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Implement 5 more scrapers:                                          │   │
│  │   6. LinkedIn (public job listings — no auth)                          │   │
│  │   7. Indeed (public listings)                                          │   │
│  │   8. Stack Overflow Jobs                                              │   │
│  │   9. GitHub Jobs (if still available) /替代                            │   │
│  │   10. Workable board scraper                                           │   │
│  │ ☐ Job deduplication pipeline:                                          │   │
│  │   Tier 1: Exact match (title + company + location hash)               │   │
│  │   Tier 2: Fuzzy match (cosine similarity > 0.92 on embeddings)        │   │
│  │   Tier 3: LLM judge for ambiguous cases (batched, cost-controlled)    │   │
│  │ ☐ Canonical job ID assignment                                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  WEEK 6                                                                      │
│  ────────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DAY 26–27: Job Enrichment & Embedding                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ LLM enrichment pipeline:                                             │   │
│  │   - Extract tech stack from job description                            │   │
│  │   - Infer seniority level (junior/mid/senior/staff)                    │   │
│  │   - Extract salary range if mentioned in text                          │   │
│  │   - Detect remote policy                                              │   │
│  │   - Extract required + nice-to-have skills                             │   │
│  │ ☐ Job embedding generation (DeepSeek, 3072d)                           │   │
│  │ ☐ HNSW index creation on job_embedding column                          │   │
│  │ ☐ Company normalization (canonical name matching)                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 28: Job Search API                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ jobs/presentation/:                                                 │   │
│  │   - GET /v1/jobs (search with 15 filter params, cursor pagination)    │   │
│  │   - GET /v1/jobs/{id} (detail with expand)                            │   │
│  │   - GET /v1/jobs/{id}/similar (vector search)                         │   │
│  │   - GET /v1/companies (search/browse)                                  │   │
│  │   - GET /v1/companies/{id} (detail)                                   │   │
│  │ ☐ Full-text search via tsvector on description_clean                   │   │
│  │ ☐ Vector search via pgvector HNSW                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 29: Background Jobs (Celery)                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Celery worker setup (Redis broker)                                   │   │
│  │ ☐ Celery Beat schedule:                                                │   │
│  │   - Every 1 hour: sweep all 10 sources                                  │   │
│  │   - Every 6 hours: enrichment pipeline for un-enriched jobs            │   │
│  │   - Every 24 hours: stale job detection + cleanup                      │   │
│  │ ☐ Task: sweep_source(source_id) → scrape → normalize → dedup → store  │   │
│  │ ☐ Task: enrich_job(job_id) → LLM enrich → update                      │   │
│  │ ☐ Task: embed_job(job_id) → generate embedding → store                │   │
│  │ ☐ Error handling: retry 3× with backoff, dead letter queue            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 30: Integration & Gate                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Run first full sweep against all 10 sources                          │   │
│  │ ☐ Verify: jobs appear in DB, dedup works, enrichment runs              │   │
│  │ ☐ Manual verification: check 50 random jobs for data quality           │   │
│  │ ☐ Load test: 10,000 jobs in DB → search response < 300ms               │   │
│  │ ☐ PHASE GATE REVIEW: Go/No-Go                                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Deliverables

| Deliverable | Acceptance Criteria |
|-------------|-------------------|
| **10 job sources** | Each source successfully scrapes. Jobs appear in DB within 1 hour of posting. |
| **Deduplication** | Same job posted on 3 sources → 1 canonical listing in DB |
| **Job enrichment** | Tech stack, seniority, salary correctly extracted for >70% of jobs |
| **Job search API** | Full-text + vector search. 15 filter parameters. Response < 300ms. |
| **Background sweeps** | Celery Beat runs sweeps on schedule. Failed sweeps retry. |

### 4.4 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Source changes HTML structure → scraper broken | High | Monitor scraper success rate. Alert on >30% failure. Use LLM as fallback parser. |
| Rate limiting / IP blocking | High | Rotate user agents. Respect robots.txt. Add delays between requests. |
| DeepSeek enrichment cost at scale | Medium | Batch enrichment. Cache LLM responses. Use cheaper model for extraction. |
| Dedup false positives (merging different jobs) | Medium | Log all dedup decisions. Add manual unmerge API. Conservative similarity threshold. |

### 4.5 Testing

```
┌─────────────────────────────────────────────────────────────────────┐
│  UNIT TESTS (target: 20)                                             │
│  · JobPosting entity: creation, validation                            │
│  · Dedup service: same job → merged, different job → separate        │
│  · SalaryRange VO: valid range, inverted range rejected               │
│  · RemotePolicy enum: valid values                                    │
│  · Canonical job ID generation (deterministic hash)                   │
│                                                                      │
│  INTEGRATION TESTS (target: 12)                                      │
│  · Scrape Greenhouse test page → jobs extracted                       │
│  · Scrape Lever test page → jobs extracted                            │
│  · Dedup: same job from 2 sources → 1 canonical                      │
│  · Enrichment: JD with tech stack → correctly extracted               │
│  · Search: keyword "Python" returns Python jobs                      │
│  · Search: location filter returns only matching jobs                 │
│  · Search: salary_min filter works                                    │
│  · Search: cursor pagination (next page different from first)         │
│  · Vector search: similar jobs share tech stack                       │
│  · GET job detail with expand=company → company embedded              │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.6 Acceptance Criteria

- [ ] 10 sources actively scraping. First sweep produces >500 jobs.
- [ ] Job search returns results for "python engineer" < 300ms
- [ ] Dedup correctly merges identical jobs posted on Greenhouse + LinkedIn
- [ ] Enrichment correctly identifies tech stack for 70%+ of jobs
- [ ] Celery Beat scheduler runs sweeps on schedule without manual intervention
- [ ] Job count visible in DB grows with each sweep

---

## 5. Phase 3: Matching Engine

**Duration:** Week 7 (5 working days)
**Goal:** Match users to jobs with explainable, multi-dimensional scores. This is the core value proposition — if matching is bad, nothing else matters.

### 5.1 Features

- Multi-dimensional match scoring (skills, experience, tech stack, location, compensation)
- Match explanations (why this job matches, what the gaps are)
- Real-time re-ranking from feedback
- Dealbreaker detection
- Match feedback collection

### 5.2 Tasks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WEEK 7                                                                      │
│  ────────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DAY 31–32: Scoring Engine                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ matching/domain/: MatchResult entity, MatchScore VO,               │   │
│  │   MatchDimension VO, MatchExplanation VO                              │   │
│  │ ☐ matching/domain/services/:                                          │   │
│  │   - SkillMatcher (vector similarity on skill embeddings)              │   │
│  │   - ExperienceMatcher (years, title hierarchy, domain relevance)      │   │
│  │   - TechStackOverlap (Jaccard + semantic adjacency)                   │   │
│  │   - LocationFit (region match + remote policy alignment)              │   │
│  │   - CompensationAligner (user min vs job range, ML estimate)          │   │
│  │   - CultureFitEstimator (JD language analysis, lower confidence)      │   │
│  │ ☐ matching/domain/services/: ScoringWeights (profile-driven)          │   │
│  │ ☐ Unit tests for each matcher independently                            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 33: Match API + Explanations                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ matching/application/: commands, queries, handlers                  │   │
│  │ ☐ matching/presentation/:                                             │   │
│  │   - POST /v1/match (compute matches for job_ids or auto-scope)        │   │
│  │   - POST /v1/match/feedback (thumbs up/down, save, dismiss)          │   │
│  │ ☐ LLM-generated explanations (DeepSeek):                              │   │
│  │   - Top 3 reasons this job matches                                     │   │
│  │   - Top 2 concerns/gaps                                                │   │
│  │   - Evidence-grounded (references specific profile facts)             │   │
│  │ ☐ Dealbreaker detection: hard-filter before scoring                   │   │
│  │ ☐ Real-time re-ranking: feedback → weight adjustment in Redis         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 34: Performance Optimization                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Optimize vector search: HNSW ef_search tuning                       │   │
│  │ ☐ Batch match computation for multiple jobs                            │   │
│  │ ☐ Redis caching: user embedding, recent match results                  │   │
│  │ ☐ Response time target: P95 < 2s for batch of 50 jobs                 │   │
│  │ ☐ If too slow: pre-compute match scores during job ingestion           │   │
│  │   (store user embedding → job embedding cosine as baseline)           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 35: Integration & Gate                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ End-to-end: profile → match → verify scores make sense              │   │
│  │ ☐ Manual QA: 10 user profiles × 20 jobs each → verify top-3          │   │
│  │ ☐ Tune scoring weights based on QA feedback                           │   │
│  │ ☐ PHASE GATE REVIEW: Go/No-Go                                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Deliverables

| Deliverable | Acceptance Criteria |
|-------------|-------------------|
| **Match scoring** | 6 dimensions computed per job. Overall score 0–100. |
| **Match explanations** | Natural language reasons for each match. Evidence-grounded. |
| **Match API** | Compute matches for up to 100 jobs. Response < 2s. |
| **Feedback loop** | Thumbs up/down → real-time re-ranking. Preferences updated async. |

### 5.4 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Matching is too slow at scale | Medium | Pre-compute baselines. Cache embeddings aggressively. |
| Match quality is poor (users dismiss good matches) | High | Log all dismissals. Weekly review of dismissed top-10 matches. Tune weights. |
| Compensation alignment inaccurate without listed salary | Low | Flag confidence. Use ML estimate only as supplemental signal. |

### 5.5 Testing

```
┌─────────────────────────────────────────────────────────────────────┐
│  UNIT TESTS (target: 20)                                             │
│  · SkillMatcher: exact match → 1.0, no overlap → 0.0                │
│  · ExperienceMatcher: same title + years → high, junior vs senior → low│
│  · LocationFit: remote user + remote job → 1.0, onsite mismatch → 0.0│
│  · ScoringWeights: user with comp priority → comp weighs more        │
│  · Dealbreaker detection: excluded company → filtered out            │
│  · MatchScore: overall = weighted sum of dimensions                  │
│                                                                      │
│  INTEGRATION TESTS (target: 10)                                      │
│  · Compute match for real profile + real job → score between 0-100   │
│  · Same profile + highly relevant job → score > 70                   │
│  · Same profile + irrelevant job → score < 30                        │
│  · Match with dealbreaker (excluded company) → not in results        │
│  · POST match feedback → subsequent match reflects feedback          │
│  · Match explanations contain specific profile references            │
│  · Batch match 50 jobs → response < 3s                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.6 Acceptance Criteria

- [ ] Match a real profile against 50 real jobs → top 5 are subjectively relevant
- [ ] Match explanation references specific profile skills/experience
- [ ] Dealbreaker (e.g., "no defense industry") actually filters out those jobs
- [ ] Thumbs-down on a match → that job ranks lower in next search
- [ ] Scoring is deterministic (same profile + same jobs = same scores)

---

## 6. Phase 4: Document Generation

**Duration:** Week 8 (5 working days)
**Goal:** Tailor resumes and generate cover letters with zero hallucinations. This is the most visible AI feature — quality here defines the product.

### 6.1 Features

- Job-tailored resume generation with diff view
- ATS keyword optimization
- Honest gap disclosure
- Cover letter generation with company research
- Factuality verification (post-generation check)
- Document export (PDF)

### 6.2 Tasks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WEEK 8                                                                      │
│  ────────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DAY 36–37: Resume Tailoring Engine                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ documents/domain/services/: ResumeTailoringService                  │   │
│  │ ☐ Prompt engineering (the hardest part):                               │   │
│  │   - System prompt: strict no-hallucination rules                       │   │
│  │   - User prompt: profile + job + match analysis                       │   │
│  │   - Structured output: diff format with before/after per section      │   │
│  │ ☐ Tailoring pipeline:                                                  │   │
│  │   1. Analyze JD keywords (LLM + TF-IDF)                                │   │
│  │   2. Map experiences to requirements (vector search over exp chunks)  │   │
│  │   3. Rewrite bullets (LLM, one per call for quality)                   │   │
│  │   4. Reorder skills (rules-based)                                      │   │
│  │   5. Rewrite summary (LLM, 3 variants)                                 │   │
│  │   6. Compute ATS keyword coverage                                      │   │
│  │   7. Identify honest gaps                                              │   │
│  │   8. Run factuality check (LLM: does every bullet trace to profile?)  │   │
│  │ ☐ POST /v1/documents/tailor-resume                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 38: Cover Letter Generation                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ documents/domain/services/: CoverLetterService                       │   │
│  │ ☐ Company research (web search via LLM + scraping):                    │   │
│  │   - Recent news, product launches, tech blog posts                     │   │
│  │   - Culture signals from about page + engineering blog                │   │
│  │ ☐ Letter generation pipeline:                                          │   │
│  │   1. Generate opening (why this company, not generic)                  │   │
│  │   2. Map 3 experiences → 3 body paragraphs (STAR-lite)                 │   │
│  │   3. Generate closing (call to action)                                 │   │
│  │   4. Adapt tone (professional/enthusiastic/concise)                    │   │
│  │   5. Verify factuality (every claim → profile)                         │   │
│  │ ☐ POST /v1/documents/generate-cover-letter                             │   │
│  │ ☐ GET /v1/documents/cover-letters (list)                               │   │
│  │ ☐ GET /v1/documents/cover-letters/{id}                                 │   │
│  │ ☐ PUT /v1/documents/cover-letters/{id} (edit)                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 39: HITL Approval Flow + PDF Rendering                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Acceptance API:                                                     │   │
│  │   - POST /v1/documents/tailor-resume/{id}/accept                      │   │
│  │   - POST /v1/documents/tailor-resume/{id}/reject                      │   │
│  │   - POST /v1/documents/cover-letter/{id}/accept                       │   │
│  │ ☐ PDF rendering for tailored resumes (WeasyPrint / LaTeX)            │   │
│  │ ☐ ATS compatibility check (basic: no tables, columns, images)        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 40: Quality Hardening + Gate                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Run factuality check on 20 generated resumes → must be 100% clean   │   │
│  │ ☐ Manual review: 5 job/combinations, check quality                    │   │
│  │ ☐ Fix hallucination sources found in review                            │   │
│  │ ☐ Token cost optimization: trim prompts, cache JD analyses            │   │
│  │ ☐ PHASE GATE REVIEW: Go/No-Go                                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Deliverables

| Deliverable | Acceptance Criteria |
|-------------|-------------------|
| **Resume tailoring** | Job-specific resume with diff. ATS coverage >70%. Zero hallucinations. |
| **Cover letter** | Personalized, company-specific. Factuality score 100%. |
| **HITL approval** | User reviews diff → accepts or edits → saves as variant |
| **PDF export** | Clean, ATS-readable PDF. Downloads correctly. |

### 6.4 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM hallucinates achievements | Critical | Post-generation factuality check. Strip unverifiable claims. Strict prompt. |
| Tailoring is too slow (>15s) | Medium | Stream response via SSE. Cache JD analyses. Use cheaper model for keyword extraction. |
| Cover letter sounds generic | Medium | Require company research step. Fail if no company-specific content found. |
| ATS PDF rendering broken | Medium | Use simplest possible template. Test against known ATS parsers. |

### 6.5 Testing

```
┌─────────────────────────────────────────────────────────────────────┐
│  UNIT TESTS (target: 15)                                             │
│  · JD keyword extraction: correct keywords identified                 │
│  · Experience mapping: most relevant experience ranked first          │
│  · ATS coverage computation: correct % of JD keywords in resume      │
│  · Factuality checker: flags fabricated achievement                  │
│  · Gap identifier: correctly identifies missing required skill        │
│                                                                      │
│  INTEGRATION TESTS (target: 10)                                      │
│  · Tailor resume for real job → diff shows meaningful changes        │
│  · Tailored resume contains no fabricated metrics                    │
│  · Cover letter references specific company details                  │
│  · Cover letter claims traceable to profile                          │
│  · PDF downloads and opens correctly                                 │
│  · ATS check passes on generated PDF                                 │
│  · Accept → resume variant saved → appears in GET /v1/resumes        │
│  · Reject → resume not saved, feedback logged                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.6 Acceptance Criteria

- [ ] Generate tailored resume for 5 different job types → all factually accurate
- [ ] ATS keyword coverage improves from base resume in all 5 cases
- [ ] Cover letter mentions at least 1 company-specific detail
- [ ] Zero hallucinations across 20 test generations
- [ ] PDF output is clean, single-column, standard fonts
- [ ] Full flow: match → tailor → review diff → accept → download

---

## 7. Phase 5: Application Pipeline

**Duration:** Week 9 (5 working days)
**Goal:** Track every application. Kanban pipeline. Interview prep. Follow-ups. This closes the MVP core loop.

### 7.1 Features

- Application CRUD with status pipeline
- Kanban pipeline view
- Task management (follow-up reminders, deadlines)
- Interview scheduling and prep (questions only)
- Follow-up email generation
- Basic pipeline analytics

### 7.2 Tasks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WEEK 9                                                                      │
│  ────────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DAY 41–42: Application Tracking Core                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Migration: applications, interviews, offers, application_tasks,    │   │
│  │   application_communications, application_documents tables           │   │
│  │ ☐ applications/domain/: Application aggregate (root of               │   │
│  │   Application → Interview → Offer → Task → Communication)            │   │
│  │ ☐ applications/domain/services/: StatusTransitionValidator           │   │
│  │   (state machine: saved→applied→phone_screen→...→offer→accepted)     │   │
│  │ ☐ applications/infrastructure/persistence/: repos + models           │   │
│  │ ☐ applications/presentation/:                                        │   │
│  │   - GET /v1/applications (list + pipeline summary)                   │   │
│  │   - POST /v1/applications (save or apply to job)                     │   │
│  │   - GET /v1/applications/{id} (detail)                               │   │
│  │   - PATCH /v1/applications/{id} (status update, notes)               │   │
│  │   - DELETE /v1/applications/{id} (saved only)                        │   │
│  │   - GET /v1/applications/{id}/tasks                                   │   │
│  │   - POST /v1/applications/{id}/tasks                                  │   │
│  │   - PATCH /v1/applications/{id}/tasks/{task_id}                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 43: Interviews                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ applications/presentation/:                                         │   │
│  │   - GET /v1/applications/{id}/interviews                              │   │
│  │   - POST /v1/applications/{id}/interviews (schedule)                  │   │
│  │   - PATCH /v1/applications/{id}/interviews/{interview_id}             │   │
│  │ ☐ interviews/domain/: InterviewPrep entity, Question VO               │   │
│  │ ☐ Interview prep generation (via LLM):                                │   │
│  │   - POST /v1/interviews/{id}/prep                                     │   │
│  │   - Company brief (1-page summary)                                    │   │
│  │   - Behavioral questions (10–15, with STAR outlines)                  │   │
│  │   - Technical questions (role-specific)                                │   │
│  │   - Questions to ask interviewer (curated)                            │   │
│  │ ☐ Manual prep: user can add notes, custom questions                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 44: Follow-ups & Communications                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ communications/domain/: Communication entity, CommType VO          │   │
│  │ ☐ communications/application/: handlers                               │   │
│  │ ☐ Follow-up generation (via LLM):                                     │   │
│  │   - POST /v1/agent/execute (intent: follow_up)                        │   │
│  │   - Post-application check-in                                          │   │
│  │   - Post-interview thank-you                                           │   │
│  │   - Recruiter response                                                 │   │
│  │ ☐ communications/presentation/:                                        │   │
│  │   - GET /v1/applications/{id}/communications                          │   │
│  │   - POST /v1/applications/{id}/communications (record sent)           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 45: Basic Analytics + Gate                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ GET /v1/analytics/pipeline (funnel, rates, time-in-stage)           │   │
│  │ ☐ Materialized view: user_pipeline_summary (refresh 5 min)            │   │
│  │ ☐ End-to-end test: full flow from match to accepted offer             │   │
│  │ ☐ Manual QA: walk through entire core loop                             │   │
│  │ ☐ PHASE GATE REVIEW: Go/No-Go ← CRITICAL: Core loop complete          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Deliverables

| Deliverable | Acceptance Criteria |
|-------------|-------------------|
| **Application pipeline** | Full CRUD. Status transitions validated. Duplicate prevention. |
| **Kanban summary** | Pipeline counts returned with application list |
| **Interview scheduling** | Schedule, log feedback, track outcomes |
| **Interview prep** | Company brief + behavioral Qs + technical Qs + questions-to-ask |
| **Follow-up emails** | Generated from templates. Reviewed before send. |
| **Pipeline analytics** | Funnel, rates, time-in-stage, source breakdown |

### 7.4 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Status transition complexity | Medium | Hardcode transition matrix. Validate server-side only. |
| Interview prep questions are repetitive | Low | Track previously shown questions per user. Regenerate on demand. |

### 7.5 Testing

```
┌─────────────────────────────────────────────────────────────────────┐
│  UNIT TESTS (target: 15)                                             │
│  · StatusTransitionValidator: all valid transitions pass             │
│  · StatusTransitionValidator: invalid transitions rejected           │
│  · Application entity: cannot apply without resume                   │
│  · Interview prep: STAR outline contains profile facts               │
│                                                                      │
│  INTEGRATION TESTS (target: 12)                                      │
│  · Create saved application → 201                                    │
│  · Create duplicate application → 409                                │
│  · Apply with resume → status = applied                             │
│  · Invalid status transition → 400                                  │
│  · Schedule interview → prep materials generated                    │
│  · Record interview feedback → outcome saved                        │
│  · Generate follow-up → draft created, not sent                      │
│  · Accept offer → status = accepted, pipeline updated               │
│  · Pipeline analytics returns correct funnel counts                  │
│                                                                      │
│  E2E TEST (target: 1)                                                │
│  · Full flow: register → upload resume → discover jobs → match →    │
│    tailor resume → generate CL → apply → track → interview →        │
│    follow-up → offer → accept                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.6 Acceptance Criteria

- [ ] User can save a job, apply with tailored resume, and track status
- [ ] Invalid status transitions are rejected with clear errors
- [ ] Interview prep generates relevant questions for the role + company
- [ ] Follow-up email draft is personalized and factually accurate
- [ ] Pipeline analytics shows correct counts for each stage
- [ ] Full end-to-end flow completes without errors

---

## 8. Phase 6: Agent Orchestration

**Duration:** Week 10–11 (10 working days)
**Goal:** Wire the LangGraph agent system. Instead of calling individual services, the user talks to a single agent endpoint that routes intents, orchestrates multi-step tasks, and manages HITL approvals.

### 8.1 Features

- Supervisor Agent (LangGraph StateGraph)
- Intent routing (natural language → agent dispatch)
- Context assembly (Memory Agent integration)
- Multi-step task planning
- Human-in-the-loop approval gates
- SSE streaming responses
- Agent execution audit logging
- 5 specialized agent subgraphs (Profile, Matching, Resume, CoverLetter, Interview)

### 8.2 Tasks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WEEK 10                                                                     │
│  ────────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DAY 46–47: LangGraph Setup + Supervisor                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ LangGraph installation + PostgresSaver checkpointer setup           │   │
│  │ ☐ Define SupervisorState (TypedDict)                                  │   │
│  │ ☐ Implement Supervisor nodes:                                         │   │
│  │   1. Guardrail node (content safety, rate limit, tier check)          │   │
│  │   2. Context builder node (calls MemoryAgent)                         │   │
│  │   3. Intent router node (LLM classification → intent)                 │   │
│  │   4. Task planner node (decompose intent → execution plan)            │   │
│  │   5. Agent dispatcher node (invoke specialized agent subgraphs)       │   │
│  │   6. Result synthesizer node (merge + format)                         │   │
│  │   7. Quality gate node (factuality, tone, completeness)               │   │
│  │ ☐ Conditional edges: intent confidence < 0.7 → ask clarifying         │   │
│  │   question. Quality gate fail → revise or degrade gracefully.         │   │
│  │ ☐ Compile graph with checkpointer                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 48–49: Specialized Agent Subgraphs                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Profile Agent subgraph:                                             │   │
│  │   - parse_resume tool, enrich_profile tool, embed_profile tool        │   │
│  │ ☐ Matching Agent subgraph:                                            │   │
│  │   - compute_match tool, explain_match tool, search_jobs tool          │   │
│  │ ☐ Resume Agent subgraph:                                              │   │
│  │   - tailor_resume tool, check_ats tool, render_pdf tool               │   │
│  │ ☐ Cover Letter Agent subgraph:                                        │   │
│  │   - research_company tool, generate_letter tool, verify_facts tool    │   │
│  │ ☐ Interview Agent subgraph:                                           │   │
│  │   - generate_questions tool, company_brief tool                       │   │
│  │ ☐ Each agent: state schema, system prompt, tool definitions,          │   │
│  │   LLM node(s), tool-execution node(s)                                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 50: Memory Agent + Context Assembly                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Memory Agent (core of the moat):                                    │   │
│  │   - store_episode tool (append-only write)                            │   │
│  │   - retrieve_context tool (assembles context package)                 │   │
│  │   - search_semantic tool (vector search over user memories)           │   │
│  │   - update_preferences tool (Bayesian weight update)                  │   │
│  │ ☐ Context assembly: full profile + preferences + recent episodes      │   │
│  │   + relevant semantic memories, all within token budget               │   │
│  │ ☐ Episodic memory: logged on every agent invocation                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  WEEK 11                                                                     │
│  ────────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DAY 51–52: Agent API + SSE Streaming                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ POST /v1/agent/execute (main entry point)                           │   │
│  │   - Accepts: intent + message + context + options                     │   │
│  │   - Returns: execution_id + response + artifacts + pending_approval   │   │
│  │ ☐ SSE streaming: event types (status, token, artifact, done)          │   │
│  │ ☐ POST /v1/agent/approvals/{id} (HITL response)                       │   │
│  │ ☐ GET /v1/agent/executions (history)                                   │   │
│  │ ☐ GET /v1/agent/executions/{id} (detail)                               │   │
│  │ ☐ POST /v1/agent/feedback (rating for continuous improvement)         │   │
│  │ ☐ Circuit breaker implementation (LLM error rate > 5% → open)         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 53–54: HITL Workflow + Task Orchestration                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ HITL gates: pause agent execution, save checkpoint, wait for user   │   │
│  │ ☐ Approval request: diff view for resume/CL, preview for emails       │   │
│  │ ☐ Resume on approval (LangGraph interrupt → resume)                   │   │
│  │ ☐ Multi-step task orchestration:                                      │   │
│  │   - "Find me jobs at Stripe and tailor my resume for the top one"     │   │
│  │   - Supervisor plans: search jobs → match → tailor → present          │   │
│  │   - Executes sequentially, checkpoints between steps                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 55: Agent Integration Testing + Gate                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Test all 11 intents via POST /v1/agent/execute                       │   │
│  │ ☐ Test multi-step orchestration (2-step and 3-step plans)              │   │
│  │ ☐ Test HITL: approve, reject, edit, timeout                            │   │
│  │ ☐ Test circuit breaker: simulate LLM failures → graceful degradation  │   │
│  │ ☐ Test checkpointing: kill agent mid-execution → resume from checkpoint│   │
│  │ ☐ PHASE GATE REVIEW: Go/No-Go                                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Deliverables

| Deliverable | Acceptance Criteria |
|-------------|-------------------|
| **Supervisor Agent** | 7-node StateGraph. Routes 11 intents. Checkpoints after each node. |
| **5 Specialized Agents** | Profile, Matching, Resume, CoverLetter, Interview agents operational |
| **Memory Agent** | Episodic logging on every invocation. Context assembly within token budget. |
| **Agent API** | Single endpoint for all intents. SSE streaming. HITL approval flow. |
| **Multi-step plans** | Automatically decompose and execute multi-step user requests |

### 8.4 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| LangGraph learning curve | Medium | Start with simple linear graphs. Add complexity incrementally. |
| Intent classification accuracy | High | Log all classifications. Track confidence. Implement clarification flow for <0.7. |
| Agent execution timeouts for multi-step | Medium | Set per-step timeouts (30s). Cancel remaining steps on timeout. |
| Checkpoint storage grows unbounded | Low | TTL on checkpoints (30 days for incomplete sessions). |

### 8.5 Testing

```
┌─────────────────────────────────────────────────────────────────────┐
│  UNIT TESTS (target: 15)                                             │
│  · Intent router: "tailor my resume" → tailor_resume                 │
│  · Intent router: ambiguous → confidence < 0.7                       │
│  · Task planner: single intent → single-step plan                    │
│  · Task planner: "find jobs and tailor" → 3-step plan                 │
│  · Guardrail: blocked content → BLOCK                                │
│  · Quality gate: incomplete response → REVISE                        │
│                                                                      │
│  INTEGRATION TESTS (target: 12)                                      │
│  · POST /v1/agent/execute (tailor_resume) → tailored resume returned │
│  · POST /v1/agent/execute (match_me) → match list returned           │
│  · SSE streaming: events arrive in order                             │
│  · HITL: resume tailoring pauses for approval                        │
│  · HITL: approve → resume saved                                      │
│  · HITL: reject → feedback logged, agent stops                       │
│  · Multi-step: "find fintech jobs" → search + match                   │
│  · Multi-step: "tailor for Stripe" → match + tailor                  │
│  · Circuit breaker: LLM failures → fallback model                    │
│  · Checkpoint: kill mid-execution → resume → completes               │
└─────────────────────────────────────────────────────────────────────┘
```

### 8.6 Acceptance Criteria

- [ ] All 11 intents work via single POST /v1/agent/execute endpoint
- [ ] SSE streaming shows token-by-token output for long generations
- [ ] Multi-step request "Find Python jobs and tailor my resume for the best one" completes end-to-end
- [ ] HITL approval pauses execution until user responds (test with >5 min wait)
- [ ] Agent works after server restart (checkpoint recovery)
- [ ] Circuit breaker opens after 5 consecutive LLM failures → graceful degradation message

---

## 9. Phase 7: Production Hardening

**Duration:** Week 12 (5 working days)
**Goal:** Ship it. Tests, monitoring, deployment, documentation, polish. Everything needed to put real users on the system.

### 9.1 Features

- Comprehensive test coverage
- Production deployment (VM / fly.io / Railway)
- Monitoring and alerting
- Documentation (API docs, setup guide)
- Performance optimization
- Security hardening
- Bug fixes from integration testing

### 9.2 Tasks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WEEK 12                                                                     │
│  ────────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DAY 56–57: Test Coverage Push                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Achieve >80% unit test coverage on domain layer                     │   │
│  │ ☐ Achieve >60% integration test coverage on API endpoints             │   │
│  │ ☐ Add edge case tests: empty profile, no jobs found, LLM timeout      │   │
│  │ ☐ Load test: 100 concurrent users searching jobs (locust/k6)          │   │
│  │ ☐ Fix performance bottlenecks found in load testing                   │   │
│  │ ☐ Rate limit tests: verify limits enforced per tier                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 58: Production Deployment                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Provision PostgreSQL (managed: RDS / Supabase / Railway)            │   │
│  │ ☐ Provision Redis (managed: ElastiCache / Upstash / Railway)          │   │
│  │ ☐ Deploy Docker container (fly.io / Railway / Hetzner + Coolify)     │   │
│  │ ☐ Configure custom domain + SSL (Cloudflare)                          │   │
│  │ ☐ Set up environment secrets (DB URL, Redis URL, API keys)            │   │
│  │ ☐ Run production migrations (Alembic upgrade head)                    │   │
│  │ ☐ Verify: health endpoint, auth flow, core features on production     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 59: Monitoring & Alerting                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Sentry error tracking (all exceptions → Sentry)                     │   │
│  │ ☐ Prometheus metrics: request rate, latency, error rate, LLM costs    │   │
│  │ ☐ Grafana dashboard: API health, agent performance, job pipeline      │   │
│  │ ☐ Uptime monitoring (UptimeRobot / BetterStack)                       │   │
│  │ ☐ Alerts: error rate >5%, P95 latency >5s, LLM cost spike, DB down   │   │
│  │ ☐ Log aggregation (CloudWatch / Grafana Loki)                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DAY 60: Documentation + Polish                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ API documentation: full OpenAPI spec deployed (Swagger UI)          │   │
│  │ ☐ README: updated with production architecture                        │   │
│  │ ☐ Deployment runbook: how to deploy, rollback, debug                  │   │
│  │ ☐ User onboarding guide: first-time user flow                         │   │
│  │ ☐ Security audit: OWASP top-10 check, dependency scan, secret scan    │   │
│  │ ☐ Performance optimization pass: slow queries, large payloads         │   │
│  │ ☐ Final bug bash: manual end-to-end testing of all flows              │   │
│  │ ☐ TAG RELEASE: v0.1.0-mvp                                             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.3 Deliverables

| Deliverable | Acceptance Criteria |
|-------------|-------------------|
| **Test coverage** | Domain >80%. API integration >60%. All critical paths covered. |
| **Production deployment** | App accessible at https://api.pathfinder.com. All features working. |
| **Monitoring** | Sentry + Prometheus + Grafana operational. Alerts configured. |
| **Documentation** | Swagger UI complete. README updated. Deployment runbook written. |
| **MVP release** | v0.1.0-mvp tagged. Ready for alpha users. |

### 9.4 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Production config issues (secrets, networking) | High | Deploy to staging first. Identical config to prod. |
| LLM cost surprise at production load | Medium | Set hard cost limits. Monitor per-user and aggregate costs. |
| Security vulnerability found late | High | Dependency scan in CI. OWASP check. Secrets never in code. |

### 9.5 Testing

```
┌─────────────────────────────────────────────────────────────────────┐
│  LOAD TESTS                                                         │
│  · 100 concurrent users searching jobs → P95 < 500ms                │
│  · 50 concurrent resume generations → queue processes without crash │
│  · Sustained 10 req/s for 1 hour → no memory leak                   │
│                                                                      │
│  SECURITY TESTS                                                      │
│  · SQL injection attempts on all search endpoints                   │
│  · XSS in user input fields                                          │
│  · Unauthenticated access to protected endpoints                     │
│  · JWT tampering → rejected                                         │
│  · Rate limit enforcement across all endpoints                       │
│                                                                      │
│  RESILIENCE TESTS                                                    │
│  · Kill PostgreSQL → health check reflects, API degrades gracefully │
│  · Kill Redis → cache misses, session state lost, API still works   │
│  · DeepSeek timeout → fallback to OpenAI (if configured)            │
│  · DeepSeek + OpenAI down → circuit breaker → graceful degradation  │
└─────────────────────────────────────────────────────────────────────┘
```

### 9.6 Acceptance Criteria

- [ ] Production deployment passes all smoke tests
- [ ] All CI checks green on main branch
- [ ] Test coverage meets targets (domain >80%, integration >60%)
- [ ] Load test: system handles 100 concurrent users without errors
- [ ] Security scan: zero critical or high vulnerabilities
- [ ] All alerts configured and test-fired successfully
- [ ] Documentation complete and accurate
- [ ] `v0.1.0-mvp` tagged and deployable from a single command

---

## 10. Risk Register

### 10.1 Top 10 Risks Across All Phases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  # │ RISK                           │ SEV │ LIKE │ MITIGATION                │
│  ──┼───────────────────────────────┼─────┼──────┼───────────────────────── │
│  1 │ DeepSeek API quality degrades  │ CRIT│ MED  │ Multi-model fallback.     │
│    │ or has extended outage         │     │      │ Weekly eval of outputs.    │
│    │                                │     │      │                           │
│  2 │ Resume/CL hallucination        │ CRIT│ MED  │ Post-gen factuality check. │
│    │ damages user trust             │     │      │ Strict grounding prompt.   │
│    │                                │     │      │ User must review before    │
│    │                                │     │      │ sending.                  │
│    │                                │     │      │                           │
│  3 │ Job sources block scraping     │ HIGH│ HIGH │ Rotate IPs. Respect        │
│    │                                │     │      │ robots.txt. LLM fallback   │
│    │                                │     │      │ parser for HTML changes.   │
│    │                                │     │      │                           │
│  4 │ Matching quality is poor —     │ HIGH│ MED  │ Weekly human eval of top   │
│    │ users don't trust scores       │     │      │ matches. User feedback     │
│    │                                │     │      │ loop. Continuous tuning.   │
│    │                                │     │      │                           │
│  5 │ LLM costs exceed budget at     │ HIGH│ MED  │ Tier-based token limits.   │
│    │ scale                          │     │      │ Cache aggressively. Use     │
│    │                                │     │      │ cheaper models for classif-│
│    │                                │     │      │ ication. Monitor per-user. │
│    │                                │     │      │                           │
│  6 │ Solo dev burnout / illness     │ HIGH│ LOW  │ Realistic timeline. No     │
│    │                                │     │      │ crunch. Buffer days built  │
│    │                                │     │      │ into each phase.           │
│    │                                │     │      │                           │
│  7 │ PostgreSQL performance         │ MED │ MED  │ Index optimization in      │
│    │ degrades with scale            │     │      │ Phase 7. Connection pooling.│
│    │                                │     │      │ Read replicas if needed.   │
│    │                                │     │      │                           │
│  8 │ LangGraph complexity blocks    │ MED │ LOW  │ Start simple. Linear graphs│
│    │ progress                       │     │      │ first. Add branching later. │
│    │                                │     │      │ Good docs exist.           │
│    │                                │     │      │                           │
│  9 │ Security vulnerability in      │ MED │ LOW  │ Dependency scanning in CI. │
│    │ dependencies                   │     │      │ Regular updates. Secrets    │
│    │                                │     │      │ never in code.             │
│    │                                │     │      │                           │
│ 10 │ User data privacy issue        │ HIGH│ LOW  │ Field-level encryption.    │
│    │ (GDPR/CCPA)                    │     │      │ Data export + deletion API. │
│    │                                │     │      │ LLM data processing agree-  │
│    │                                │     │      │ ments.                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Weekly Burn-Down Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WEEK │ PHASE        │ GOAL                           │ KEY DELIVERABLE      │
│  ────┼──────────────┼───────────────────────────────┼───────────────────── │
│   1   │ 0: Foundation │ Project scaffolds. Auth done.  │ Docker Compose up.    │
│       │              │ CI/CD green.                   │ Auth API working.     │
│   2   │ 0: Foundation │ DB migrated. Config done.      │ Health check. CI.     │
│       │              │ Staging deployed.               │ Deployed to staging.  │
│  ────┼──────────────┼───────────────────────────────┼───────────────────── │
│   3   │ 1: Profile   │ Resume parsing works.          │ Upload → structured   │
│       │              │ Profile CRUD done.              │ profile.              │
│   4   │ 1: Profile   │ Resumes + Prefs complete.      │ PDF download. Prefs   │
│       │              │ Phase 1 demo-able.              │ with version history. │
│  ────┼──────────────┼───────────────────────────────┼───────────────────── │
│   5   │ 2: Jobs      │ 10 scrapers running.            │ Jobs flowing into DB. │
│       │              │ Dedup working.                  │ Canonical listings.   │
│   6   │ 2: Jobs      │ Enrichment + Search done.       │ Search API. Celery    │
│       │              │ Background sweeps running.      │ Beat operational.     │
│  ────┼──────────────┼───────────────────────────────┼───────────────────── │
│   7   │ 3: Matching  │ 6-dimension scoring.            │ Match API with        │
│       │              │ Explanations generated.         │ explanations.         │
│  ────┼──────────────┼───────────────────────────────┼───────────────────── │
│   8   │ 4: Documents │ Resume tailoring + CL done.     │ Zero-hallucination    │
│       │              │ Factuality verified.            │ generation.           │
│  ────┼──────────────┼───────────────────────────────┼───────────────────── │
│   9   │ 5: Pipeline  │ Apps + Interviews + Follow-ups. │ Core loop closed.     │
│       │              │ Pipeline analytics.             │ Full flow demo.       │
│  ────┼──────────────┼───────────────────────────────┼───────────────────── │
│  10   │ 6: Agents    │ LangGraph Supervisor + 5        │ Agent API with SSE.   │
│       │              │ subgraphs. Intent routing.      │ Single endpoint.      │
│  11   │ 6: Agents    │ HITL + multi-step plans.        │ Complex orchestrations│
│       │              │ Memory Agent integrated.        │ working.              │
│  ────┼──────────────┼───────────────────────────────┼───────────────────── │
│  12   │ 7: Hardening │ Tests, monitoring, prod deploy. │ v0.1.0-mvp shipped.   │
│       │              │ Docs, security, polish.         │ Ready for alpha.      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

> *"The only thing that matters is shipping working software that users love. Everything else is a distraction. Ship every Friday. Learn every week. Keep moving forward."*

**End of Implementation Plan**
