# Pathfinder — First Run Guide

**Target:** Engineer who just cloned the repo. Never started Pathfinder before.
**Goal:** Get Pathfinder running with all health checks green within 10 minutes.

---

## Phase 1 — Startup Readiness Audit

### 1. Docker Compose Services

| What Happens | Expected Error | Root Cause | Fix |
|-------------|---------------|------------|-----|
| `docker compose up -d` starts PostgreSQL + Redis + API | Postgres: OK. Redis: OK. API: **crashes** on startup. | `lifespan()` calls `ensure_default_tenant_exists()` which queries the `tenants` table. Table doesn't exist until migrations run. | Run migrations **before** starting the API container |
| Docker not installed | `command not found: docker` | Missing Docker Desktop | Install Docker Desktop |
| Port 5432 or 6379 already in use | `port is already allocated` | Another PostgreSQL/Redis instance running | Stop conflicting service or change ports in `.env` |

### 2. PostgreSQL Readiness

| What Happens | Expected Error | Root Cause | Fix |
|-------------|---------------|------------|-----|
| `pg_isready -U pathfinder` | `connection refused` | PostgreSQL container not started | `docker compose up -d postgres` |
| Migrations fail | `password authentication failed` | Wrong credentials in DATABASE_URL | Verify `.env` DATABASE_URL matches docker-compose credentials: `pathfinder:pathfinder_dev` |
| pgvector extension missing | `extension "vector" is not available` | Using vanilla PostgreSQL image instead of `pgvector/pgvector:pg16` | Use `pgvector/pgvector:pg16` image |

### 3. Redis Readiness

| What Happens | Expected Error | Root Cause | Fix |
|-------------|---------------|------------|-----|
| `redis-cli ping` fails | `Could not connect to Redis` | Redis container not started | `docker compose up -d redis` |
| Rate limiting fails silently | No error — requests pass through without limits | Redis unavailable. `RateLimitMiddleware` catches exception and passes. | Start Redis |
| Token blacklisting fails silently | Logout returns 204 but token still valid | Redis unavailable. `logout()` catches exception. | Start Redis |

### 4. Alembic Migrations

| What Happens | Expected Error | Root Cause | Fix |
|-------------|---------------|------------|-----|
| `alembic upgrade head` | `connection refused` | PostgreSQL not running | Start PostgreSQL first |
| Migration 001 fails | `could not open extension control file` | pgvector not installed on PostgreSQL | Use `pgvector/pgvector:pg16` image |
| Migration 011 fails | `column "content_tsv" does not exist` | Migration 001 didn't create the column | Run migrations in order: `alembic upgrade head` |

### 5. Environment Variables

| What Happens | Expected Error | Root Cause | Fix |
|-------------|---------------|------------|-----|
| Settings validation | `1 validation error for Settings` at startup | Unknown env var with `extra="forbid"` | Remove unknown vars or set valid values |
| `DATABASE_URL` not set | `sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL` | .env file missing or variable not exported | `cp .env.example .env`, verify `DATABASE_URL` is set |

### 6. JWT Configuration — **MOST LIKELY FAILURE**

| What Happens | Expected Error | Root Cause | Fix |
|-------------|---------------|------------|-----|
| Register/login attempt | `jose.exceptions.JWSError: Invalid key` | `JWT_PRIVATE_KEY` and `JWT_PUBLIC_KEY` are empty strings (default in config) | Generate RSA keys or use HS256 with shared secret |
| RS256 with malformed key | `ValueError: Could not deserialize key data` | Key file is not valid PEM format | Regenerate: `openssl genpkey -algorithm RSA ...` |

**Root cause trace:**
1. `.env.example` has no JWT key values (blank)
2. Developer copies `.env.example` → `.env`
3. JWT_PRIVATE_KEY = "" and JWT_PUBLIC_KEY = ""
4. `JWTService.__init__()` calls `self._private_key = "".encode()` → empty bytes
5. First `POST /v1/auth/register` calls `jwt.encode(claims, b"", algorithm="RS256")`
6. **CRASH:** `jose.exceptions.JWSError: Invalid key`

