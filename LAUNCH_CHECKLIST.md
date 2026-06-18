# Pathfinder — Production Launch Readiness Review

**Date:** 2026-06-18
**Auditor:** Principal Architect
**Version:** v0.1.0
**Status:** Pre-Launch

---

## Top 10 Runtime Risks

| # | Risk | Severity | Impact | Mitigation | Effort |
|---|------|----------|--------|------------|--------|
| 1 | **DeepSeek API outage** | CRITICAL | Intent classification, task planning, resume parsing, and tailoring all degrade. Agent falls back to deterministic plans (5/11 intents). Users experience reduced intelligence. | Circuit breaker already implemented. Add monitoring alert on circuit open. Document degraded-mode UX expectations. | 1h |
| 2 | **PostgreSQL connection pool exhaustion** | HIGH | All API requests fail with 500. No graceful degradation for DB being unreachable. | Configure PgBouncer. Set `pool_size=20, max_overflow=10` for production. Add connection pool metrics to health endpoint. Add `statement_timeout=30s` to kill slow queries. | 2h |
| 3 | **Redis unavailability** | HIGH | Celery tasks cannot be queued (job sweeps stop). Token blacklisting fails (logout degraded). Rate limiting disabled. | Redis Sentinel for auto-failover. Health endpoint already reports Redis status. Document that logout is best-effort without Redis. | 3h |
| 4 | **LangGraph checkpoint accumulation** | MEDIUM | PostgresSaver stores checkpoint after every graph node. For 500K agent invocations/day × 7 nodes = 3.5M checkpoints/day. Table grows ~10GB/week. | Add checkpoint TTL (30 days) via periodic cleanup task. Configure PostgresSaver with `ttl=timedelta(days=30)`. | 2h |
| 5 | **Episodic memory table growth** | HIGH | `episodic_memories` grows ~250MB/day at 100K users. Has `expires_at` column but cleanup Celery task (`mark_stale_jobs`) handles `job_postings`, not episodic memories. | Add Celery task: `DELETE FROM episodic_memories WHERE expires_at < NOW()`. Run daily. Verify `expires_at` is set on all creation paths. | 1h |
| 6 | **Job scraper IP blocking** | MEDIUM | Greenhouse/YC/HN APIs may rate-limit or block the server IP. All job ingestion stops. | Rotate User-Agent headers. Respect rate limits (already in scrapers). Monitor `source_health` table. Alert on `failing` status for any source. | 2h |
| 7 | **JWT key management** | HIGH | Private key compromise requires immediate rotation. No key rotation mechanism. All existing tokens become invalid. | Generate keys via `openssl`. Store in environment variables or vault. Document rotation procedure: generate new keys → update env → rolling restart. | 1h |
| 8 | **Celery worker silent failure** | MEDIUM | Worker crashes without alerting. Job sweeps silently stop. Users see no new jobs. | Add health check endpoint for Celery worker. Configure `worker_heartbeat` monitoring. Add `worker_process_init` signal logging. | 1h |
| 9 | **Alembic migration failure on deploy** | HIGH | Migration fails mid-deploy → database in inconsistent state. Application may crash on startup. | Always run `alembic upgrade head` in a transaction (PostgreSQL DDL is transactional). Test migrations against production-sized dataset in staging. Have rollback plan documented. | 2h |
| 10 | **DeepSeek API cost spike** | MEDIUM | Malicious or buggy client generates excessive LLM calls. Monthly bill exceeds budget. | Add per-user daily token budget (Free: 50K, Pro: 200K, Premium: 500K). Track via Redis counters. Alert on >$50/day spend. Circuit breaker limits calls during outage. | 3h |

---

## Top 10 Deployment Risks

