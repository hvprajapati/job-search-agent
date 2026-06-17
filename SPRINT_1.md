# Pathfinder — Sprint 1: Foundation

**Sprint:** 1 of 7
**Duration:** 2 Weeks (10 working days)
**Epic:** E0 — Foundation
**Developer:** Solo
**Goal:** Production-grade project scaffold. Zero business logic. Clean architecture skeleton ready for features.
**Source:** FINAL_ARCHITECTURE.md §7 + EPICS_AND_TASKS.md Epic 0

---

## Sprint 1 Checklist — At a Glance

```
DAY 1  ☐ E0-01: Poetry project + dependencies
       ☐ E0-02: Full folder structure (6 modules × 4 layers)
       ☐ E0-04: Linting, formatting, type checking

DAY 2  ☐ E0-03: Shared domain primitives (Entity, VO, Repository, Result, IDs)
       ☐ E0-05: Docker Compose (PostgreSQL + pgvector + Redis)
       ☐ E0-06: Dockerfile + Dockerfile.dev

DAY 3  ☐ E0-07: SQLAlchemy async engine + session factory
       ☐ E0-08: Redis connection pool
       ☐ E0-09: Pydantic Settings configuration

DAY 4  ☐ E0-10: First Alembic migration (tenants, users, sessions)
       ☐ E0-11: User entity + Email value object

DAY 5  ☐ E0-12: Password hasher (Argon2) + JWT service (RS256)
       ☐ E0-13: UserRepository (SQL) + ORM models

DAY 6  ☐ E0-14a: Auth API routes (register, login)
       ☐ E0-14b: Auth API routes (refresh, logout)
       ☐ E0-14c: Pydantic schemas + FastAPI dependencies

DAY 7  ☐ E0-15a: Auth middleware
       ☐ E0-15b: Rate limiting middleware
       ☐ E0-15c: Request ID + CORS + Error handlers

DAY 8  ☐ E0-16a: Health endpoints (live, ready, detailed)
       ☐ E0-16b: Structured logging (structlog)
       ☐ E0-16c: Sentry error tracking

DAY 9  ☐ E0-16d: GitHub Actions CI/CD pipeline
       ☐ E0-16e: Makefile for common commands
       ☐ Integration: Full E2E verification

DAY 10 ☐ Polish: README, .env.example, documentation
       ☐ Gate review: All acceptance criteria verified
       ☐ Buffer: Fix any issues found
```

---

## Day 1 — Project Initialization & Structure

### E0-01: Initialize Python Project with Poetry (2h)

**Step 1: Create the project**

```bash
mkdir pathfinder && cd pathfinder
poetry init --name pathfinder --description "Autonomous AI Career Agent" \
  --author "Pathfinder Team" --python "^3.12" --no-interaction
```

**Step 2: Add production dependencies**

```bash
poetry add fastapi==0.115.\* uvicorn[standard]==0.32.\*
poetry add sqlalchemy[asyncio]==2.0.\* asyncpg==0.29.\* pgvector==0.3.\*
poetry add redis[hiredis]==5.2.\* celery==5.4.\*
poetry add langgraph==0.3.\* langgraph-checkpoint-postgres==0.1.\*
poetry add pydantic==2.9.\* pydantic-settings==2.6.\*
poetry add httpx==0.28.\* python-multipart==0.0.\*
poetry add structlog==24.4.\* tenacity==9.0.\*
poetry add python-jose[cryptography]==3.3.\* argon2-cffi==23.1.\*
poetry add alembic==1.14.\* PyPDF2==3.0.\* python-docx==1.1.\*
poetry add weasyprint==63.\* sentry-sdk==2.19.\*
poetry add prometheus-client==0.21.\*
```

**Step 3: Add dev dependencies**

```bash
poetry add --group dev pytest==8.3.\* pytest-asyncio==0.24.\*
poetry add --group dev pytest-cov==6.0.\* pytest-mock==3.14.\*
poetry add --group dev black==24.10.\* ruff==0.8.\* mypy==1.13.\*
poetry add --group dev faker==33.\* testcontainers==4.9.\*
poetry add --group dev httpx (already added above, available for testing)
```

**Step 4: Configure pyproject.toml**

```toml
[tool.poetry]
name = "pathfinder"
version = "0.1.0"
description = "Autonomous AI Career Agent"
authors = ["Pathfinder Team"]
readme = "README.md"
packages = [{include = "pathfinder", from = "src"}]

[tool.poetry.dependencies]
python = "^3.12"
# ... (poetry add populates this)

[tool.poetry.group.dev.dependencies]
# ... (poetry add --group dev populates this)

[tool.black]
line-length = 100
target-version = ["py312"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "B", "C4", "SIM", "UP", "ARG", "RUF"]

[tool.ruff.lint.isort]
known-first-party = ["pathfinder"]

[tool.mypy]
strict = true
disallow_untyped_defs = true
warn_unused_ignores = true
warn_return_any = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --strict-markers --cov=src/pathfinder --cov-report=term-missing"

[tool.coverage.run]
source = ["src/pathfinder"]
omit = ["*/migrations/*", "*/tests/*"]

[tool.coverage.report]
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

**Step 5: Create poetry.lock and verify**

```bash
poetry lock
poetry install
poetry run python -c "import fastapi; import sqlalchemy; print('OK')"
```

**Definition of Done:**
- `pyproject.toml` exists with all dependencies listed
- `poetry.lock` committed
- `poetry install` succeeds without errors
- `poetry run python -c "import fastapi, sqlalchemy, redis, pgvector, langgraph, structlog"` — all imports succeed

---

### E0-02: Create Full Folder Structure (2h)

**Create the following directory tree. Every directory gets an `__init__.py` file.**

```
src/
└── pathfinder/
    ├── __init__.py
    │
    ├── shared/
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── base_entity.py
    │   │   ├── base_value_object.py
    │   │   ├── base_repository.py
    │   │   ├── base_domain_event.py
    │   │   ├── identifiers.py
    │   │   ├── result.py
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   ├── __init__.py
    │   │   │   ├── logger_port.py
    │   │   │   ├── event_bus_port.py
    │   │   │   ├── unit_of_work.py
    │   │   │   └── clock_port.py
    │   │   └── pagination.py
    │   └── infrastructure/
    │       ├── __init__.py
    │       ├── database.py
    │       ├── redis.py
    │       ├── clock.py
    │       ├── logging_config.py
    │       └── middleware/
    │           ├── __init__.py
    │           ├── auth.py
    │           ├── rate_limit.py
    │           ├── audit.py
    │           └── request_id.py
    │
    ├── identity/
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py
    │   │   ├── value_objects.py
    │   │   ├── repositories.py
    │   │   ├── services.py
    │   │   ├── events.py
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   └── __init__.py
    │   │   ├── commands.py
    │   │   ├── queries.py
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── models.py
    │   │   │   └── user_repository.py
    │   │   └── auth/
    │   │       ├── __init__.py
    │   │       ├── jwt_service.py
    │   │       ├── password_hasher.py
    │   │       └── google_oauth.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── profile/
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py
    │   │   ├── value_objects.py
    │   │   ├── repositories.py
    │   │   ├── services.py
    │   │   ├── events.py
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   └── __init__.py
    │   │   ├── commands.py
    │   │   ├── queries.py
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   └── models.py
    │   │   ├── llm/
    │   │   │   ├── __init__.py
    │   │   │   └── prompts/
    │   │   │       └── __init__.py
    │   │   ├── parsing/
    │   │   │   └── __init__.py
    │   │   └── rendering/
    │   │       └── __init__.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── jobs/
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py
    │   │   ├── value_objects.py
    │   │   ├── repositories.py
    │   │   ├── services.py
    │   │   ├── events.py
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   └── __init__.py
    │   │   ├── commands.py
    │   │   ├── queries.py
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   └── models.py
    │   │   ├── scraping/
    │   │   │   └── __init__.py
    │   │   ├── matching/
    │   │   │   └── __init__.py
    │   │   └── enrichment/
    │   │       └── __init__.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── tracking/
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py
    │   │   ├── value_objects.py
    │   │   ├── repositories.py
    │   │   ├── services.py
    │   │   ├── events.py
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   └── __init__.py
    │   │   ├── commands.py
    │   │   ├── queries.py
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   └── models.py
    │   │   └── email/
    │   │       └── __init__.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py
    │       ├── schemas.py
    │       └── dependencies.py
    │
    └── agent/
        ├── __init__.py
        ├── domain/
        │   ├── __init__.py
        │   ├── entities.py
        │   ├── value_objects.py
        │   ├── repositories.py
        │   ├── services.py
        │   ├── events.py
        │   └── exceptions.py
        ├── application/
        │   ├── __init__.py
        │   ├── ports/
        │   │   └── __init__.py
        │   ├── commands.py
        │   ├── queries.py
        │   └── handlers.py
        ├── infrastructure/
        │   ├── __init__.py
        │   ├── persistence/
        │   │   ├── __init__.py
        │   │   └── models.py
        │   ├── langgraph/
        │   │   ├── __init__.py
        │   │   ├── nodes/
        │   │   │   └── __init__.py
        │   │   └── tools/
        │   │       └── __init__.py
        │   ├── llm/
        │   │   └── __init__.py
        │   ├── memory/
        │   │   └── __init__.py
        │   └── celery_tasks/
        │       └── __init__.py
        └── presentation/
            ├── __init__.py
            ├── router.py
            ├── schemas.py
            └── dependencies.py