**Fix:**
```bash
# Option A: Generate RSA keys
mkdir -p keys
openssl genpkey -algorithm RSA -out keys/private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in keys/private.pem -out keys/public.pem
# Add to .env: JWT_PRIVATE_KEY=<contents of private.pem>, JWT_PUBLIC_KEY=<contents of public.pem>

# Option B: Use HS256 (simpler for development)
# Add to .env: JWT_ALGORITHM=HS256
#              JWT_PRIVATE_KEY=any-secret-string-at-least-32-chars
#              JWT_PUBLIC_KEY=any-secret-string-at-least-32-chars
```

### 7. Uvicorn Startup

| What Happens | Expected Error | Root Cause | Fix |
|-------------|---------------|------------|-----|
| `uvicorn` starts but `/v1/health/ready` returns 503 | DB not reachable | PostgreSQL not running or DATABASE_URL wrong | Start PostgreSQL, verify connection |
| `ModuleNotFoundError: No module named 'pathfinder'` | Import error | `PYTHONPATH` not set to `src/` | `export PYTHONPATH=src` or use Docker |
| Lifespan crashes | `relation "tenants" does not exist` | Migrations not run. `ensure_default_tenant_exists()` queries `tenants` table before it exists. | Run `alembic upgrade head` before starting API |
| Lifespan crashes | `duplicate key value violates unique constraint "tenants_pkey"` | Default tenant already exists from previous run | No action needed — second startup succeeds |

### 8. Celery Worker Startup

| What Happens | Expected Error | Root Cause | Fix |
|-------------|---------------|------------|-----|
| Worker starts but can't connect | `Error connecting to Redis` | Redis not running | Start Redis first |
| Worker imports fail | `ModuleNotFoundError` | `PYTHONPATH` not set | `export PYTHONPATH=src` |
| Scraper fails on first sweep | `ClientError: 404` or rate limit | External API issue, not startup | Normal — scraper errors are logged, not fatal |

### 9. Celery Beat Startup

| What Happens | Expected Error | Root Cause | Fix |
|-------------|---------------|------------|-----|
| Beat scheduler starts but tasks fail | Same as Celery worker issues | Same root causes | Same fixes |
| Beat schedule not loading | `KeyError: 'beat_schedule'` | Celery config not loaded | Verify `app.conf.beat_schedule` is set in scraping.py |

### 10. DeepSeek Integration

| What Happens | Expected Error | Root Cause | Fix |
|-------------|---------------|------------|-----|
| LLM calls return empty responses | No error — graceful degradation | `DEEPSEEK_API_KEY` not set or value is `sk-your-key-here` | Set real API key in `.env` |
| LLM calls fail with 401 | `Invalid API key` | Wrong API key | Verify key at platform.deepseek.com |
| Embeddings return zero vectors | No error — zero vector returned | Same as above | Set real API key |

---

## Phase 2 — Verified Startup Order