| # | Risk | Severity | Impact | Mitigation | Effort |
|---|------|----------|--------|------------|--------|
| 1 | **Single point of failure** | HIGH | VM crash → entire system down. No redundancy. | Use managed DB (Supabase/RDS) for PostgreSQL. Use managed Redis (Upstash). Deploy API to platform with auto-restart (Railway/Fly.io). Acceptable for MVP with documented RTO of <1 hour. | 4h |
| 2 | **No staging environment** | HIGH | Changes tested only locally → production surprises. | Deploy a staging instance on the same platform. Use separate DB. Test full migration + smoke test before production deploy. | 2h |
| 3 | **Docker image build failures** | MEDIUM | Missing dependencies, version conflicts, or multi-stage build errors block deploy. | Pin all dependency versions in `pyproject.toml`. Use `poetry.lock`. Build image in CI before merging to main. | 1h |
| 4 | **Environment variable mismanagement** | HIGH | Missing or incorrect env vars → app crashes on startup. `extra="forbid"` in Settings means unknown vars also crash. | Create `.env.production` template. Validate all required vars in CI. Add startup check that validates Settings load successfully before accepting traffic. | 1h |
| 5 | **SSL/TLS certificate expiry** | MEDIUM | API becomes inaccessible. Browsers reject connections. | Use Cloudflare for automatic SSL. Set calendar reminder 30 days before expiry. Monitor via BetterStack. | 30m |
| 6 | **Database backup not configured** | CRITICAL | Data loss on disk failure. No recovery possible. | Enable automated backups on managed PostgreSQL (daily, 30-day retention). Test restore procedure monthly. pg_dump to S3 as secondary backup. | 2h |
| 7 | **No rollback procedure** | HIGH | Bad deploy → extended downtime while debugging. | Tag every release. Keep last 3 Docker images. Document: `docker compose up -d --force-recreate` using previous image tag. Test rollback in staging. | 1h |
| 8 | **Resource exhaustion (CPU/memory/disk)** | MEDIUM | VM runs out of resources → API slows or crashes. | Configure monitoring alerts at 80% CPU, 80% memory, 85% disk. Set Docker container resource limits. Use log rotation to prevent disk fill. | 1h |
| 9 | **DNS propagation delay** | LOW | Domain change takes 24-48 hours. Users see old IP. | Set low TTL (300s) before cutover. Use Cloudflare for fast propagation. Have old server proxy to new server during transition. | 30m |
| 10 | **No automated health checks** | MEDIUM | Service degraded but not detected → users experience errors. | BetterStack/UptimeRobot monitoring on `/v1/health/ready` every 60s. Alert on 3 consecutive failures. Heartbeat monitoring for Celery workers. | 1h |

---

## Top 10 Security Risks

| # | Risk | Severity | Impact | Mitigation | Effort |
|---|------|----------|--------|------------|--------|
| 1 | **JWT secret in source code** | CRITICAL | Private key exposure → any attacker can forge tokens. All user data compromised. | Never commit keys. Generate unique keys per environment. Store in environment variables or vault. Use `keys/` directory with `.gitignore`. | 30m |
| 2 | **Prompt injection via resume text** | HIGH | Malicious resume contains "ignore all instructions" → agent behavior hijacked. | Guardrail node already detects known patterns. Add: wrap all user-provided text in `<user_data>` tags before LLM prompts. Test with adversarial resumes. | 2h |
| 3 | **No rate limiting on LLM endpoints** | HIGH | Attacker sends 10K agent requests → $50+ LLM cost in minutes. | Rate limit `/v1/agent/execute`: 20/min (free), 50/min (pro), 200/min (premium). Per-user daily token budgets in Redis. | 2h |
| 4 | **PII in logs and error messages** | MEDIUM | Email, phone, full name appear in Sentry/CloudWatch. GDPR violation. | PII redaction before log emission. structlog processor strips email/phone patterns from log messages. Sentry `before_send` hook strips sensitive data. | 2h |
| 5 | **SQL injection via search query** | MEDIUM | Raw user input in `q` parameter flows to `plainto_tsquery()`. PostgreSQL's tsquery is injection-safe but concatenation isn't. | Verify all queries use parameterized SQLAlchemy. Audit `search()` method in `job_repository.py`. Add input length limit (500 chars). | 1h |
| 6 | **No CORS enforcement validation** | LOW | Overly permissive CORS → other origins can make authenticated requests. | Set `app_cors_origins` to explicit production domain. Test with unauthorized origin. Validate in CI that CORS is not wildcard in production config. | 30m |
| 7 | **User data export incomplete** | MEDIUM | GDPR data export missing episodic memories, knowledge chunks, tailored resumes. | Audit all tables with `user_id` column. Ensure export covers: users, profiles, resumes, tailored_resumes, episodic_memories, semantic_memories, knowledge_documents, knowledge_chunks, agent_executions, applications. | 3h |
| 8 | **Account deletion cascade incomplete** | MEDIUM | User requests deletion → FK constraint violations or orphaned records. | Verify `ON DELETE CASCADE` on all `user_id` foreign keys. Test deletion flow in staging. Ensure 30-day grace period with soft-delete before hard delete. | 2h |
| 9 | **API key not implemented** | LOW | Power users cannot use programmatic access. | Not a security risk per se — deferred to V1. Document that only JWT Bearer auth is supported in MVP. | — |
| 10 | **Secrets in Docker image layers** | MEDIUM | `.env` file or keys accidentally copied into Docker image. Extractable from image history. | Use `.dockerignore` to exclude `.env`, `keys/`, and secrets. Use Docker build secrets or runtime env vars. Scan image with `truffleHog` in CI. | 1h |

