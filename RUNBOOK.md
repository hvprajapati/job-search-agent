# Pathfinder — Startup Runbook

**Target:** Local development environment
**Prerequisites:** Docker Desktop, Python 3.12+, openssl

---

## Required Services

| Service | Version | Purpose | Port |
|---------|---------|---------|------|
| PostgreSQL | 16 + pgvector | Primary database + vector search | 5432 |
| Redis | 7 | Cache, rate limiting, Celery broker | 6379 |
| DeepSeek API | cloud | LLM reasoning and embeddings | external |

## Required Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `DATABASE_URL` | YES | `postgresql+asyncpg://...` | Must match docker-compose credentials |
| `REDIS_URL` | YES | `redis://localhost:6379/0` | Must match docker-compose |
| `DEEPSEEK_API_KEY` | YES | — | Get from platform.deepseek.com. Without it, all LLM features degrade. |
| `JWT_PRIVATE_KEY` | YES | — | RSA private key (see Step 2) |
| `JWT_PUBLIC_KEY` | YES | — | RSA public key (see Step 2) |
| `JWT_ALGORITHM` | NO | `RS256` | Use `HS256` with a shared secret for simpler dev setup |
| `DEEPSEEK_MODEL` | NO | `deepseek-chat` | |
| `APP_ENV` | NO | `local` | |
| `APP_DEBUG` | NO | `false` | |
| `APP_CORS_ORIGINS` | NO | `["http://localhost:3000"]` | |
| `OPENAI_API_KEY` | NO | — | Optional LLM fallback |
| `SENTRY_DSN` | NO | — | Error tracking |
| `RESEND_API_KEY` | NO | — | Email (not used in MVP) |

### Startup Blockers

These must be fixed before Pathfinder starts:

1. **`.env` file must exist** — Copy from `.env.example` and fill in values
2. **JWT keys must be generated** — See Step 2 below. Without keys, auth endpoints crash.
3. **PostgreSQL must be running** — `docker compose up -d postgres`
4. **Redis must be running** — `docker compose up -d redis`
5. **Database must exist** — Created automatically by docker-compose
6. **DeepSeek API key** — Without it, agent executes in degraded mode (deterministic fallback). All endpoints still work.

---

## Step 1: Clone and Configure

```bash
git clone https://github.com/pathfinder/pathfinder.git
cd pathfinder
cp .env.example .env
```

Edit `.env`:
```ini
DEEPSEEK_API_KEY=sk-your-actual-key-here
```

---

## Step 2: Generate JWT Keys

**Automatic (dev mode):** No action needed. Pathfinder auto-generates HS256 dev keys on first startup when `APP_ENV=local` and JWT keys are not configured.

**Production:** Must set explicit keys.
```bash
mkdir -p keys
openssl genpkey -algorithm RSA -out keys/private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in keys/private.pem -out keys/public.pem
```
Set in `.env`:
```ini
APP_ENV=production
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY=<contents of private.pem>
JWT_PUBLIC_KEY=<contents of public.pem>
```

---

## Step 3: Start Infrastructure

```bash
docker compose up -d postgres redis
```

Verify:
```bash
docker compose ps
# Both services should show "healthy"
```

---

## Step 4: Run Database Migrations

```bash
alembic upgrade head
```

Verify:
```bash
alembic current
# Should show: 011 (head)
```

---

## Step 5: Start the API

```bash
PYTHONPATH=src uvicorn pathfinder.shared.infrastructure.main:app --host 0.0.0.0 --port 8000 --reload
```

Or with Docker:
```bash
docker compose up -d api
```

---

## Step 6: Start Celery (Background Jobs)

In a separate terminal:

**Celery Worker:**
```bash
PYTHONPATH=src celery -A pathfinder.agent.infrastructure.celery_tasks.scraping worker -Q scraping,celery -c 2 -l info
```

**Celery Beat (scheduler):**
```bash
PYTHONPATH=src celery -A pathfinder.agent.infrastructure.celery_tasks.scraping beat -l info
```

---

## Step 7: Start the Entire Stack (One Command)

```bash
# Development (API + PostgreSQL + Redis)
docker compose up -d

# Production (API + PostgreSQL + Redis + Celery worker + Celery beat)
docker compose -f docker-compose.prod.yml up -d
```

---

## Verification

After startup, verify each endpoint:

```bash
# Health — process alive
curl http://localhost:8000/v1/health/live
# → {"status": "ok"}

# Health — database + Redis reachable
curl http://localhost:8000/v1/health/ready
# → {"status": "ok", "db": true, "redis": true}

# Health — detailed status with LLM metrics
curl http://localhost:8000/v1/health
# → {"status": "ok", "version": "0.1.0", "components": {"db": true, "redis": true, "llm": {...}}}

# Metrics
curl http://localhost:8000/v1/metrics
# → Prometheus text format

# Register a test user
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test1234!", "full_name": "Test User", "accept_terms": true}'
# → 201 with access_token

# Login
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test1234!"}'
# → 200 with JWT tokens

# Agent execution (degraded mode if no DeepSeek)
TOKEN="<access_token_from_login>"
curl -X POST http://localhost:8000/v1/agent/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "find me python jobs", "stream": false}'
# → 200 with agent response
```

## Expected URLs

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI (interactive API docs) |
| `http://localhost:8000/v1/health/live` | Liveness probe |
| `http://localhost:8000/v1/health/ready` | Readiness probe |
| `http://localhost:8000/v1/health` | Detailed health |
| `http://localhost:8000/v1/health/startup` | Bootstrap checks (DB, Redis, migrations, JWT, DeepSeek) |
| `http://localhost:8000/v1/metrics` | Prometheus metrics |
| `http://localhost:8000/v1/auth/register` | Registration |
| `http://localhost:8000/v1/auth/login` | Login |

## Quick Start (All-in-One)

```bash
git clone https://github.com/pathfinder/pathfinder.git && cd pathfinder
cp .env.example .env
# Edit .env: set DEEPSEEK_API_KEY, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY
docker compose up -d
alembic upgrade head
curl http://localhost:8000/v1/health/ready
```