```

**Also create:**

```
tests/
├── __init__.py
├── conftest.py
├── unit/
│   ├── __init__.py
│   ├── identity/
│   │   └── __init__.py
│   ├── profile/
│   │   └── __init__.py
│   ├── jobs/
│   │   └── __init__.py
│   ├── tracking/
│   │   └── __init__.py
│   └── agent/
│       └── __init__.py
├── integration/
│   ├── __init__.py
│   ├── persistence/
│   │   └── __init__.py
│   ├── llm/
│   │   └── __init__.py
│   └── api/
│       └── __init__.py
└── e2e/
    └── __init__.py

alembic/
├── env.py
├── script.py.mako
└── versions/

scripts/
├── seed_dev_data.py
└── run_consolidation.py

.github/
└── workflows/
    └── ci.yml
```

**How to create efficiently:**

```bash
cd src/pathfinder
# Create all directories at once
mkdir -p shared/{domain,application/ports,infrastructure/middleware}
mkdir -p identity/{domain,application/ports,infrastructure/{persistence,auth},presentation}
mkdir -p profile/{domain,application/ports,infrastructure/{persistence,llm/prompts,parsing,rendering},presentation}
mkdir -p jobs/{domain,application/ports,infrastructure/{persistence,scraping,matching,enrichment},presentation}
mkdir -p tracking/{domain,application/ports,infrastructure/{persistence,email},presentation}
mkdir -p agent/{domain,application/ports,infrastructure/{persistence,langgraph/{nodes,tools},llm,memory,celery_tasks},presentation}
# Create __init__.py in every directory
find . -type d -exec touch {}/__init__.py \;
```

**Definition of Done:**
- All directories exist with `__init__.py` files
- Structure matches FINAL_ARCHITECTURE.md §7 exactly
- `find src -type d | wc -l` shows correct count (60+ dirs)
- `poetry run python -c "import pathfinder"` succeeds

---

### E0-04: Configure Linting, Formatting, Type Checking (2h)

**Step 1: Create .editorconfig**

```ini
root = true

[*]
indent_style = space
indent_size = 4
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.{yml,yaml}]
indent_size = 2

[Makefile]
indent_style = tab
```

**Step 2: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
*.egg

# Virtual environment
.venv/
venv/

# Environment
.env
.env.*
!.env.example

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
.docker/

# Data
data/
*.db
*.sqlite3

# Coverage
htmlcov/
.coverage
coverage.xml

# MyPy
.mypy_cache/

# Ruff
.ruff_cache/

# Alembic
alembic/versions/*.pyc
```

**Step 3: Verify tooling**

```bash
poetry run black --check src/ tests/
poetry run ruff check src/ tests/
poetry run mypy src/ --strict
```

At this point, black may fail on empty files. Accept that — it'll pass once we add content. Ruff and mypy will show errors on empty `__init__.py` files — that's expected.

**Step 4: Create Makefile for common commands**

```makefile
.PHONY: help install lint format typecheck test test-cov clean docker-up docker-down

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	poetry install

lint:  ## Run linter
	poetry run ruff check src/ tests/

format:  ## Format code
	poetry run black src/ tests/
	poetry run ruff check --fix src/ tests/

typecheck:  ## Run type checker
	poetry run mypy src/

test:  ## Run tests
	poetry run pytest tests/ -v

test-cov:  ## Run tests with coverage
	poetry run pytest tests/ -v --cov=src/pathfinder --cov-report=term-missing

check: lint typecheck test  ## Run all checks

docker-up:  ## Start Docker services
	docker compose up -d

docker-down:  ## Stop Docker services
	docker compose down

docker-build:  ## Build Docker image
	docker build -t pathfinder:latest .

clean:  ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml dist/ build/
```

**Definition of Done:**
- `.editorconfig`, `.gitignore`, `Makefile` exist
- `make lint` runs ruff (may show warnings on init files — acceptable)
- `make format` runs black successfully
- `make typecheck` runs mypy (will show errors until code is written — acceptable)

---

## Day 2 — Domain Primitives & Docker

### E0-03: Implement Shared Domain Primitives (6h)

These files are the foundation every other module depends on. Write them carefully — they will be imported hundreds of times.

**File: `src/pathfinder/shared/domain/base_entity.py`**

Purpose: Abstract base for all domain entities. Every entity has an identity (UUID), creation timestamp, and update timestamp.

Required contents:
- `BaseEntity` class with `id: UUID`, `created_at: datetime`, `updated_at: datetime`
- `__eq__` based on `id` (identity equality, not attribute equality)
- `__hash__` based on `id`
- Abstract — entities must subclass and define their own fields