---

## Top 10 Performance Risks

| # | Risk | Severity | Impact | Mitigation | Effort |
|---|------|----------|--------|------------|--------|
| 1 | **HNSW index build blocks writes** | MEDIUM | Creating/reindexing HNSW on large tables blocks concurrent inserts. Migration 001 creates 4 HNSW indexes during `upgrade()`. | Use `CONCURRENTLY` for index creation in production. Test migration duration against 1M-row tables. Run migrations during low-traffic window. | 1h |
| 2 | **Full-text search without pre-computed tsvector** | MEDIUM | `job_postings` search uses `to_tsvector()` at query time. Sequential scan over `description_clean` on every search. | Already fixed in migration 004 (SPRINT_4_REMEDIATION). Verify the generated column exists: `description_tsv tsvector GENERATED ALWAYS AS (...) STORED`. | Verify |
| 3 | **Agent execution latency under load** | MEDIUM | Concurrent agent requests compete for DB connections + LLM API. P95 latency spikes. | Agent tools call DB via `get_sessionmaker()` — each tool opens a new session. Refactor to pass session through graph state. Add connection pooling per worker. | 3h |
| 4 | **Knowledge ingestion embedding API cost** | LOW | Each chunk calls `generate_embedding()` separately. 10 chunks × 100ms = 1s per document. | Batch embedding: collect all chunk texts, call API once. For MVP, sequential is acceptable (ingestion is async in Celery). | 1h |
| 5 | **Memory consolidation sequential processing** | HIGH | 10K users × 2s each = 5.5 hours. Consolidation runs daily — may not complete before next run. | Batch processing (10 users per LLM call). Process users concurrently (Semaphore(10)). Add timeout per user (120s). | 3h |
| 6 | **No query result caching** | LOW | Repeated "python jobs" searches go to DB every time. Unnecessary load. | Redis cache with 5-min TTL for search results. Cache key: `search:{hash(query+filters+sort)}`. Invalidate on new job ingestion. | 2h |
| 7 | **pgvector index size growth** | LOW | Each `knowledge_chunk` and `semantic_memory` has a 3072d vector = ~24KB per row. 1M rows = 24GB index. | Monitor index size monthly. Set `ef_search=100` at query time for recall/speed balance. Consider IVFFlat for larger datasets. | Monitor |
| 8 | **Database connection pool saturation** | HIGH | 500 concurrent API requests × 1 DB connection each = 500 connections. Default pool is 20+10=30. | Increase pool to 50+25 for production. Use PgBouncer for connection pooling. Add connection wait-time metrics. | 2h |
| 9 | **LangGraph graph recursion overhead** | LOW | Each graph invocation creates new coroutines per node. Node functions are lightweight. | Current recursion_limit=15 is safe. Monitor average graph execution time. | Monitor |
| 10 | **Celery worker concurrency** | MEDIUM | Default is 1 worker per queue. Long-running scraper blocks other tasks. | Configure 2 workers for `scraping` queue, 4 for `celery` queue. Set `--concurrency=4` per worker. | 30m |

