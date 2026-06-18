# Sprint 4 — Principal Engineer Architecture Review

**Review Date:** 2026-06-18
**Reviewer:** Principal Engineer
**Sprint Reviewed:** Sprint 4 — Job Discovery Domain
**Documents Audited:** SPRINT_4.md (full implementation)
**Classification:** Confidential — Internal

---

## Verdict: CONDITIONALLY APPROVED — 3 Critical Issues Must Be Fixed Before Production Use

The Sprint 4 implementation is well-structured and follows Clean Architecture and DDD principles admirably. The pluggable source framework, normalization pipeline, and deduplication logic are solid. However, three critical bugs would cause production failures, and several important gaps must be addressed before Sprint 5.

---

## Critical Issues (Block Production)

### CRIT-1: `session.get()` Called With Non-Primary-Key Value (Lines 1764, 1812)

**Location:** `src/pathfinder/agent/infrastructure/celery_tasks/scraping.py`

```python
source_model = await session.get(JobSourceModel, source.source_name)
```

**Problem:** `SQLAlchemy Session.get()` requires the primary key of the entity. `JobSourceModel` has `id: UUID` as its primary key, but the code passes `source.source_name` (a string). This will silently fail — `session.get()` returns `None` for any value that doesn't match the PK type. Every sweep will skip source stat updates.

**Fix:** Use a select query:
```python
stmt = select(JobSourceModel).where(JobSourceModel.name == source.source_name)
result = await session.execute(stmt)
source_model = result.scalar_one_or_none()
```

### CRIT-2: Race Condition in `get_or_create` (Line 1653–1660)

**Location:** `src/pathfinder/jobs/infrastructure/persistence/company_repository.py`

**Problem:** Two concurrent celery workers (e.g., Greenhouse scraping Stripe and YC also scraping Stripe) both call `get_or_create("Stripe")`. Both find no existing company, both create one. The second `save()` hits a `UNIQUE CONSTRAINT VIOLATION` on `canonical_name`.

**Fix:**
```python
async def get_or_create(self, name: str) -> Company:
    canonical = name.strip().lower()
    existing = await self.get_by_canonical_name(canonical)
    if existing:
        return existing
    company = Company.create(name=name.strip())
    try:
        await self.save(company)
        await self._session.flush()
        return company
    except IntegrityError:
        await self._session.rollback()
        # Another worker created it — fetch again
        return await self.get_by_canonical_name(canonical)
```

### CRIT-3: Null Reference in `_job_to_response` (Lines 1977–1979)

**Location:** `src/pathfinder/jobs/presentation/router.py`

```python
"salary_range": {
    "min": j.salary_range.min_amount, "max": j.salary_range.max_amount,
    "currency": j.salary_range.currency,
} if j.salary_range else None,
```

**Problem:** When `j.salary_range` is `None`, this correctly returns `None`. But when the `SalaryRange` object exists and `min_amount` or `max_amount` are `None` (which is valid per the value object design — either field can be null), the response will contain `"min": null` which is fine. HOWEVER — if a job has `salary_range` set but `max_amount` is None, the downstream consumers (frontend in V1) may crash expecting a number. Not a crash in the API itself, but a data contract issue.

**Verdict:** Downgraded to MAJOR — the null-safety is correct. The issue is contract ambiguity with partially populated salary data.

---

## Major Issues (Fix Before Sprint 5 Merge)

### MAJ-1: Cursor Pagination Not Implemented Despite Interface Contract

**Location:** `SqlJobRepository.search()` (line 1520) and `SqlCompanyRepository.search()` (line 1662)

**Problem:** Both `search()` methods accept a `cursor` parameter but never use it. The repository interface contract promises cursor-based pagination. The API response includes `cursor_next` but the value is always the last item's ID — not a proper encoded cursor. This means:
- Clients cannot reliably paginate (no stable cursor token)
- Results shift under pagination (offset drift)
- The interface lies about its capabilities

**Fix:** Implement opaque cursor tokens. Store the last-seen sort value + ID in a base64-encoded JSON token. On the next page, filter: `WHERE (sort_col, id) > (last_sort_val, last_id)`.

### MAJ-2: HN Scraper Performance — 7-Minute Sweep Time

**Location:** `HackerNewsScraper.sweep()` — 200 sequential API calls at 0.5 req/s (lines 918–937)