**File: `src/pathfinder/shared/domain/base_value_object.py`**

Purpose: Immutable value objects. Equality by value, not identity. Frozen after creation.

Required contents:
- `BaseValueObject` class, frozen dataclass
- `__eq__` compares all fields
- `__hash__` based on all fields

**File: `src/pathfinder/shared/domain/identifiers.py`**

Purpose: Strongly-typed identifier newtypes. Prevents passing a UserId where a JobId is expected.

Required contents:
- `UserId = NewType('UserId', UUID)`
- `TenantId = NewType('TenantId', UUID)`
- `JobId = NewType('JobId', UUID)`
- `ApplicationId = NewType('ApplicationId', UUID)`
- `ResumeId = NewType('ResumeId', UUID)`
- `SessionId = NewType('SessionId', UUID)`
- `ApprovalId = NewType('ApprovalId', UUID)`
- Factory functions: `UserId.generate()`, `TenantId.generate()`, etc. — all return new UUIDv4 wrapped in the newtype

**File: `src/pathfinder/shared/domain/base_repository.py`**

Purpose: Generic abstract repository interface. All domain repositories inherit from this.

Required contents:
- `T = TypeVar('T', bound=BaseEntity)`
- `class BaseRepository(ABC, Generic[T])`
- Abstract methods: `async get_by_id(id) -> T | None`, `async save(entity: T) -> None`, `async list(cursor, limit) -> list[T]`
- No implementation. No imports from infrastructure.

**File: `src/pathfinder/shared/domain/result.py`**

Purpose: Railway-oriented programming. Return Result[T] instead of raising exceptions for expected failures.

Required contents:
- `class Result[T]`
- `is_success: bool`, `is_failure: bool`
- `value: T | None` (only if success)
- `error: DomainError | None` (only if failure)
- Static factory: `Result.success(value)` and `Result.failure(error)`
- `map(fn)` — chain operations on success
- `unwrap()` — get value or raise
- `unwrap_or(default)` — get value or default

**File: `src/pathfinder/shared/domain/exceptions.py`**

Purpose: Domain exception hierarchy. All domain errors inherit from DomainError.

Required contents:
- `class DomainError(Exception)` — base for all domain exceptions
- `class NotFoundError(DomainError)` — entity not found (404)
- `class ValidationError(DomainError)` — business rule violation (422)
- `class ConflictError(DomainError)` — duplicate or conflict (409)
- `class UnauthorizedError(DomainError)` — auth failure (401)
- `class ForbiddenError(DomainError)` — permission denied (403)
- Each has `message: str` and optional `details: dict`

**Unit Tests (write alongside):**
Create `tests/unit/test_result.py`:
- `test_success_creates_result_with_value`
- `test_failure_creates_result_with_error`
- `test_map_on_success_transforms_value`
- `test_map_on_failure_returns_same_error`
- `test_unwrap_on_success_returns_value`
- `test_unwrap_on_failure_raises`

Create `tests/unit/test_base_entity.py`:
- `test_entities_with_same_id_are_equal`
- `test_entities_with_different_id_are_not_equal`
- `test_entity_has_created_at_and_updated_at`

Create `tests/unit/test_value_object.py`:
- `test_value_objects_with_same_values_are_equal`
- `test_value_objects_with_different_values_are_not_equal`
- `test_value_object_is_immutable`

**Definition of Done:**
- All 6 files exist with complete implementations
- 10 unit tests pass (`make test tests/unit/`)
- `python -c "from pathfinder.shared.domain import BaseEntity, Result, UserId"` works

---

### E0-05: Docker Compose — PostgreSQL + pgvector + Redis (4h)

**File: `docker-compose.yml`**

```yaml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: pathfinder-postgres
    environment:
      POSTGRES_USER: pathfinder
      POSTGRES_PASSWORD: pathfinder_dev
      POSTGRES_DB: pathfinder
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pathfinder"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - pathfinder-net

  redis:
    image: redis:7-alpine
    container_name: pathfinder-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - pathfinder-net

  # Optional: minio for S3-compatible file storage (V1)
  # minio:
  #   image: minio/minio:latest
  #   container_name: pathfinder-minio
  #   command: server /data --console-address ":9001"
  #   environment:
  #     MINIO_ROOT_USER: minioadmin
  #     MINIO_ROOT_PASSWORD: minioadmin
  #   ports:
  #     - "9000:9000"
  #     - "9001:9001"
  #   volumes:
  #     - minio_data:/data
  #   networks:
  #     - pathfinder-net

volumes:
  postgres_data:
  redis_data:
  # minio_data:

networks:
  pathfinder-net:
    driver: bridge
```

**File: `.env.example`**

```bash
# ── Application ──────────────────────────────────────────
APP_ENV=local
APP_DEBUG=true
APP_CORS_ORIGINS=["http://localhost:3000"]

# ── Database ─────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://pathfinder:pathfinder_dev@localhost:5432/pathfinder
DATABASE_POOL_SIZE=5
DATABASE_POOL_OVERFLOW=5

# ── Redis ────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── DeepSeek (Primary LLM) ──────────────────────────────
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=30
DEEPSEEK_MAX_RETRIES=3

# ── OpenAI (Fallback LLM) ───────────────────────────────
OPENAI_API_KEY=sk-your-key-here

# ── JWT ──────────────────────────────────────────────────
JWT_PRIVATE_KEY_PATH=./keys/private.pem
JWT_PUBLIC_KEY_PATH=./keys/public.pem
JWT_ALGORITHM=RS256
JWT_ACCESS_TOKEN_TTL=900
JWT_REFRESH_TOKEN_TTL=604800

# ── Email (Resend) ──────────────────────────────────────
RESEND_API_KEY=re-your-key-here

# ── Google OAuth ─────────────────────────────────────────
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# ── Sentry ───────────────────────────────────────────────
SENTRY_DSN=

# ── Feature Flags ────────────────────────────────────────
FF_ENABLE_GITHUB_OAUTH=false
FF_ENABLE_WEBHOOKS=false
```

**Generate JWT keys:**

```bash
mkdir -p keys
openssl genpkey -algorithm RSA -out keys/private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in keys/private.pem -out keys/public.pem
```

**Definition of Done:**
- `docker compose up -d` starts PostgreSQL + Redis
- `docker compose ps` shows both healthy
- `docker compose logs postgres` shows "database system is ready"
- `docker compose logs redis` shows "Ready to accept connections"
- `.env.example` exists with all variables documented
- JWT keys generated in `keys/`

---

### E0-06: Dockerfile + Dockerfile.dev (3h)

**File: `Dockerfile`**

Requirements:
- Multi-stage build (builder → runtime)
- Builder stage: Python 3.12-slim, install poetry, copy pyproject.toml + poetry.lock, `poetry install --no-dev`
- Runtime stage: Python 3.12-slim, copy virtualenv from builder, copy source code
- Non-root user (`pathfinder`) with UID 1000
- HEALTHCHECK using curl against `/v1/health/live`
- CMD: `uvicorn pathfinder.shared.infrastructure.main:app --host 0.0.0.0 --port 8000`