```
Step 1: Prerequisites
  □ Docker Desktop installed and running
  □ openssl installed (or use HS256)

Step 2: Clone and configure
  $ git clone <repo> && cd pathfinder
  $ cp .env.example .env

Step 3: Generate JWT keys ← MOST COMMON FAILURE POINT
  Option A (RS256):
    $ mkdir -p keys
    $ openssl genpkey -algorithm RSA -out keys/private.pem -pkeyopt rsa_keygen_bits:2048
    $ openssl rsa -pubout -in keys/private.pem -out keys/public.pem
    Edit .env: set JWT_PRIVATE_KEY and JWT_PUBLIC_KEY to file contents

  Option B (HS256, simpler):
    Edit .env:
      JWT_ALGORITHM=HS256
      JWT_PRIVATE_KEY=dev-secret-change-in-production-1234567890
      JWT_PUBLIC_KEY=dev-secret-change-in-production-1234567890

Step 4: Edit .env — set required values
  □ DEEPSEEK_API_KEY=sk-...  (or leave blank for degraded mode)
  □ DATABASE_URL=postgresql+asyncpg://pathfinder:pathfinder_dev@localhost:5432/pathfinder
  □ REDIS_URL=redis://localhost:6379/0

Step 5: Start infrastructure
  $ docker compose up -d postgres redis
  Verify: docker compose ps → both "healthy"

Step 6: Run migrations
  $ alembic upgrade head
  Verify: alembic current → 011 (head)

Step 7: Start API
  $ PYTHONPATH=src uvicorn pathfinder.shared.infrastructure.main:app --port 8000 --reload
  Verify: curl http://localhost:8000/v1/health/live → {"status":"ok"}

Step 8: Verify health
  $ curl http://localhost:8000/v1/health/ready
  Should return: {"status":"ok","db":true,"redis":true}
  If db=false → PostgreSQL not running or wrong DATABASE_URL
  If redis=false → Redis not running or wrong REDIS_URL

Step 9: Test auth
  $ curl -X POST http://localhost:8000/v1/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"Test1234!","full_name":"Test","accept_terms":true}'
  Should return: 201 with access_token

Step 10: (Optional) Start background workers
  Terminal 2: $ PYTHONPATH=src celery -A pathfinder.agent.infrastructure.celery_tasks.scraping worker -c 2 -l info
  Terminal 3: $ PYTHONPATH=src celery -A pathfinder.agent.infrastructure.celery_tasks.scraping beat -l info
```

---

## Phase 3 — Validation Checkpoints

After each step, verify before proceeding:

| Checkpoint | Command | Expected Output |
|-----------|---------|----------------|
| Docker running | `docker info` | Server version info |
| PostgreSQL healthy | `docker compose ps postgres` | Status: healthy |
| Redis healthy | `docker compose ps redis` | Status: healthy |
| Migrations applied | `alembic current` | 011 (head) |
| API process alive | `curl localhost:8000/v1/health/live` | `{"status":"ok"}` |
| Database reachable | `curl localhost:8000/v1/health/ready` | `"db":true` |
| Redis reachable | `curl localhost:8000/v1/health/ready` | `"redis":true` |
| Auth works | `curl -X POST .../auth/register` | 201 + access_token |
| Agent works | `curl -X POST .../agent/execute` | 200 + response text |

---

## Phase 4 — Recovery Steps

| Symptom | Recovery |
|---------|----------|
| API won't start (import errors) | `pip install -e ".[dev]"` to install all dependencies |
| Auth crashes (JWT error) | See Step 3 — JWT keys not generated |
| Health shows `db: false` | `docker compose up -d postgres`, verify DATABASE_URL |
| Health shows `redis: false` | `docker compose up -d redis`, verify REDIS_URL |
| Migrations won't run | `docker compose up -d postgres`, wait for healthy, retry |
| Agent returns generic responses | DeepSeek API key not set — degraded mode. Set DEEPSEEK_API_KEY for full intelligence. |
| Port 8000 already in use | `lsof -i :8000`, kill existing process or use different port |
| Docker pull fails | Check internet connection, `docker login` if private registry |

---

## THE SINGLE MOST LIKELY STARTUP FAILURE

**JWT keys not generated.**

When a developer clones the repository and copies `.env.example` to `.env`, the JWT_PRIVATE_KEY and JWT_PUBLIC_KEY variables are empty strings. The first request to `POST /v1/auth/register` crashes with `jose.exceptions.JWSError: Invalid key` because the RS256 algorithm requires an actual RSA key pair.

The server starts successfully (uvicorn loads, health endpoints respond), but every authenticated endpoint fails on first use.

**Fix time: 2 minutes.** Generate keys with openssl or switch to HS256 with a shared secret.