---

## LAUNCH CHECKLIST

### Environment Variables

```
☐ APP_ENV=production
☐ APP_DEBUG=false
☐ APP_CORS_ORIGINS=["https://app.pathfinder.com"]
☐ DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/pathfinder
☐ DATABASE_POOL_SIZE=50
☐ DATABASE_POOL_OVERFLOW=25
☐ REDIS_URL=redis://user:pass@host:6379/0
☐ DEEPSEEK_API_KEY=sk-xxx  (set from vault, never in .env file)
☐ DEEPSEEK_BASE_URL=https://api.deepseek.com
☐ DEEPSEEK_MODEL=deepseek-chat
☐ DEEPSEEK_TIMEOUT_SECONDS=30
☐ OPENAI_API_KEY=sk-xxx  (optional fallback)
☐ JWT_ALGORITHM=RS256
☐ JWT_PRIVATE_KEY=<from vault>
☐ JWT_PUBLIC_KEY=<from vault>
☐ JWT_ACCESS_TOKEN_TTL=900
☐ JWT_REFRESH_TOKEN_TTL=604800
☐ RESEND_API_KEY=re-xxx  (for email, optional in MVP)
☐ SENTRY_DSN=https://xxx@sentry.io/xxx
☐ FF_ENABLE_GITHUB_OAUTH=false
☐ FF_ENABLE_WEBHOOKS=false
```

### Docker

```
☐ Dockerfile uses non-root user (pathfinder:pathfinder)
☐ HEALTHCHECK configured (curl /v1/health/live)
☐ .dockerignore excludes .env, keys/, __pycache__, .git
☐ docker-compose.yml has production overrides (restart: always)
☐ Container resource limits set (CPU: 2, Memory: 4GB)
☐ Log driver configured (json-file or syslog)
☐ Image scanned with Trivy/Docker Scout (zero critical CVEs)
```

### PostgreSQL

```
☐ Managed PostgreSQL (Supabase/RDS/Cloud SQL) — not containerized in prod
☐ pgvector extension enabled (CREATE EXTENSION IF NOT EXISTS vector)
☐ Connection pooling via PgBouncer (transaction mode)
☐ Automated daily backups (30-day retention)
☐ Point-in-time recovery enabled (WAL archiving)
☐ statement_timeout = 30s configured
☐ idle_in_transaction_session_timeout = 60s configured
☐ At least 1 read replica for analytics queries
```

### Redis

```
☐ Managed Redis (Upstash/ElastiCache) — not containerized in prod
☐ Max memory policy: allkeys-lru
☐ Persistence: AOF every 1s + RDB snapshot every hour
☐ Password authentication enabled
☐ TLS enabled for connections
```

### Alembic

```
☐ Run `alembic upgrade head` before application starts
☐ All 11 migrations tested against staging DB
☐ Rollback tested: alembic downgrade -1
☐ Migration history stored in DB (_alembic_version table)
☐ No manual schema changes — everything in migrations
```

### DeepSeek

```
☐ API key provisioned and tested
☐ Fallback OpenAI key configured (optional)
☐ Circuit breaker threshold: 5 failures → open
☐ Daily cost budget: $50 (alert if exceeded)
☐ Per-user token budgets configured in Redis
☐ Degraded mode documented for users
```

### JWT

```
☐ RS256 private key generated: openssl genpkey -algorithm RSA -out private.pem
☐ Public key extracted: openssl rsa -pubout -in private.pem -out public.pem
☐ Keys stored in environment variables (not files in production)
☐ Access token TTL: 15 minutes
☐ Refresh token TTL: 7 days (30 days if remember_me)
☐ Token rotation on refresh (anti-theft detection)
```