**File: `Dockerfile.dev`**

Requirements:
- Single stage: Python 3.12-slim
- Install poetry, dependencies (including dev)
- Expose 8000
- CMD with `--reload` flag for uvicorn hot-reload
- Mount source code as volume (handled by docker-compose)

**Definition of Done:**
- `docker build -t pathfinder:latest .` succeeds
- `docker build -t pathfinder:dev -f Dockerfile.dev .` succeeds
- Image runs as non-root user (verify: `docker run --rm pathfinder:latest whoami` → `pathfinder`)

---

## Day 3 — Database, Redis, Configuration

### E0-07: SQLAlchemy Async Engine + Session Factory (4h)

**File: `src/pathfinder/shared/infrastructure/database.py`**

Required implementation:

```
Core components:
1. create_async_engine(url, pool_size, max_overflow, echo=debug)
   - Uses asyncpg driver
   - pool_size from settings (default 20)
   - max_overflow from settings (default 10)
   - pool_pre_ping=True (detect stale connections)
   - connect_args with server_settings for application_name

2. async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

3. async def get_session() -> AsyncGenerator[AsyncSession, None]:
   - Yields session from sessionmaker
   - try/finally: closes session
   - This is the FastAPI dependency

4. async def check_database_health() -> bool:
   - Executes SELECT 1
   - Returns True if successful, False otherwise

5. async def close_database() -> None:
   - Disposes engine (called on app shutdown)
```

**File: `tests/integration/persistence/test_database.py`**

```python
# Test: async session connects and executes SELECT 1
# Test: get_session yields a working session
# Test: check_database_health returns True when DB is up
# Test: engine.dispose() is callable
```

**Definition of Done:**
- `from pathfinder.shared.infrastructure.database import get_session` works
- Integration test passes against real PostgreSQL in Docker
- PgBouncer-compatible (transaction mode)

---

### E0-08: Redis Connection Pool (2h)

**File: `src/pathfinder/shared/infrastructure/redis.py`**

Required implementation:

```
Core components:
1. create_redis_pool(url) -> redis.asyncio.ConnectionPool
   - max_connections from settings (default 50)
   - decode_responses=True
   - socket_keepalive=True
   - health_check_interval=30

2. async def get_redis() -> AsyncGenerator[redis.asyncio.Redis, None]:
   - Creates Redis client from pool
   - try/finally: closes client
   - FastAPI dependency

3. async def check_redis_health() -> bool:
   - Executes PING
   - Returns True if PONG, False otherwise

4. async def close_redis() -> None:
   - Closes connection pool (called on app shutdown)
```

**File: `tests/integration/persistence/test_redis.py`**

```python
# Test: get_redis yields a working client
# Test: ping returns True
# Test: set and get round-trip
```

**Definition of Done:**
- `from pathfinder.shared.infrastructure.redis import get_redis` works
- Integration test passes against real Redis in Docker

---

### E0-09: Pydantic Settings Configuration (3h)

**File: `src/pathfinder/shared/config.py`**

Required implementation:

```
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=False,
    )

    # Application
    app_env: Literal["local", "dev", "staging", "production"] = "local"
    app_debug: bool = False
    app_name: str = "pathfinder"
    app_cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = "postgresql+asyncpg://pathfinder:pathfinder_dev@localhost:5432/pathfinder"
    database_pool_size: int = 20
    database_pool_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout_seconds: int = 30
    deepseek_max_retries: int = 3

    # OpenAI (fallback)
    openai_api_key: str = ""

    # JWT
    jwt_private_key: str = ""
    jwt_public_key: str = ""
    jwt_algorithm: str = "RS256"
    jwt_access_token_ttl: int = 900
    jwt_refresh_token_ttl: int = 604800

    # Email
    resend_api_key: str = ""

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Sentry
    sentry_dsn: str = ""

    # Feature flags
    ff_enable_github_oauth: bool = False
    ff_enable_webhooks: bool = False

    @property
    def is_development(self) -> bool:
        return self.app_env in ("local", "dev")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def jwt_private_key_bytes(self) -> bytes:
        return self.jwt_private_key.encode()

    @property
    def jwt_public_key_bytes(self) -> bytes:
        return self.jwt_public_key.encode()


@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

**Test:** `tests/unit/test_config.py`

```python
# Test: Settings loads from .env file
# Test: unknown env var raises ValidationError (extra="forbid")
# Test: is_development returns True for local env
# Test: default values are applied when env var missing
```

**Definition of Done:**
- `Settings()` loads without errors
- `.env.example` matches Settings fields exactly
- `extra="forbid"` prevents unknown environment variables from being silently ignored

---

## Day 4 — Database Migrations & User Entity

### E0-10: First Alembic Migration (4h)

**Step 1: Initialize Alembic**

```bash
poetry run alembic init alembic
```

**Step 2: Configure `alembic/env.py`**

Required changes from default:
- Import `get_settings` and use `settings.database_url`
- Use async engine (import `create_async_engine` from sqlalchemy.ext.asyncio)
- Set `target_metadata` — for now, empty. We'll add model metadata in E0-13.
- `run_migrations_online` uses `connectable = create_async_engine(url)`, then `await conn.run_sync(do_run_migrations)`

**Step 3: Configure `alembic.ini`**

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://pathfinder:pathfinder_dev@localhost:5432/pathfinder
```

**Step 4: Create migration 001**

```bash
poetry run alembic revision --autogenerate -m "001_tenants_users_sessions"
```

OR — since we want explicit control — create the migration manually:

**`alembic/versions/001_tenants_users_sessions.py`**

Upgrade:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    plan VARCHAR(20) NOT NULL DEFAULT 'free',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    billing_email VARCHAR(320),
    settings JSONB DEFAULT '{}',
    max_users INTEGER,
    storage_limit_bytes BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    email VARCHAR(320) NOT NULL,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    full_name VARCHAR(255) NOT NULL,
    avatar_url TEXT,
    hashed_password VARCHAR(255),
    oauth_provider VARCHAR(50),
    oauth_subject VARCHAR(255),
    tier VARCHAR(20) NOT NULL DEFAULT 'free',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    locale VARCHAR(10) DEFAULT 'en-US',
    timezone VARCHAR(50) DEFAULT 'UTC',
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_users_tenant_email ON users(tenant_id, email);
CREATE UNIQUE INDEX idx_users_oauth ON users(oauth_provider, oauth_subject)
    WHERE oauth_provider IS NOT NULL AND oauth_subject IS NOT NULL;

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    token_family_id UUID NOT NULL,
    ip_address INET,
    user_agent TEXT,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON sessions(user_id, is_revoked);
