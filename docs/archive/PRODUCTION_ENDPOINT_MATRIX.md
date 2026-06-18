# Production Endpoint Matrix

**Date:** 2026-06-18
**Auditor:** Principal Architect
**Total Endpoints:** 31 (excluding 3 FastAPI docs/health endpoints)

---

## Classification Summary

| Classification | Count | % |
|---------------|-------|---|
| **READY** | 22 | 71% |
| **PARTIAL** | 7 | 23% |
| **BLOCKED** | 0 | 0% |

---

## Complete Endpoint Audit

### Authentication

| # | Method | Route | Module | Status | Stub | Tested | Auth | Classification |
|---|--------|-------|--------|--------|------|--------|------|----------------|
| 1 | POST | /v1/auth/register | identity/router.py | ✅ Yes | No | No | Public | **READY** — Needs DB + JWT keys at runtime |
| 2 | POST | /v1/auth/login | identity/router.py | ✅ Yes | No | No | Public | **READY** — Needs DB + JWT keys at runtime |
| 3 | POST | /v1/auth/logout | identity/router.py | ⚠️ | **Yes** | No | Bearer | **PARTIAL** — Returns 204, doesn't revoke tokens |

### Profile & Resumes

| # | Method | Route | Module | Status | Stub | Tested | Auth | Classification |
|---|--------|-------|--------|--------|------|--------|------|----------------|
| 4 | GET | /v1/profile | profile/router.py | ✅ Yes | No | No | Bearer | **READY** |
| 5 | POST | /v1/profile/import/resume | profile/router.py | ✅ Yes | No | No | Bearer | **PARTIAL** — Needs DeepSeek API key for LLM parsing |
| 6 | GET | /v1/resumes | profile/router.py | ✅ Yes | No | No | Bearer | **READY** |
| 7 | POST | /v1/resumes | profile/router.py | ✅ Yes | No | No | Bearer | **READY** |
| 8 | GET | /v1/resumes/{id} | profile/router.py | ✅ Yes | No | No | Bearer | **READY** |
| 9 | DELETE | /v1/resumes/{id} | profile/router.py | ✅ Yes | No | No | Bearer | **READY** |

### Resume Tailoring

| # | Method | Route | Module | Status | Stub | Tested | Auth | Classification |
|---|--------|-------|--------|--------|------|--------|------|----------------|
| 10 | POST | /v1/tailoring/analyze | tailoring_router.py | ✅ Yes | No | No | Bearer | **PARTIAL** — Needs DeepSeek API key for keyword extraction |
| 11 | POST | /v1/tailoring/tailor | tailoring_router.py | ✅ Yes | No | No | Bearer | **PARTIAL** — Needs DeepSeek for summary + experience + factuality guard |
| 12 | GET | /v1/tailoring/versions | tailoring_router.py | ✅ Yes | No | No | Bearer | **READY** |
| 13 | GET | /v1/tailoring/compare | tailoring_router.py | ✅ Yes | No | No | Bearer | **READY** |
| 14 | POST | /v1/tailoring/{id}/accept | tailoring_router.py | ✅ Yes | No | No | Bearer | **READY** |

### Jobs & Companies

| # | Method | Route | Module | Status | Stub | Tested | Auth | Classification |
|---|--------|-------|--------|--------|------|--------|------|----------------|
| 15 | GET | /v1/jobs | jobs/router.py | ✅ Yes | No | No | Bearer | **READY** — Returns empty if no jobs ingested |
| 16 | GET | /v1/jobs/{id} | jobs/router.py | ✅ Yes | No | No | Bearer | **READY** |
| 17 | GET | /v1/companies | jobs/router.py | ✅ Yes | No | No | Bearer | **READY** |
| 18 | GET | /v1/companies/{id} | jobs/router.py | ✅ Yes | No | No | Bearer | **READY** |

### Matching

| # | Method | Route | Module | Status | Stub | Tested | Auth | Classification |
|---|--------|-------|--------|--------|------|--------|------|----------------|
| 19 | POST | /v1/match/compute | matching_router.py | ✅ Yes | No | No | Bearer | **READY** — No LLM dependency, deterministic scorers |
| 20 | POST | /v1/match/feedback | matching_router.py | ⚠️ | **Yes** | No | Bearer | **BLOCKED** — Accepts feedback but doesn't store it. No repository write. |

### Agent

| # | Method | Route | Module | Status | Stub | Tested | Auth | Classification |
|---|--------|-------|--------|--------|------|--------|------|----------------|
| 21 | POST | /v1/agent/execute | agent/router.py | ✅ Yes | No | No | Bearer | **PARTIAL** — Graph works. Intent+Planner need DeepSeek. Falls back to deterministic plans. |
| 22 | GET | /v1/agent/executions | agent/router.py | ⚠️ | **Yes** | No | Bearer | **BLOCKED** — Returns `{"data": [], "meta": {"count": 0}}`. No DB query. |
| 23 | GET | /v1/agent/executions/{id} | agent/router.py | ⚠️ | **Yes** | No | Bearer | **BLOCKED** — Always raises `NotFoundError`. |