**Problem:** The HN scraper fetches up to 200 comments individually from the Firebase API. At 0.5 req/s (2-second delay per request), a full sweep takes 400 seconds = 6.7 minutes. This blocks the scraping worker for the entire duration. Meanwhile, the Greenhouse and YC scrapers finish in <30 seconds.

**Fix for MVP:** Reduce comment limit from 200 to 50. Increase rate to 1 req/s by using a separate API key or accepting the HN rate limit.
**Fix for V1:** Use the Algolia search API to find individual job posts rather than crawling the thread. Or batch-comment fetches using the `items` endpoint.

### MAJ-3: No Job Embedding Generation

**Location:** Missing from the entire implementation.

**Problem:** `JobPostingModel.job_embedding` is created as a `VECTOR(3072)` column with an HNSW index, but no code generates embeddings. `find_similar()` (line 1583) checks `job.job_embedding is None` and returns an empty list. Until embeddings are populated:
- Vector similarity search returns nothing
- The "Similar Jobs" API endpoint always returns `[]`
- The HNSW index exists but is empty

**Fix:** Add a Celery task `embed_job` that calls the DeepSeek embedding API and stores the result. Trigger it after job enrichment. Defer actual embedding generation to Sprint 5 (Matching Engine) since the embedding client already exists in Sprint 3's `DeepSeekClient`. Acknowledge this gap explicitly.

### MAJ-4: No Full-Text Search Index on `description_clean`

**Location:** `SqlJobRepository.search()` (line 1528–1534) uses `to_tsvector('english', description_clean)` at query time.

**Problem:** Without a GIN index on a pre-computed tsvector column, full-text search performs a sequential scan over `description_clean`, computing tsvector on every row. With 100K+ jobs, search latency will degrade beyond the 300ms target.

**Fix:** Add a migration creating a generated tsvector column and a GIN index:
```sql
ALTER TABLE job_postings ADD COLUMN description_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(description_clean, ''))) STORED;
CREATE INDEX idx_jobs_tsv ON job_postings USING GIN (description_tsv);
```
Update the search query to use `description_tsv @@ ts_query` instead of computing tsvector at query time.

### MAJ-5: Celery Task Database Session Handling

**Location:** `_sweep_all_sources_async()` (lines 1729–1797)

**Problem:** The entire sweep of all 3 sources happens in a single database transaction. If any operation fails:
- The `commit()` at line 1794 commits partial work
- OR the exception causes a rollback losing ALL new jobs from all sources
- There's no per-source transaction boundary

Additionally, the `sessionmaker` is created fresh via `get_sessionmaker()` but the engine must already be initialized. If this Celery task runs before the FastAPI app initializes the engine, it will fail.