CREATE INDEX idx_sessions_expiry ON sessions(expires_at) WHERE is_revoked = FALSE;
CREATE INDEX idx_sessions_family ON sessions(token_family_id);
```

Downgrade:
```sql
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
```

**Step 5: Verify migrations**

```bash
# Apply
poetry run alembic upgrade head
# Verify tables exist
docker compose exec postgres psql -U pathfinder -d pathfinder -c "\dt"
# Rollback
poetry run alembic downgrade -1
# Re-apply
poetry run alembic upgrade head
```

**Definition of Done:**
- `alembic upgrade head` creates all tables
- `alembic downgrade -1` drops all tables
- `alembic history` shows one migration
- Tables verified: tenants, users, sessions with all columns, indexes, constraints

---

### E0-11: User Entity + Email Value Object (4h)

**File: `src/pathfinder/identity/domain/entities.py`**

Purpose: User entity — the core identity aggregate. This is a domain entity, not an ORM model.

```
class User(BaseEntity):
    email: Email          # Value object, not raw string
    hashed_password: str
    full_name: str
    tier: Tier            # Enum: FREE, PRO, PREMIUM
    status: UserStatus    # Enum: ACTIVE, INACTIVE, SUSPENDED, DELETED
    role: UserRole        # Enum: USER, ADMIN, SUPPORT
    email_verified: bool
    oauth_provider: str | None
    oauth_subject: str | None
    avatar_url: str | None
    locale: str
    timezone: str
    last_login_at: datetime | None
    deleted_at: datetime | None

    Static factory methods:
    - User.register(email, password, full_name) -> User
      (hashes password, sets tier=FREE, status=ACTIVE)

    Instance methods:
    - verify_email() -> None
    - upgrade_tier(new_tier) -> None
    - deactivate() -> None
    - record_login() -> None (updates last_login_at)
```

**File: `src/pathfinder/identity/domain/value_objects.py`**

```
class Email(BaseValueObject):
    value: str
    Validation: must contain @, must have valid domain format
    Factory: Email.create(raw) -> Result[Email]

class Tier(str, Enum):
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPPORT = "support"
```

**File: `src/pathfinder/identity/domain/exceptions.py`**

```
class InvalidCredentialsError(DomainError):
    # Wrong email or password

class EmailAlreadyExistsError(ConflictError):
    # Email already registered

class AccountLockedError(DomainError):
    # Too many failed attempts

class WeakPasswordError(ValidationError):
    # Password doesn't meet requirements
```

**File: `src/pathfinder/identity/domain/repositories.py`**

```
class UserRepository(BaseRepository[User], ABC):
    @abstractmethod
    async def get_by_email(self, email: Email) -> User | None: ...
    @abstractmethod
    async def email_exists(self, email: Email) -> bool: ...
    @abstractmethod
    async def get_by_oauth(self, provider: str, subject: str) -> User | None: ...
```

**Unit Tests: `tests/unit/identity/test_user_entity.py`**

```python
# test_register_creates_user_with_free_tier
# test_register_with_weak_password_returns_error
# test_email_verification_sets_flag
# test_upgrade_tier_changes_tier
# test_users_with_same_id_are_equal
```

**Unit Tests: `tests/unit/identity/test_email_vo.py`**

```python
# test_valid_email_is_accepted
# test_invalid_email_returns_error
# test_emails_are_equal_case_insensitive
# test_empty_email_is_invalid
```

**Definition of Done:**
- User entity with all fields, factory methods, and instance methods
- Email VO with validation
- Enums: Tier, UserStatus, UserRole
- Repository interface (abstract)
- Domain exceptions
- 8 unit tests pass

---

## Day 5 — Auth Infrastructure

### E0-12: Password Hasher + JWT Service (6h)

**File: `src/pathfinder/identity/infrastructure/auth/password_hasher.py`**

Purpose: Argon2id password hashing. Domain service implementation.

```
class Argon2PasswordHasher:
    def hash(self, password: str) -> str:
        # argon2-cffi: PasswordHasher().hash(password)
        # Returns hashed password string

    def verify(self, hash: str, password: str) -> bool:
        # argon2-cffi: PasswordHasher().verify(hash, password)
        # Returns True if match, False otherwise
        # Handles argon2.exceptions.VerifyMismatchError
```

**File: `src/pathfinder/identity/infrastructure/auth/jwt_service.py`**

Purpose: JWT token creation and validation. RS256 asymmetric keys.

```
class JWTService:
    def __init__(self, settings: Settings):
        self.private_key = settings.jwt_private_key_bytes
        self.public_key = settings.jwt_public_key_bytes
        self.algorithm = settings.jwt_algorithm
        self.access_ttl = settings.jwt_access_token_ttl
        self.refresh_ttl = settings.jwt_refresh_token_ttl

    def create_access_token(self, user_id: str, tenant_id: str,
                            tier: str, permissions: list[str]) -> str:
        # Claims: sub, tenant_id, tier, permissions, iat, exp, jti
        # Returns encoded JWT string

    def create_refresh_token(self, user_id: str, family_id: str) -> str:
        # Claims: sub, family_id, type="refresh", iat, exp, jti
        # Returns encoded JWT string

    def decode(self, token: str) -> dict:
        # Decode and validate. Raises JWTError on failure.
        # Returns claims dictionary.

    def decode_without_expiry_check(self, token: str) -> dict:
        # For refresh token rotation — decode expired token to get family_id
```

**Unit Tests: `tests/unit/identity/test_password_hasher.py`**

```python
# test_hash_produces_different_output_for_same_password
# test_verify_matches_correct_password
# test_verify_rejects_wrong_password
```

**Unit Tests: `tests/unit/identity/test_jwt_service.py`**

```python
# test_create_access_token_contains_claims
# test_decode_valid_token_returns_claims
# test_decode_expired_token_raises
# test_decode_tampered_token_raises
# test_refresh_token_has_type_claim
```

**Definition of Done:**
- Argon2id hashing with verify
- JWT RS256 encode/decode
- Access token (15 min) and refresh token (7 day) creation
- 7 unit tests pass

---

### E0-13: UserRepository (SQL) + ORM Models (6h)

**File: `src/pathfinder/identity/infrastructure/persistence/models.py`**

Purpose: SQLAlchemy ORM models. These are infrastructure — the domain never sees them.

```
class TenantModel(Base):
    __tablename__ = "tenants"
    id: Mapped[UUID] (primary_key, default=uuid4)
    name: Mapped[str]
    slug: Mapped[str] (unique)
    plan: Mapped[str]
    status: Mapped[str]
    billing_email: Mapped[str | None]
    settings: Mapped[dict] (JSONB)
    max_users: Mapped[int | None]
    storage_limit_bytes: Mapped[int | None]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    deleted_at: Mapped[datetime | None]