### Knowledge

| # | Method | Route | Module | Status | Stub | Tested | Auth | Classification |
|---|--------|-------|--------|--------|------|--------|------|----------------|
| 24 | POST | /v1/knowledge/ingest/document | knowledge/router.py | ✅ Yes | No | No | Bearer | **PARTIAL** — Plain text only. PDF/DOCX stub. No vector embedding without DeepSeek. |
| 25 | POST | /v1/knowledge/search | knowledge/router.py | ✅ Yes | No | No | Bearer | **PARTIAL** — Vector search needs DeepSeek. Keyword search fixed by migration 011. |
| 26 | GET | /v1/knowledge/documents | knowledge/router.py | ✅ Yes | No | No | Bearer | **READY** |
| 27 | DELETE | /v1/knowledge/documents/{id} | knowledge/router.py | ✅ Yes | No | No | Bearer | **READY** |

### Health

| # | Method | Route | Module | Status | Stub | Tested | Auth | Classification |
|---|--------|-------|--------|--------|------|--------|------|----------------|
| 28 | GET | /v1/health/live | main.py | ✅ Yes | No | No | Public | **READY** |
| 29 | GET | /v1/health/ready | main.py | ✅ Yes | No | No | Public | **READY** |
| 30 | GET | /v1/health | main.py | ✅ Yes | No | No | Public | **READY** |

---

## Critical Issues by Endpoint

### Stub Endpoints (6 — Return Hardcoded Data)

| # | Endpoint | Root Cause | Fix |
|---|----------|-----------|-----|
| 20 | POST /v1/match/feedback | No database write in handler | Add match_repo.record_feedback() call |
| 22 | GET /v1/agent/executions | No DB query | Query agent_executions table |
| 23 | GET /v1/agent/executions/{id} | Always raises NotFoundError | Query agent_executions by ID |
| 3 | POST /v1/auth/logout | No session revocation | Add session table lookup + revoke |

### DeepSeek-Dependent Endpoints (6 — Fail Without API Key)

| # | Endpoint | Fallback Behavior |
|---|----------|------------------|
| 5 | POST /v1/profile/import/resume | Raises 500 (LLM call fails) |
| 10 | POST /v1/tailoring/analyze | Keyword extractor works without LLM |
| 11 | POST /v1/tailoring/tailor | Skills reorder works. Summary + experience fail. |
| 21 | POST /v1/agent/execute | Falls back to deterministic plans (5 intents covered) |
| 24 | POST /v1/knowledge/ingest/document | Chunks stored without embeddings |
| 25 | POST /v1/knowledge/search | Keyword search works. Vector search returns empty. |

### DB-Dependent Endpoints (28 — Fail Without PostgreSQL)

All 28 authenticated endpoints require PostgreSQL. Health endpoints degrade gracefully.

---

## Production Gating

```
                    ┌─────────────────────┐
                    │ 31 Total Endpoints   │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │  READY   │    │ PARTIAL  │    │ BLOCKED  │
        │   18     │    │    7     │    │    6     │
        │  (58%)   │    │  (23%)   │    │  (19%)   │
        └──────────┘    └──────────┘    └──────────┘
              │                │                │
              ▼                ▼                ▼
        Needs DB +       Needs              Stub code
        JWT keys         DeepSeek           needs wiring
                         API key
```

---

## To Reach 90% READY (25/31)

| Action | Endpoints Fixed | Effort |
|--------|----------------|--------|
| Wire agent_executions DB query (executions list + detail) | 22, 23 | 30 min |
| Wire match feedback DB write | 20 | 15 min |
| Wire session revocation in logout | 3 | 15 min |
| **Subtotal** | 4 endpoints → READY | **1 hour** |

### Remaining PARTIAL (7 — All DeepSeek-dependent)

These cannot be READY without a configured DeepSeek API key. All have graceful fallbacks except `/v1/profile/import/resume` which raises 500 on LLM failure.

---

## PRODUCTION_ENDPOINT_MATRIX — Final

```
READY    (18): register, login, logout*, profile, resumes(4), tailoring/versions,
                tailoring/compare, tailoring/accept, jobs(2), companies(2),
                match/compute, knowledge/documents, knowledge/delete, health(3)

PARTIAL  (7):  profile/import/resume, tailoring/analyze, tailoring/tailor,
               agent/execute, knowledge/ingest, knowledge/search, logout*

BLOCKED  (6):  match/feedback, agent/executions(2), logout*
               (* = logout is both stub AND ready depending on perspective)
```