**Fix:** Commit per source (after each source's jobs are processed). Use nested transactions for individual job operations. Ensure the engine is initialized in the Celery worker startup.

---

## Minor Issues

### MIN-1: Global Singleton `source_registry`

**Location:** `src/pathfinder/jobs/infrastructure/scraping/source_registry.py` (line 586)

**Problem:** The `source_registry = SourceRegistry()` global singleton means:
- Every Celery worker process has its own copy
- Sources must be re-registered per process (`_register_sources()` called on every sweep)
- Cannot mock or test with different source sets
- Violates dependency inversion (infrastructure is globally depended upon)

**Fix:** Pass the registry as a dependency to the Celery task, or use a factory function instead of a module-level singleton. Acceptable for MVP given the Celery worker pattern.

### MIN-2: `_register_sources()` Called on Every Sweep

**Location:** `scraping.py` lines 1715–1720

The guard `if source_registry.source_count == 0` works because it's per-process, but each Celery worker process calls this on its first sweep. Consider registering in the Celery worker's `celery.signals.worker_init` signal.

### MIN-3: `first_seen_at`/`last_seen_at` Column Types

**Location:** `JobPostingModel` lines 1367-1368

```python
first_seen_at: Mapped[DateTime] = mapped_column()
last_seen_at: Mapped[DateTime] = mapped_column()
```

`DateTime` without `timezone=True` stores naive datetimes. The domain entity uses `datetime.now(timezone.utc)` which is timezone-aware. PostgreSQL will reject timezone-aware datetimes in a naive column. Should be `DateTime(timezone=True)`.

### MIN-4: Duplicate Health Logic

**Location:** `JobSource.record_success/record_failure` (domain entity) AND Celery task direct model updates (lines 1768–1780)

**Problem:** Two places update source health: (a) the domain entity methods, (b) direct model column assignments in the Celery task. The domain entity logic is never called in the sweep — the Celery task bypasses it entirely by setting `source_model.health_status = ...` directly. The domain entity's health methods are dead code.

**Fix:** Use the domain entity: fetch `JobSource` from repository, call `record_success()` or `record_failure()`, save back. Remove the direct model manipulation.

### MIN-5: No Event Emission

**Location:** Missing from `_sweep_all_sources_async`

**Problem:** Domain events (`JobDiscovered`, `JobDedupMerged`, `SweepCompleted`) are defined in `events.py` but never emitted. Downstream consumers (Memory Agent, Notification Service) have no way to react to new jobs.

**Fix:** Emit events through the EventBus after job processing. Acceptable to defer to Sprint 6 (Agent Orchestration) when the EventBus is wired.

### MIN-6: Test Coverage Gaps

**Location:** Test files vs. file inventory

The file inventory lists `tests/unit/jobs/test_dedup.py` (3 tests) but no implementation is provided. Missing tests for:
- `JobDedupService` (listed but not implemented)
- `JobEnrichmentService` (no tests)
- `HealthTracker` (no tests)
- `RateLimiter` (no tests)
- Celery tasks (no tests)
- Repository edge cases (race condition, missing cursor, stale jobs)

### MIN-7: `active_jobs_count: 0` Hardcode

**Location:** `_company_to_response()` line 2004

Returns `"active_jobs_count": 0` for every company. This is worse than omitting the field — it actively provides wrong information. Either compute the count via a subquery or remove the field.

### MIN-8: No Request Timeout on Celery Tasks

**Location:** Celery task definitions

No `time_limit` or `soft_time_limit` is configured on Celery tasks. A stuck scraper (network hang, API timeout) could block the worker indefinitely. Set `time_limit=600` (10 min) and `soft_time_limit=540` (9 min) on sweep tasks.

---

## Suggested Improvements

### IMP-1: Add a GIN Index for Full-Text Search (see MAJ-4)

Migration:
```python
op.execute("ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS description_tsv tsvector")
op.execute("UPDATE job_postings SET description_tsv = to_tsvector('english', coalesce(description_clean, ''))")
op.execute("CREATE INDEX CONCURRENTLY idx_jobs_tsv ON job_postings USING GIN (description_tsv)")
```

### IMP-2: Implement Proper Cursor Pagination

Replace the current `cursor` parameter handling with opaque base64-encoded cursors:
```python
# Encode: base64(json.dumps({"sort_val": ..., "id": "..."}))
# Decode: json.loads(base64.b64decode(cursor))
# Query: WHERE (sort_col, id) > (decoded.sort_val, decoded.id) ORDER BY sort_col, id LIMIT n+1
```

### IMP-3: Use the Domain Entity for Source Health Updates

```python
# In _sweep_all_sources_async:
source_domain = await source_repo.get_by_name(source.source_name)
if result.errors:
    source_domain.record_failure("; ".join(result.errors))
else:
    source_domain.record_success(result.job_count, result.duration_ms)
await source_repo.save(source_domain)
```

### IMP-4: Add Per-Source Commit Boundaries

```python
for source in source_registry.list_enabled():
    async with maker() as source_session:
        # Process one source in its own transaction
        ...
        await source_session.commit()
```

### IMP-5: Add `posted_after` Validation in API

```python
try:
    posted_after_dt = datetime.fromisoformat(posted_after) if posted_after else None
except ValueError:
    raise InvalidFilterError("posted_after must be ISO8601 format")
```

### IMP-6: Implement `SqlJobSourceRepository`

The `JobSourceRepository` interface is defined but never implemented. The Celery tasks read/write `JobSourceModel` directly. Add a `SqlJobSourceRepository` and use it consistently.

### IMP-7: Add Structured Logging to Scrapers

Replace bare `print`/`Exception` handling with structlog calls including source name, duration, job count, and error details.

---

## Architecture Compliance Assessment

| Dimension | Grade | Notes |
|-----------|-------|-------|
| 1. Architecture Compliance | **B+** | Modular monolith respected. Module boundaries correct. Global singleton is the main violation. |
| 2. Clean Architecture | **B** | Domain layer is clean. Celery task mixes infrastructure + orchestration. Direct model access bypasses domain entities. |
| 3. DDD Compliance | **B** | Entities and value objects are well-modeled. Aggregate boundaries are correct. Domain services are appropriately stateless. Direct model manipulation in Celery tasks breaks DDD. |
| 4. Performance | **C+** | HN scraper is 6.7 min per sweep. No FTS index. Missing embedding generation means vector search returns empty. |
| 5. Security | **B+** | No major injection vectors. Rate limiting exists at API layer. `get_or_create` race condition is the main concern. |
| 6. Tests | **C** | 18 tests total (good for unit coverage of domain). Missing: service tests, Celery tests, integration tests for dedup. |
| 7. Repository Design | **B** | Interface contracts are clean. Cursor pagination not implemented. Race condition in get_or_create. |
| 8. Database Design | **B** | Schema is solid. Missing FTS index. Naive datetime columns. JSONB for source tracking is appropriate. |
| 9. API Design | **B** | RESTful and clean. Cursor pagination response is fake. Salary null-safety is fragile. |
| 10. Celery Architecture | **C+** | Task structure is clean. Critical bug with session.get(). Missing timeouts. No dead-letter queue. |
| 11. Error Handling | **B-** | Individual job errors caught. Source-level errors caught. Missing: failed-job count tracking, dead-letter queue, error categorization. |
| 12. Logging | **C+** | Celery logging is adequate. Scrapers have no structured logging. Missing from domain services. No metrics emission. |
| 13. Scalability | **C** | HN scraper won't scale. Single transaction for all sources won't scale. Good: pluggable framework makes adding sources easy. |

**Overall Grade: B** (Passing. Conditional approval with 3 critical fixes required.)

---

## Remediation Plan

### Must-Fix (Before Production Use — 4 hours)

| # | Issue | Effort | Priority |
|---|-------|--------|----------|
| CRIT-1 | Fix `session.get()` with correct select query | 30 min | BLOCKING |
| CRIT-2 | Fix `get_or_create` race condition | 30 min | BLOCKING |
| MAJ-4 | Add GIN index for full-text search (migration + code) | 1 hour | HIGH |
| MAJ-5 | Per-source transaction boundaries | 1 hour | HIGH |
| MIN-3 | Fix DateTime timezone on first_seen_at/last_seen_at | 30 min | HIGH |
| MIN-4 | Use domain entity for source health updates | 30 min | MEDIUM |

### Should-Fix (Before Sprint 5 Merge — 6 hours)

| # | Issue | Effort |
|---|-------|--------|
| MAJ-1 | Implement cursor pagination | 2 hours |
| MAJ-2 | Reduce HN comment limit to 50 | 15 min |
| MAJ-3 | Acknowledge embedding gap, add stub Celery task | 1 hour |
| MIN-2 | Move source registration to worker_init signal | 30 min |
| MIN-6 | Add missing tests (DedupService, HealthTracker, RateLimiter) | 2 hours |

### Nice-to-Have (Can Defer to Sprint 7 — 8 hours)

| # | Issue | Effort |
|---|-------|--------|
| IMP-2 | Opaque cursor token encoding | 2 hours |
| IMP-6 | SqlJobSourceRepository implementation | 1 hour |
| IMP-7 | Structured logging in scrapers | 2 hours |
| MIN-1 | Remove global singleton registry | 1 hour |
| MIN-5 | Event emission through EventBus | 1 hour |
| MIN-7 | Compute active_jobs_count correctly | 1 hour |

---

## Reviewer Notes

Sprint 4 is a solid implementation. The architecture is clean, the domain model is well-thought-out, and the pluggable source framework is exactly the right design for job discovery. The three critical bugs are all implementation-level issues — none indicate a design problem. The structure is correct; the code just needs debugging.

The most concerning finding is the missing cursor pagination (MAJ-1) — the API contract promises something that doesn't work. This should be fixed before any client integrates against it.

The HN scraper performance (MAJ-2) is acceptable for MVP — it still completes within a reasonable time and the data is valuable. Reduce the batch size and move on.

I approve Sprint 4 **conditional on fixing the 3 critical issues** before any production deployment or Sprint 5 merge. The 6 "should-fix" items should be completed during the Sprint 5 development cycle (matching engine) since they share infrastructure (embedding, event bus).

---

> *"Good architecture survives bad code. The structure is sound. Now make the code match the structure."*

**End of Sprint 4 Review**