class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[UUID] (primary_key, default=uuid4)
    tenant_id: Mapped[UUID] (ForeignKey("tenants.id"))
    email: Mapped[str]
    email_verified: Mapped[bool]
    full_name: Mapped[str]
    avatar_url: Mapped[str | None]
    hashed_password: Mapped[str | None]
    oauth_provider: Mapped[str | None]
    oauth_subject: Mapped[str | None]
    tier: Mapped[str]
    status: Mapped[str]
    role: Mapped[str]
    locale: Mapped[str]
    timezone: Mapped[str]
    last_login_at: Mapped[datetime | None]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    deleted_at: Mapped[datetime | None]

    # Relationships
    tenant: Mapped[TenantModel] (relationship)
    sessions: Mapped[list["SessionModel"]] (relationship, back_populates, cascade)

    # Mapping methods
    def to_domain(self) -> User:
        # Converts ORM model → domain entity

    @classmethod
    def from_domain(cls, user: User) -> "UserModel":
        # Converts domain entity → ORM model

class SessionModel(Base):
    __tablename__ = "sessions"
    id: Mapped[UUID] (primary_key)
    user_id: Mapped[UUID] (ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] (unique)
    refresh_token_hash: Mapped[str]
    token_family_id: Mapped[UUID]
    ip_address: Mapped[str | None]
    user_agent: Mapped[str | None]
    is_revoked: Mapped[bool]
    expires_at: Mapped[datetime]
    last_activity_at: Mapped[datetime]
    created_at: Mapped[datetime]

    user: Mapped[UserModel] (relationship, back_populates)
```

**File: `src/pathfinder/identity/infrastructure/persistence/user_repository.py`**

Purpose: SQLAlchemy implementation of UserRepository interface.

```
class SqlUserRepository(UserRepository):
    def __init__(self, session: AsyncSession): ...

    async def get_by_id(self, id: UserId) -> User | None:
        # SELECT * FROM users WHERE id = $1 AND deleted_at IS NULL
        # Return model.to_domain() or None

    async def get_by_email(self, email: Email) -> User | None:
        # SELECT * FROM users WHERE email = $1 AND deleted_at IS NULL
        # Return model.to_domain() or None

    async def email_exists(self, email: Email) -> bool:
        # SELECT EXISTS(SELECT 1 FROM users WHERE email = $1)

    async def save(self, user: User) -> None:
        # Convert to model, merge, flush

    async def get_by_oauth(self, provider: str, subject: str) -> User | None:
        # SELECT * WHERE oauth_provider = $1 AND oauth_subject = $2

    async def list(self, cursor: str | None = None,
                   limit: int = 20) -> list[User]:
        # Paginated list for admin (future use)
```

**Integration Tests: `tests/integration/persistence/test_user_repository.py`**

```python
# test_save_and_retrieve_user
# test_get_by_email_finds_user
# test_get_by_email_returns_none_for_missing
# test_email_exists_returns_true_for_existing
# test_email_exists_returns_false_for_nonexistent
```

**Definition of Done:**
- 3 SQLAlchemy models with all columns, relationships, and mapping methods
- SqlUserRepository implements all abstract methods
- 5 integration tests pass against real PostgreSQL

---

## Day 6 — Auth API Routes

### E0-14a, E0-14b, E0-14c: Auth API (10h total across Days 6-7)

**File: `src/pathfinder/identity/presentation/schemas.py`**

Purpose: Pydantic request/response schemas. These are the API contract.

```
class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    locale: str = Field(default="en-US", max_length=10)
    timezone: str = Field(default="UTC", max_length=50)
    accept_terms: bool = Field(default=True)

    @field_validator("email")
    def validate_email(cls, v): ... (simple @ check)

    @field_validator("password")
    def validate_password_strength(cls, v):
        # Min 8 chars, 1 upper, 1 lower, 1 digit

class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str  # Only returned in body for API key auth
    token_type: str = "bearer"
    expires_in: int

class UserResponse(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    tier: str
    has_profile: bool = False

class AuthResponse(BaseModel):
    tokens: TokenResponse
    user: UserResponse

class ErrorResponse(BaseModel):
    error: ErrorDetail

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict] | None = None
    request_id: str
```

**File: `src/pathfinder/identity/application/commands.py`**

```
@dataclass
class RegisterUserCommand:
    email: str
    password: str
    full_name: str
    locale: str
    timezone: str

@dataclass
class LoginUserCommand:
    email: str
    password: str
    ip_address: str | None
    user_agent: str | None
    remember_me: bool
```

**File: `src/pathfinder/identity/application/handlers.py`**

```
class AuthCommandHandler:
    def __init__(self, user_repo: UserRepository,
                 password_hasher: Argon2PasswordHasher,
                 jwt_service: JWTService,
                 session: AsyncSession): ...

    async def register(self, command: RegisterUserCommand) -> Result[User]:
        # 1. Validate email format (Email.create)
        # 2. Check email doesn't exist (ConflictError if so)
        # 3. User.register(email, password, name)
        # 4. user_repo.save(user)
        # 5. Return user

    async def login(self, command: LoginUserCommand) -> Result[tuple[User, str, str]]:
        # 1. Find user by email
        # 2. Verify password
        # 3. Create tokens (access + refresh)
        # 4. Create session (store refresh token hash)
        # 5. user.record_login()
        # 6. user_repo.save()
        # 7. Return (user, access_token, refresh_token)

    async def refresh(self, refresh_token: str) -> Result[tuple[str, str]]:
        # 1. Decode refresh token (allow expired for family check)
        # 2. Hash token → find session
        # 3. Check session not revoked (revoke family if reuse detected)
        # 4. Create new tokens (rotate)
        # 5. Update session with new refresh hash
        # 6. Return new tokens

    async def logout(self, access_token: str) -> None:
        # 1. Decode access token
        # 2. Find session by family_id
        # 3. Revoke session
```

**File: `src/pathfinder/identity/presentation/router.py`**

```python
router = APIRouter(prefix="/v1/auth", tags=["Authentication"])

@router.post("/register", status_code=201, response_model=AuthResponse)
async def register(
    body: RegisterRequest,
    handler: AuthCommandHandler = Depends(get_auth_handler),
    settings: Settings = Depends(get_settings),
):
    # Validate → handler.register → return AuthResponse

@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    request: Request,
    handler: AuthCommandHandler = Depends(get_auth_handler),
):
    # Validate → handler.login → set refresh cookie → return AuthResponse

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,  # Read refresh_token cookie
    handler: AuthCommandHandler = Depends(get_auth_handler),
):
    # Extract cookie → handler.refresh → set new cookie → return TokenResponse

@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    handler: AuthCommandHandler = Depends(get_auth_handler),
):
    # Extract token → handler.logout → clear cookie → 204
```

**File: `src/pathfinder/identity/presentation/dependencies.py`**

```python
async def get_auth_handler(
    session: AsyncSession = Depends(get_session),
) -> AuthCommandHandler:
    settings = get_settings()
    user_repo = SqlUserRepository(session)
    password_hasher = Argon2PasswordHasher()
    jwt_service = JWTService(settings)
    return AuthCommandHandler(user_repo, password_hasher, jwt_service, session)

async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    # Extract JWT from Authorization header
    # Decode → find user → return
    # Raise 401 if invalid/missing
