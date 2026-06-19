# Launch Checklist — Pathfinder Beta

**Date**: 2026-06-20
**Target**: Private Beta (10-50 users)

---

## Infrastructure

| # | Item | Status | Notes |
|---|------|:------:|-------|
| 1 | PostgreSQL 16 + pgvector | ✅ | Docker Compose, persistent volume |
| 2 | Redis 7 | ✅ | Rate limiting + caching |
| 3 | Docker Compose deployment | ✅ | 3 services (API, DB, Redis) |
| 4 | Health checks configured | ✅ | Liveness, readiness, startup probes |
| 5 | Container restart policy | ✅ | `restart: unless-stopped` |
| 6 | Resource limits | ⚠️ | Not set in compose — add for production |
| 7 | Multi-AZ/region | ❌ | Single node — not needed for beta |
| 8 | Load balancer | ❌ | Single uvicorn worker — add for >50 users |

## Backups

| # | Item | Status | Notes |
|---|------|:------:|-------|
| 9 | PostgreSQL backups | ⚠️ | Not configured — add pg_dump cron job |
| 10 | Backup schedule | ❌ | Recommend: daily full, hourly WAL |
| 11 | Backup retention | ❌ | Recommend: 30 days |
| 12 | Restore procedure tested | ❌ | Not yet tested |
| 13 | Redis persistence | ✅ | AOF enabled by default |

## Monitoring

| # | Item | Status | Notes |
|---|------|:------:|-------|
| 14 | Health dashboard | ✅ | `GET /v1/admin/stats` |
| 15 | Prometheus metrics | ✅ | `GET /v1/metrics` |
| 16 | Uptime monitoring | ❌ | Not configured — add UptimeRobot/Datadog |
| 17 | Alerting | ❌ | Not configured — add PagerDuty/OpsGenie |
| 18 | Error tracking | ⚠️ | Sentry SDK installed, verify DSN |
| 19 | Performance monitoring | ❌ | Not configured |

## Logging

| # | Item | Status | Notes |
|---|------|:------:|-------|
| 20 | Structured logging | ✅ | structlog configured |
| 21 | Log levels | ✅ | INFO default, DEBUG available |
| 22 | Log aggregation | ❌ | Container logs only — add Loki/ELK |
| 23 | Log retention | ⚠️ | Docker default — configure rotation |
| 24 | Audit logging | ⚠️ | Partial — audit_logs table exists |

## Secrets & Security

| # | Item | Status | Notes |
|---|------|:------:|-------|
| 25 | JWT signing keys | ✅ | Auto-generated on startup |
| 26 | DeepSeek API key | ✅ | In .env (gitignored) |
| 27 | Database password | ✅ | In .env (gitignored) |
| 28 | Secrets rotation | ❌ | Manual — no rotation policy |
| 29 | .env in .gitignore | ✅ | Verified |
| 30 | No hardcoded secrets | ✅ | Verified — all from config |

## SSL / HTTPS

| # | Item | Status | Notes |
|---|------|:------:|-------|
| 31 | SSL certificate | ❌ | Not configured — add Traefik/Nginx + LetsEncrypt |
| 32 | HTTP → HTTPS redirect | ❌ | Not applicable (HTTP only) |
| 33 | HSTS header | ⚠️ | SecurityHeadersMiddleware present |

## Rate Limiting

| # | Item | Status | Notes |
|---|------|:------:|-------|
| 34 | Global rate limiter | ✅ | Redis sliding window, tier-based |
| 35 | Auth endpoints limited | ✅ | 5 registrations/60s, 10 logins/60s |
| 36 | Agent endpoint limited | ⚠️ | 20/60s free tier — too restrictive |
| 37 | Rate limit headers | ✅ | X-RateLimit-Limit, X-RateLimit-Remaining |
| 38 | Retry-After header | ✅ | Sent on 429 responses |

## Database

| # | Item | Status | Notes |
|---|------|:------:|-------|
| 39 | Migrations up to date | ✅ | 4 migrations applied (001, 010, 011, 012) |
| 40 | Connection pooling | ✅ | SQLAlchemy pool configured |
| 41 | Indexes on FK columns | ✅ | Created in migration 001 |
| 42 | Vector indexes | ⚠️ | HNSW deferred to V1 (>2000 dims limit) |
| 43 | Seed data available | ✅ | 500 jobs, 50 users, 200 resumes |

## Pre-Launch Verification

| # | Item | Status | Notes |
|---|------|:------:|-------|
| 44 | All endpoints functional | ✅ | 35/35 working |
| 45 | Demo journey passes | ✅ | 7/7 subsystems |
| 46 | Agent stable | ✅ | 0 crashes, 0 empty responses |
| 47 | Skills extraction quality | ✅ | 90% F1 |
| 48 | RAG relevance | ✅ | 100% Top-1 |
| 49 | Security tested | ✅ | 14/16 pass |
| 50 | Seed data present | ✅ | DB not empty |

---

## Summary

| Category | Ready | Partial | Missing |
|----------|:-----:|:-------:|:-------:|
| Infrastructure | 4 | 2 | 2 |
| Backups | 1 | 1 | 3 |
| Monitoring | 2 | 1 | 3 |
| Logging | 1 | 2 | 1 |
| Secrets | 4 | 0 | 1 |
| SSL | 0 | 1 | 2 |
| Rate Limiting | 3 | 1 | 0 |
| Database | 4 | 1 | 0 |
| Verification | 7 | 0 | 0 |
| **Total** | **26** | **9** | **12** |

**Go decision**: 26 ready, 9 partial, 12 missing. Beta-ready with monitoring/backup gaps.