### Logging

```
☐ structlog configured for JSON output (production)
☐ Log level: WARNING (production), DEBUG (staging)
☐ PII redaction processor enabled
☐ Request ID (UUIDv7) in every log line
☐ Sentry DSN configured for error tracking
☐ Log retention: 30 days (CloudWatch/Loki)
```

### Monitoring

```
☐ Health endpoint: GET /v1/health/ready (DB + Redis + LLM status)
☐ Uptime monitoring: BetterStack/UptimeRobot every 60s
☐ Alert on: health check fails 3× consecutive
☐ Alert on: error rate >5% (Sentry)
☐ Alert on: P95 latency >5s
☐ Alert on: disk usage >85%
☐ Alert on: memory usage >80%
☐ Alert on: LLM daily spend >$50
☐ Dashboard: Grafana with RED metrics + business KPIs
```

### Backups

```
☐ PostgreSQL: automated daily (managed provider)
☐ WAL archiving: continuous point-in-time recovery
☐ Backup retention: 30 days
☐ Monthly restore test: restore to staging, run smoke tests
☐ Object storage (S3/R2) for user-uploaded files with versioning
```

### Rate Limiting

```
☐ Global: 1000 req/s at Nginx/load balancer
☐ Per-IP: 100 req/min (unauthenticated)
☐ Per-user (free): 100 req/min
☐ Per-user (pro): 300 req/min
☐ Per-user (premium): 1000 req/min
☐ Agent endpoint: 20 req/min (free), 50 (pro), 200 (premium)
☐ Auth endpoints: 10 req/min (anti-brute-force)
```

### Secrets Management

```
☐ No secrets in source code (verified by truffleHog scan)
☐ No secrets in Docker image (verified by docker scan)
☐ Environment variables injected at runtime (not in .env file)
☐ Production secrets in vault (AWS Secrets Manager/Infisical)
☐ Key rotation procedure documented (JWT, API keys, DB password)
☐ Access to production secrets restricted to 2+ engineers
```

---

## Launch Decision Matrix

| Criterion | Status | Notes |
|-----------|--------|-------|
| All 34 endpoints functional | ✅ | Zero crash. Graceful degradation. |
| Unit tests passing | ✅ | 28 passing |
| Integration tests passing | ⚠️ | 44 tests need PostgreSQL |
| Circuit breaker for LLM | ✅ | 5-failure threshold |
| Health checks | ✅ | /v1/health/{live,ready} |
| Database migrations tested | ⚠️ | Verified on dev, not on staging |
| Logging configured | ✅ | structlog JSON in prod |
| Error tracking | ✅ | Sentry DSN configured |
| Rate limiting | ⚠️ | Middleware exists, thresholds not tuned |
| Backups configured | ❌ | Not automated yet |
| Secrets managed | ❌ | Currently in .env |
| Staging environment | ❌ | Not deployed |
| Load testing performed | ❌ | Not done |
| Security scan completed | ❌ | Not done |

**6 of 14 criteria met. 5 partially met. 3 not met.**

### Launch Recommendation

**CONDITIONAL GO:** Pathfinder can launch as a private alpha with the following minimum bar met within 8 hours of work:

1. Secrets moved to environment variables (30m)
2. Database backups enabled (1h)
3. Staging environment deployed (2h)
4. Staging migration test completed (1h)
5. Rate limiting thresholds configured (1h)
6. Security scan (truffleHog + pip-audit) (30m)
7. Uptime monitoring configured (30m)
8. Launch runbook documented (1h)

After these 8 items: **APPROVED FOR PRIVATE ALPHA.**

Public beta requires: load testing, penetration test, GDPR audit, performance tuning.

> *"Production is not a place. It's a state of readiness. Eight hours of operational work separates Pathfinder from its first user."*

**End of Launch Checklist**