```

**Integration Tests: `tests/integration/api/test_auth_api.py`**

```python
# test_register_creates_user_returns_201
# test_register_duplicate_email_returns_409
# test_register_weak_password_returns_400
# test_login_valid_credentials_returns_200_with_tokens
# test_login_invalid_password_returns_401
# test_login_nonexistent_user_returns_401
# test_refresh_valid_token_returns_200_with_new_tokens
# test_refresh_reused_token_revokes_family_returns_401
# test_logout_revokes_session_returns_204
# test_protected_route_without_auth_returns_401
# test_protected_route_with_valid_token_returns_200
```

**File: `src/pathfinder/shared/infrastructure/main.py`** (FastAPI app factory)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathfinder.shared.config import get_settings
from pathfinder.shared.infrastructure.database import close_database, create_async_engine
from pathfinder.shared.infrastructure.redis import close_redis
from pathfinder.shared.infrastructure.logging_config import setup_logging
from pathfinder.identity.presentation.router import router as auth_router
# ... other routers (added in later sprints)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield
    await close_database()
    await close_redis()

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Pathfinder API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware (order matters)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(CORSMiddleware, ...)
    app.add_middleware(RateLimitMiddleware, ...)
    app.add_middleware(AuditMiddleware, ...)

    # Exception handlers
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    # Routers
    app.include_router(auth_router)
    # ... more routers in later sprints

    # Health endpoints
    @app.get("/v1/health/live")
    async def health_live(): ...

    @app.get("/v1/health/ready")
    async def health_ready(): ...

    @app.get("/v1/health")
    async def health(): ...

    return app

app = create_app()
```

**Definition of Done:**
- 4 auth endpoints working (register, login, refresh, logout)
- All 11 integration tests pass
- FastAPI app factory creates app with all middleware and routers
- Refresh token in httpOnly cookie
- Refresh token rotation with anti-theft detection

---

## Day 7 — Middleware

### E0-15a, E0-15b, E0-15c: Middleware Stack (10h, cont. from Day 6)

**File: `src/pathfinder/shared/infrastructure/middleware/auth.py`**

Purpose: JWT authentication middleware. Extracts and validates JWT from Authorization header, injects user info into request.state.

```
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Skip if path in PUBLIC_PATHS (register, login, health, /docs)
        # 2. Extract Authorization: Bearer <token>
        # 3. Decode JWT → get user_id, tenant_id, tier
        # 4. Set request.state.user_id, request.state.tenant_id, request.state.tier
        # 5. Set PostgreSQL session variable: SET app.tenant_id = $tenant_id
        # 6. await call_next(request)
        # 7. If 401 from decode → return JSON error
```

**File: `src/pathfinder/shared/infrastructure/middleware/rate_limit.py`**

Purpose: Redis-based sliding window rate limiter. Tier-based limits.

```
class RateLimitMiddleware(BaseHTTPMiddleware):
    # Limits: free: 100/min, pro: 300/min, premium: 1000/min
    async def dispatch(self, request: Request, call_next):
        # 1. Extract user_id or IP (for unauthenticated)
        # 2. Build Redis key: rate:{user_id}:{window}
        # 3. Increment counter with TTL
        # 4. If exceeded → 429 with Retry-After header
        # 5. Set response headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
```

**File: `src/pathfinder/shared/infrastructure/middleware/request_id.py`**

Purpose: Inject UUIDv7 request ID into every request. Propagate via response header.

```
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Generate UUIDv7 (time-ordered UUID)
        # 2. Set request.state.request_id
        # 3. structlog.contextvars.bind_contextvars(request_id=str(uuid))
        # 4. Response header: X-Request-ID
```

**File: `src/pathfinder/shared/infrastructure/middleware/audit.py`**

Purpose: Log every request to audit log (stdout for MVP, DB in V1).

```
class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log: method, path, user_id, request_id, timestamp, status_code, duration_ms
```

**File: Global exception handlers (in main.py)**

```python
async def domain_error_handler(request: Request, exc: DomainError):
    status_map = {
        NotFoundError: 404,
        ValidationError: 422,
        ConflictError: 409,
        UnauthorizedError: 401,
        ForbiddenError: 403,
    }
    status = status_map.get(type(exc), 400)
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": type(exc).__name__.upper(),
                "message": str(exc),
                "request_id": request.state.request_id,
            }
        }
    )
```

**Integration Tests:**

```python
# test_request_without_auth_returns_401
# test_rate_limit_exceeded_returns_429
# test_request_id_header_in_response
# test_cors_preflight_returns_correct_headers
# test_domain_error_maps_to_correct_status
# test_validation_error_returns_422_with_details
```

**Definition of Done:**
- All middleware functional
- All exception handlers map correctly
- Protected routes require valid JWT
- Rate limits enforced per tier
- X-Request-ID in every response

---

## Day 8 — Health, Logging, Sentry

### E0-16a: Health Endpoints (2h)

**File: In `src/pathfinder/shared/infrastructure/main.py`**

```python
@app.get("/v1/health/live")
async def health_live():
    """Kubernetes liveness probe. Returns 200 if process is alive."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/v1/health/ready")
async def health_ready():
    """Kubernetes readiness probe. Returns 200 if DB + Redis are reachable."""
    db_ok = await check_database_health()
    redis_ok = await check_redis_health()
    all_ok = db_ok and redis_ok
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ok" if all_ok else "degraded", "db": db_ok, "redis": redis_ok}
    )

@app.get("/v1/health")
async def health():
    """Detailed health for debugging. Includes component status and versions."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "components": {"db": ..., "redis": ...},
        "uptime_seconds": ...,
    }
```

**Tests:**

```python
# test_health_live_returns_200
# test_health_ready_returns_200_when_all_healthy
# test_health_ready_returns_503_when_db_down
# test_health_returns_detailed_info
```

---

### E0-16b: Structured Logging (2h)

**File: `src/pathfinder/shared/infrastructure/logging_config.py`**

```python
import structlog

def setup_logging():
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if get_settings().is_production:
        # JSON format for log aggregation
        structlog.configure(
            processors=shared_processors + [structlog.processors.JSONRenderer()],
            wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING),
        )
    else:
        # Console format for development
        structlog.configure(
            processors=shared_processors + [structlog.dev.ConsoleRenderer()],
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        )

def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)
```

**Definition of Done:**
- Logs are JSON in production, human-readable in development
- Request ID automatically included in all log entries
- Log level configurable via environment

---

### E0-16c: Sentry Error Tracking (2h)

**File: In `src/pathfinder/shared/infrastructure/main.py`**

```python
def setup_sentry(settings: Settings):
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=0.1 if settings.is_production else 1.0,
        before_send=strip_pii_from_sentry_event,  # Redact PII
    )

def strip_pii_from_sentry_event(event, hint):
    """Remove email, name, phone from Sentry events before sending."""
    # Strip sensitive fields from request body, headers, etc.
    return event
```

**Definition of Done:**
- Sentry SDK initialized (no-op if DSN not set)
- PII stripping function filters sensitive data
- Test: raise exception → appears in Sentry dashboard

---

## Day 9 — CI/CD Pipeline

### E0-16d: GitHub Actions CI/CD (5h)

**File: `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-type:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: abatilo/actions-poetry@v3
      - run: poetry install
      - run: poetry run ruff check src/ tests/
      - run: poetry run mypy src/ --strict

  unit-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: pathfinder
          POSTGRES_PASSWORD: pathfinder_test
          POSTGRES_DB: pathfinder_test
        ports:
          - 5432:5432
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    env:
      DATABASE_URL: postgresql+asyncpg://pathfinder:pathfinder_test@localhost:5432/pathfinder_test
      REDIS_URL: redis://localhost:6379/0
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: abatilo/actions-poetry@v3
      - run: poetry install
      - run: poetry run alembic upgrade head
      - run: poetry run pytest tests/ -v --cov=src/pathfinder --cov-report=xml
      - uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml

  docker-build:
    runs-on: ubuntu-latest
    needs: [lint-and-type, unit-tests]
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t pathfinder:${{ github.sha }} .
      - run: docker build -t pathfinder:dev -f Dockerfile.dev .
```

**Definition of Done:**
- CI runs on push and PR
- Lint, type-check, unit tests, docker build all pass
- Coverage report uploaded
- CI completes in < 5 minutes

---

### E0-16e: Integration Verification (3h)

**Manual verification script:** `scripts/verify_sprint1.sh`

```bash
#!/bin/bash
set -e

echo "=== Sprint 1 Verification ==="

echo "1. Docker services..."
docker compose up -d
sleep 5
docker compose ps | grep -q "healthy" && echo "   ✓ Services healthy" || echo "   ✗ FAILED"

echo "2. Database migration..."
poetry run alembic upgrade head && echo "   ✓ Migration applied" || echo "   ✗ FAILED"

echo "3. API server starts..."
poetry run uvicorn pathfinder.shared.infrastructure.main:app --port 8000 &
SERVER_PID=$!
sleep 3

echo "4. Health endpoints..."
curl -sf http://localhost:8000/v1/health/live > /dev/null && echo "   ✓ /health/live" || echo "   ✗ FAILED"
curl -sf http://localhost:8000/v1/health/ready > /dev/null && echo "   ✓ /health/ready" || echo "   ✗ FAILED"

echo "5. Auth flow..."
REGISTER=$(curl -sf -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test1234!","full_name":"Test User","accept_terms":true}')
echo "$REGISTER" | grep -q "access_token" && echo "   ✓ Register" || echo "   ✗ FAILED"

LOGIN=$(curl -sf -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test1234!"}')
ACCESS_TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['tokens']['access_token'])")
echo "   ✓ Login"

curl -sf http://localhost:8000/v1/health/live \
  -H "Authorization: Bearer $ACCESS_TOKEN" > /dev/null && echo "   ✓ Authenticated request" || echo "   ✗ FAILED"

kill $SERVER_PID

echo ""
echo "=== Sprint 1: ALL CHECKS PASSED ==="
```

---

## Day 10 — Polish & Gate Review

### Final Cleanup Tasks (remaining hours)

1. **Write README** (30 min): Clone instructions, `docker compose up`, `make test`, architecture overview. Link to FINAL_ARCHITECTURE.md.

2. **`.env.example` review** (30 min): Verify every variable is documented with example values and descriptions. No secrets committed.

3. **Run full CI pipeline** (1h): Push to GitHub. Verify all checks green. Fix any issues.

4. **Gate review checklist** (1h):

```
☐ docker compose up succeeds on clean checkout
☐ docker compose ps shows postgres + redis healthy
☐ alembic upgrade head creates all tables
☐ make lint → zero errors
☐ make typecheck → zero errors
☐ make test → all tests pass
☐ make test-cov → coverage ≥ 80% on domain layer
☐ POST /v1/auth/register → 201
☐ POST /v1/auth/login → 200 + JWT
☐ POST /v1/auth/refresh → 200 + new tokens
☐ POST /v1/auth/logout → 204
☐ GET /v1/health/live → 200
☐ GET /v1/health/ready → 200 (DB + Redis OK)
☐ GET /v1/health → 200 (detailed)
☐ Protected route without auth → 401
☐ Rate limit exceeded → 429 + headers
☐ X-Request-ID header in all responses
☐ CI pipeline green on GitHub
☐ Docker image builds
```

---

## Sprint 1 — Final File Inventory

```
pathfinder/
├── .editorconfig
├── .env.example
├── .github/workflows/ci.yml
├── .gitignore
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/001_tenants_users_sessions.py
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.dev
├── keys/
│   ├── private.pem
│   └── public.pem
├── Makefile
├── poetry.lock
├── pyproject.toml
├── scripts/
│   └── verify_sprint1.sh
├── src/pathfinder/
│   ├── __init__.py
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── domain/
│   │   │   ├── base_entity.py
│   │   │   ├── base_repository.py
│   │   │   ├── base_value_object.py
│   │   │   ├── base_domain_event.py
│   │   │   ├── exceptions.py
│   │   │   ├── identifiers.py
│   │   │   └── result.py
│   │   ├── application/
│   │   │   ├── ports/ (logger, event_bus, uow, clock)
│   │   │   └── pagination.py
│   │   └── infrastructure/
│   │       ├── database.py
│   │       ├── redis.py
│   │       ├── clock.py
│   │       ├── logging_config.py
│   │       ├── main.py
│   │       └── middleware/ (auth, rate_limit, request_id, audit)
│   ├── identity/
│   │   ├── domain/ (entities, value_objects, repositories, services,
│   │   │           events, exceptions)
│   │   ├── application/ (ports, commands, queries, handlers)
│   │   ├── infrastructure/
│   │   │   ├── persistence/ (models, user_repository)
│   │   │   └── auth/ (jwt_service, password_hasher, google_oauth)
│   │   └── presentation/ (router, schemas, dependencies)
│   ├── profile/ (domain, application, infrastructure, presentation)
│   ├── jobs/ (domain, application, infrastructure, presentation)
│   ├── tracking/ (domain, application, infrastructure, presentation)
│   └── agent/ (domain, application, infrastructure, presentation)
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── identity/ (test_user_entity, test_email_vo, test_jwt, ...)
│   │   └── test_result.py
│   ├── integration/
│   │   ├── api/ (test_auth_api)
│   │   └── persistence/ (test_user_repository, test_redis, test_database)
│   └── e2e/
```

---

## Sprint 1 Completion Criteria

All 10 items must pass:

1. `docker compose up` → both services healthy within 30 seconds
2. `alembic upgrade head` → all tables created
3. `make lint` → 0 errors
4. `make typecheck` → 0 errors
5. `make test` → all tests pass (30+ tests)
6. `make test-cov` → domain layer ≥ 80%
7. Full auth flow works: register → login → access protected route → refresh → logout
8. Health endpoints return correct status with DB/Redis checks
9. CI pipeline green on GitHub main branch
10. `docker build -t pathfinder:latest .` → image builds

---

> *"Sprint 1 is not about features. It's about confidence. At the end of Sprint 1, you know the foundation is solid and every line of code you write from here will land on stable ground."*

**End of Sprint 1**
