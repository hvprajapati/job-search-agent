# Pathfinder — Sprint 2: Core Infrastructure Layer

**Sprint:** 2 of 7
**Duration:** 10 Days
**Developer:** Solo
**Prerequisite:** Sprint 1 complete (project skeleton, Docker, folder structure, dependencies)
**Goal:** All infrastructure code working. Database, migrations, Redis, auth, logging, health. Zero business logic beyond user identity.
**Source:** FINAL_ARCHITECTURE.md §7 + EPICS_AND_TASKS.md Epic 0 Tasks E0-07 through E0-16

---

## Sprint 2 Checklist

```
DAY 1-2  ☐ PostgreSQL integration + Alembic migrations + all tables
DAY 3    ☐ Redis integration (pool, health, client)
DAY 4    ☐ Shared domain primitives (Entity, VO, Repository ABC, Result, IDs, Exceptions)
DAY 5    ☐ Unit of Work + Repository pattern implementations
DAY 6    ☐ Domain entities (User, Tenant, Session, Email, enums)
DAY 7    ☐ JWT + Password hashing + Auth service
DAY 8    ☐ User management API (register, login, refresh, logout)
DAY 9    ☐ Health endpoints + Structured logging + API versioning + Config
DAY 10   ☐ Integration tests, CI verification, gate review
```

---

## Area 1: PostgreSQL Integration

### Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `src/pathfinder/shared/infrastructure/database.py` | Async engine, session factory, health check |
| 2 | `tests/integration/persistence/test_database.py` | Database connection tests |
| 3 | `tests/conftest.py` | Update — add DB fixtures |

### `src/pathfinder/shared/infrastructure/database.py`

```python
"""
PostgreSQL async integration via SQLAlchemy + asyncpg.

Provides:
- Async engine with connection pooling
- Async session factory (FastAPI dependency)
- Health check function
- Graceful shutdown
"""

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text
from pathfinder.shared.config import get_settings

_engine = None
_sessionmaker = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_pool_overflow,
            pool_pre_ping=True,
            echo=settings.app_debug,
            connect_args={
                "server_settings": {"application_name": "pathfinder"},
            },
        )
    return _engine


def get_sessionmaker():
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _sessionmaker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an AsyncSession per request."""
    maker = get_sessionmaker()
    async with maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database_health() -> bool:
    """Check if database is reachable and responsive."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception:
        return False


async def close_database() -> None:
    """Gracefully dispose engine on shutdown."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
```

### `tests/integration/persistence/test_database.py`

```python
"""Integration tests for database connectivity (requires running PostgreSQL)."""
import pytest
from pathfinder.shared.infrastructure.database import (
    check_database_health,
    get_session,
)

pytestmark = pytest.mark.integration


async def test_database_health_returns_true():
    result = await check_database_health()
    assert result is True


async def test_get_session_yields_working_session():
    gen = get_session()
    session = await anext(gen)
    result = await session.execute(text("SELECT 1"))
    assert result.scalar() == 1
    await gen.aclose()


async def test_session_rollback_on_exception():
    gen = get_session()
    session = await anext(gen)
    try:
        async with gen:
            raise ValueError("simulated error")
    except ValueError:
        # Session should be rolled back, not left in a broken state
        assert not session.in_transaction()
```

### Acceptance Criteria
- `from pathfinder.shared.infrastructure.database import get_session` imports cleanly
- `check_database_health()` returns `True` against running PostgreSQL
- `get_session()` yields a working `AsyncSession`
- Exceptions during session use trigger rollback, not commit
- Engine disposed on `close_database()`

---

## Area 2: Alembic Migrations

### Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `alembic/env.py` | Async migration runner |
| 2 | `alembic/versions/001_initial_schema.py` | All MVP tables |
| 3 | `alembic/versions/002_user_preferences.py` | Preferences table |

### `alembic/env.py`

```python
"""Alembic async migration environment."""
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

from pathfinder.shared.config import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
target_metadata = None  # We use raw SQL migrations for explicit control


def run_migrations_offline() -> None:
    url = settings.database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

### `alembic/versions/001_initial_schema.py`

```python
"""001_initial_schema — tenants, users, sessions, profiles, resumes, jobs, applications, memories, audit.

Revision ID: 001
Create Date: 2026-06-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensions ──
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    # ── Identity ──
    op.create_table("tenants",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("billing_email", sa.String(320)),
        sa.Column("settings", sa.JSON(), server_default="{}"),
        sa.Column("max_users", sa.Integer()),
        sa.Column("storage_limit_bytes", sa.BigInteger()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
    )

    op.create_table("users",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.Text()),
        sa.Column("hashed_password", sa.String(255)),
        sa.Column("oauth_provider", sa.String(50)),
        sa.Column("oauth_subject", sa.String(255)),
        sa.Column("tier", sa.String(20), nullable=False, server_default="free"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("locale", sa.String(10), server_default="en-US"),
        sa.Column("timezone", sa.String(50), server_default="UTC"),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_index("idx_users_tenant_email", "users", ["tenant_id", "email"])
    op.create_index("idx_users_oauth", "users", ["oauth_provider", "oauth_subject"],
                    unique=True, postgresql_where=sa.text("oauth_provider IS NOT NULL"))

    op.create_table("sessions",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("refresh_token_hash", sa.String(255), nullable=False),
        sa.Column("token_family_id", sa.UUID(), nullable=False),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_sessions_user", "sessions", ["user_id", "is_revoked"])
    op.create_index("idx_sessions_expiry", "sessions", ["expires_at"],
                    postgresql_where=sa.text("is_revoked = false"))
    op.create_index("idx_sessions_family", "sessions", ["token_family_id"])

    op.create_table("api_keys",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("permissions", sa.JSON(), server_default="[]"),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── Profile ──
    op.create_table("profiles",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                   nullable=False, unique=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("structured_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("embedding", Vector(3072)),
        sa.Column("summary", sa.Text()),
        sa.Column("parsing_confidence", sa.JSON(), server_default="{}"),
        sa.Column("enrichment_data", sa.JSON(), server_default="{}"),
        sa.Column("source", sa.ARRAY(sa.Text())),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table("resumes",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("template_id", sa.String(50), nullable=False, server_default="base"),
        sa.Column("content", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("file_url", sa.Text()),
        sa.Column("file_format", sa.String(10), server_default="pdf"),
        sa.Column("is_base", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("tailored_for_job_id", sa.UUID(), nullable=True),
        sa.Column("tailored_for_role", sa.String(255)),
        sa.Column("performance_metrics", sa.JSON(), server_default="{}"),
        sa.Column("ats_parse_score", sa.SmallInteger()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table("cover_letters",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tone", sa.String(50), server_default="professional"),
        sa.Column("company_research", sa.JSON(), server_default="{}"),
        sa.Column("factuality_score", sa.Float()),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── Jobs ──
    op.create_table("companies",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("canonical_name", sa.String(255), nullable=False, unique=True),
        sa.Column("website", sa.Text()),
        sa.Column("industry", sa.String(100)),
        sa.Column("industry_tags", sa.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("size_range", sa.String(20)),
        sa.Column("employee_count", sa.Integer()),
        sa.Column("funding_stage", sa.String(50)),
        sa.Column("total_funding", sa.BigInteger()),
        sa.Column("founded_year", sa.SmallInteger()),
        sa.Column("headquarters", sa.JSON(), server_default="{}"),
        sa.Column("locations", sa.ARRAY(sa.JSON()), server_default="{}"),
        sa.Column("tech_stack", sa.JSON(), server_default="{}"),
        sa.Column("culture_tags", sa.JSON(), server_default="{}"),
        sa.Column("crunchbase_id", sa.String(100)),
        sa.Column("glassdoor_rating", sa.Float()),
        sa.Column("career_page_url", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table("job_postings",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("canonical_job_id", sa.String(64), nullable=False, unique=True),
        sa.Column("company_id", sa.UUID(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("normalized_title", sa.String(255)),
        sa.Column("location", sa.JSON(), server_default="{}"),
        sa.Column("remote_policy", sa.String(20)),
        sa.Column("description_raw", sa.Text()),
        sa.Column("description_clean", sa.Text()),
        sa.Column("description_summary", sa.Text()),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(50)),
        sa.Column("application_url", sa.Text()),
        sa.Column("job_embedding", Vector(3072)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("first_seen_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("refreshed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_jobs_active_fresh", "job_postings", ["is_active", "first_seen_at"])
    op.create_index("idx_jobs_company", "job_postings", ["company_id"])

    op.create_table("job_sources",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("base_url", sa.Text()),
        sa.Column("scraper_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("priority", sa.SmallInteger(), server_default="5"),
        sa.Column("sweep_interval_min", sa.Integer(), server_default="60"),
        sa.Column("health_status", sa.String(20), server_default="healthy"),
        sa.Column("last_sweep_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("last_sweep_status", sa.String(20)),
        sa.Column("success_rate", sa.Float()),
        sa.Column("jobs_per_sweep_avg", sa.Float()),
        sa.Column("consecutive_fails", sa.SmallInteger(), server_default="0"),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table("job_enrichments",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", sa.UUID(), sa.ForeignKey("job_postings.id", ondelete="CASCADE"),
                   nullable=False, unique=True),
        sa.Column("tech_stack", sa.JSON(), server_default="{}"),
        sa.Column("salary_range", sa.JSON(), server_default="{}"),
        sa.Column("seniority", sa.String(30)),
        sa.Column("required_skills", sa.JSON(), server_default="[]"),
        sa.Column("nice_to_have_skills", sa.JSON(), server_default="[]"),
        sa.Column("required_years_min", sa.SmallInteger()),
        sa.Column("education_required", sa.String(100)),
        sa.Column("interview_process", sa.JSON(), server_default="{}"),
        sa.Column("benefits_inferred", sa.JSON(), server_default="{}"),
        sa.Column("urgency_flag", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("enrichment_version", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── Tracking ──
    op.create_table("applications",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.UUID(), sa.ForeignKey("job_postings.id"), nullable=True),
        sa.Column("resume_id", sa.UUID(), sa.ForeignKey("resumes.id"), nullable=True),
        sa.Column("cover_letter_id", sa.UUID(), sa.ForeignKey("cover_letters.id"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="saved"),
        sa.Column("status_history", sa.JSON(), server_default="[]"),
        sa.Column("source_channel", sa.String(50)),
        sa.Column("match_score_at_apply", sa.Float()),
        sa.Column("notes", sa.Text()),
        sa.Column("applied_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("last_updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("next_follow_up_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
    )
    op.create_index("idx_applications_user_status", "applications", ["user_id", "status"])

    op.create_table("interviews",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("application_id", sa.UUID(), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("duration_minutes", sa.SmallInteger()),
        sa.Column("interviewer_name", sa.String(255)),
        sa.Column("interviewer_role", sa.String(100)),
        sa.Column("location", sa.String(50)),
        sa.Column("meeting_link", sa.Text()),
        sa.Column("status", sa.String(30), server_default="scheduled"),
        sa.Column("notes", sa.Text()),
        sa.Column("feedback", sa.JSON(), server_default="{}"),
        sa.Column("outcome", sa.String(30)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table("offers",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("application_id", sa.UUID(), sa.ForeignKey("applications.id", ondelete="CASCADE"),
                   nullable=False, unique=True),
        sa.Column("compensation", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("negotiated", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("negotiation_history", sa.JSON(), server_default="[]"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table("application_tasks",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("application_id", sa.UUID(), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("due_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("is_completed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_by", sa.String(50), server_default="user"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table("application_communications",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("application_id", sa.UUID(), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("comm_type", sa.String(30), nullable=False),
        sa.Column("subject", sa.Text()),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("sent_via", sa.String(50)),
        sa.Column("generated_by", sa.String(50), server_default="user"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── Memory ──
    op.create_table("episodic_memories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("episode_type", sa.String(50), nullable=False),
        sa.Column("actor", sa.String(50), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("importance_score", sa.Float(), server_default="0.5"),
        sa.Column("emotion_signal", sa.Float()),
        sa.Column("embedding", Vector(1536)),
        sa.Column("context_summary", sa.Text()),
        sa.Column("parent_episode_id", sa.UUID()),
        sa.Column("consolidation_id", sa.UUID()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.PrimaryKeyConstraint("id", "created_at"),
    )
    op.create_index("idx_episodic_user_time", "episodic_memories", ["user_id", sa.text("created_at DESC")])

    op.create_table("semantic_memories",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("memory_type", sa.String(50), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("content_text", sa.Text()),
        sa.Column("embedding", Vector(3072)),
        sa.Column("confidence", sa.Float(), server_default="0.5"),
        sa.Column("evidence_episodes", sa.ARRAY(sa.UUID()), server_default="{}"),
        sa.Column("evidence_count", sa.Integer(), server_default="1"),
        sa.Column("importance_score", sa.Float(), server_default="0.5"),
        sa.Column("access_count", sa.Integer(), server_default="0"),
        sa.Column("last_accessed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("last_updated_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("consolidation_run_id", sa.UUID()),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_semantic_user_type", "semantic_memories", ["user_id", "memory_type"])

    op.create_table("user_preferences",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("preference_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("source_breakdown", sa.JSON(), server_default="{}"),
        sa.Column("confidence_scores", sa.JSON(), server_default="{}"),
        sa.Column("evidence_episodes", sa.ARRAY(sa.UUID()), server_default="{}"),
        sa.Column("change_summary", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table("career_timeline",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_type", sa.String(50), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("structured_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("importance", sa.String(20), server_default="minor"),
        sa.Column("source", sa.Text()),
        sa.Column("verified", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("embedding", Vector(3072)),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── Agent & Audit ──
    op.create_table("agent_executions",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("call_id", sa.UUID(), nullable=False, unique=True),
        sa.Column("parent_call_id", sa.UUID()),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("input_context", sa.JSON(), server_default="{}"),
        sa.Column("output_summary", sa.JSON(), server_default="{}"),
        sa.Column("tools_called", sa.JSON(), server_default="[]"),
        sa.Column("llm_model", sa.String(50), nullable=False),
        sa.Column("llm_provider", sa.String(20)),
        sa.Column("tokens_used", sa.JSON(), server_default="{}"),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("cost_estimate", sa.Numeric(10, 6)),
        sa.Column("is_success", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error_message", sa.Text()),
        sa.Column("error_type", sa.String(50)),
        sa.Column("retry_count", sa.SmallInteger(), server_default="0"),
        sa.Column("user_approved", sa.Boolean()),
        sa.Column("user_modified", sa.Boolean()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_agent_user_time", "agent_executions", ["user_id", sa.text("created_at DESC")])
    op.create_index("idx_agent_session", "agent_executions", ["session_id"])

    op.create_table("audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_type", sa.String(50), nullable=False),
        sa.Column("actor_id", sa.UUID()),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("action_category", sa.String(50)),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", sa.UUID()),
        sa.Column("changes", sa.JSON(), server_default="{}"),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("request_id", sa.UUID()),
        sa.Column("metadata", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", "created_at"),
    )
    op.create_index("idx_audit_user_time", "audit_logs", ["user_id", sa.text("created_at DESC")])

    # ── HNSW Vector Indexes (created separately for performance) ──
    op.execute(
        "CREATE INDEX idx_jobs_embedding ON job_postings "
        "USING hnsw (job_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 200)"
    )
    op.execute(
        "CREATE INDEX idx_semantic_embedding ON semantic_memories "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 200)"
    )
    op.execute(
        "CREATE INDEX idx_episodic_embedding ON episodic_memories "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 12, ef_construction = 150)"
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("agent_executions")
    op.drop_table("career_timeline")
    op.drop_table("user_preferences")
    op.drop_table("semantic_memories")
    op.drop_table("episodic_memories")
    op.drop_table("application_communications")
    op.drop_table("application_tasks")
    op.drop_table("offers")
    op.drop_table("interviews")
    op.drop_table("applications")
    op.drop_table("job_enrichments")
    op.drop_table("job_sources")
    op.drop_table("job_postings")
    op.drop_table("companies")
    op.drop_table("cover_letters")
    op.drop_table("resumes")
    op.drop_table("profiles")
    op.drop_table("api_keys")
    op.drop_table("sessions")
    op.drop_table("users")
    op.drop_table("tenants")
```

### `alembic/versions/002_user_preferences_index.py`

```python
"""002_user_preferences_index.

Revision ID: 002
Create Date: 2026-06-18
"""
from alembic import op

revision: str = "002"
down_revision: str = "001"


def upgrade() -> None:
    op.create_index(
        "idx_prefs_current",
        "user_preferences",
        ["user_id", "is_current"],
        unique=False,
        postgresql_where="is_current = true",
    )
    op.create_index(
        "idx_semantic_active",
        "semantic_memories",
        ["user_id", "is_active"],
        postgresql_where="is_active = true",
    )


def downgrade() -> None:
    op.drop_index("idx_prefs_current", table_name="user_preferences")
    op.drop_index("idx_semantic_active", table_name="semantic_memories")
```

### Acceptance Criteria
- `alembic upgrade head` creates all 21 tables with correct columns, types, constraints, indexes
- `alembic downgrade -2` drops all tables cleanly
- `alembic upgrade head` re-applies without errors
- 3 HNSW indexes created on vector columns
- All foreign keys enforce referential integrity
- Partial indexes created correctly (WHERE clauses)

---

## Area 3: Redis Integration

### Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `src/pathfinder/shared/infrastructure/redis.py` | Connection pool, client, health check |
| 2 | `tests/integration/persistence/test_redis.py` | Redis integration tests |

### `src/pathfinder/shared/infrastructure/redis.py`

```python
"""
Redis async integration.

Provides:
- Connection pool with keepalive
- Client factory (FastAPI dependency)
- Health check function
- Graceful shutdown
"""

from collections.abc import AsyncGenerator
import redis.asyncio as aioredis
from pathfinder.shared.config import get_settings

_pool = None


def get_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=50,
            decode_responses=True,
            socket_keepalive=True,
            health_check_interval=30,
        )
    return _pool


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency: yields a Redis client per request."""
    pool = get_pool()
    client = aioredis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.aclose()


async def check_redis_health() -> bool:
    """Check if Redis is reachable."""
    try:
        pool = get_pool()
        client = aioredis.Redis(connection_pool=pool)
        result = await client.ping()
        await client.aclose()
        return result is True
    except Exception:
        return False


async def close_redis() -> None:
    """Gracefully close pool on shutdown."""
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None
```

### `tests/integration/persistence/test_redis.py`

```python
import pytest
from pathfinder.shared.infrastructure.redis import check_redis_health, get_redis

pytestmark = pytest.mark.integration


async def test_redis_health_returns_true():
    assert await check_redis_health() is True


async def test_get_redis_yields_working_client():
    gen = get_redis()
    client = await anext(gen)
    result = await client.ping()
    assert result is True
    await gen.aclose()


async def test_set_and_get_roundtrip():
    gen = get_redis()
    client = await anext(gen)
    await client.set("test_key", "hello", ex=60)
    value = await client.get("test_key")
    assert value == "hello"
    await client.delete("test_key")
    await gen.aclose()
```

### Acceptance Criteria
- `check_redis_health()` returns True against running Redis
- `get_redis()` yields a client that can `ping()` and `set()/get()`
- Pool reuses connections (verify: two `get_redis()` calls share underlying connections)
- `close_redis()` disconnects pool cleanly

---

## Area 4: Repository Pattern

### Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `src/pathfinder/shared/domain/base_repository.py` | Generic abstract repository ABC |
| 2 | `src/pathfinder/shared/domain/base_entity.py` | Base entity class (all entities inherit) |
| 3 | `src/pathfinder/shared/domain/base_value_object.py` | Immutable value object base |
| 4 | `src/pathfinder/shared/domain/identifiers.py` | Typed ID newtypes |
| 5 | `src/pathfinder/shared/domain/result.py` | Result[T] monad |
| 6 | `src/pathfinder/shared/domain/exceptions.py` | Domain exception hierarchy |
| 7 | `tests/unit/test_result.py` | Result monad tests |
| 8 | `tests/unit/test_base_entity.py` | Entity tests |
| 9 | `tests/unit/test_value_object.py` | Value object tests |

### `src/pathfinder/shared/domain/base_entity.py`

```python
"""Abstract base for all domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(kw_only=True)
class BaseEntity:
    """All domain entities extend this. Identity-based equality."""

    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseEntity):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def mark_updated(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
```

### `src/pathfinder/shared/domain/base_value_object.py`

```python
"""Immutable value object base."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class BaseValueObject:
    """Value objects are immutable and compared by value, not identity."""

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return tuple(sorted(self.__dict__.items())) == tuple(sorted(other.__dict__.items()))

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))
```

### `src/pathfinder/shared/domain/base_repository.py`

```python
"""Generic abstract repository."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID
from pathfinder.shared.domain.base_entity import BaseEntity

T = TypeVar("T", bound=BaseEntity)


class BaseRepository(ABC, Generic[T]):
    """Abstract repository. Domain defines what it needs; infrastructure implements how."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> T | None:
        """Retrieve entity by ID. Returns None if not found."""
        ...

    @abstractmethod
    async def save(self, entity: T) -> None:
        """Persist entity (insert or update)."""
        ...

    @abstractmethod
    async def delete(self, entity: T) -> None:
        """Remove entity."""
        ...
```

### `src/pathfinder/shared/domain/identifiers.py`

```python
"""Strongly-typed identifier newtypes. Prevents passing UserId where JobId is expected."""
from uuid import UUID, uuid4
from typing import NewType

UserId = NewType("UserId", UUID)
TenantId = NewType("TenantId", UUID)
JobId = NewType("JobId", UUID)
ApplicationId = NewType("ApplicationId", UUID)
ResumeId = NewType("ResumeId", UUID)
SessionId = NewType("SessionId", UUID)
CoverLetterId = NewType("CoverLetterId", UUID)
InterviewId = NewType("InterviewId", UUID)
ApprovalId = NewType("ApprovalId", UUID)

def new_user_id() -> UserId: return UserId(uuid4())
def new_tenant_id() -> TenantId: return TenantId(uuid4())
def new_job_id() -> JobId: return JobId(uuid4())
def new_application_id() -> ApplicationId: return ApplicationId(uuid4())
def new_resume_id() -> ResumeId: return ResumeId(uuid4())
def new_session_id() -> SessionId: return SessionId(uuid4())
```

### `src/pathfinder/shared/domain/result.py`

```python
"""Result[T] monad for railway-oriented error handling."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, TypeVar, Callable

T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True)
class Result(Generic[T]):
    """Represents either success (with value) or failure (with error)."""

    _value: T | None = None
    _error: Exception | None = None
    _is_success: bool = True

    @staticmethod
    def success(value: T) -> Result[T]:
        return Result(_value=value, _is_success=True)

    @staticmethod
    def failure(error: Exception) -> Result[T]:
        return Result(_error=error, _is_success=False)

    @property
    def is_success(self) -> bool:
        return self._is_success

    @property
    def is_failure(self) -> bool:
        return not self._is_success

    @property
    def value(self) -> T:
        if self.is_failure:
            raise ValueError(f"Cannot get value from failure: {self._error}")
        return self._value  # type: ignore

    @property
    def error(self) -> Exception:
        if self.is_success:
            raise ValueError("Cannot get error from success")
        return self._error  # type: ignore

    def map(self, fn: Callable[[T], U]) -> Result[U]:
        if self.is_failure:
            return Result.failure(self._error)  # type: ignore
        return Result.success(fn(self._value))  # type: ignore

    def unwrap_or(self, default: T) -> T:
        return self._value if self.is_success else default  # type: ignore
```

### `src/pathfinder/shared/domain/exceptions.py`

```python
"""Domain exception hierarchy."""


class DomainError(Exception):
    """Base for all domain exceptions."""
    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code or type(self).__name__
        super().__init__(message)


class NotFoundError(DomainError):
    """Entity not found (→ 404)."""
    pass


class ValidationError(DomainError):
    """Business rule violation (→ 422)."""
    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class ConflictError(DomainError):
    """Duplicate or conflict (→ 409)."""
    pass


class UnauthorizedError(DomainError):
    """Authentication required (→ 401)."""
    pass


class ForbiddenError(DomainError):
    """Permission denied (→ 403)."""
    pass
```

### Tests

**`tests/unit/test_result.py`:**
```python
from pathfinder.shared.domain.result import Result
from pathfinder.shared.domain.exceptions import ValidationError

def test_success_has_value():
    r = Result.success(42)
    assert r.is_success is True
    assert r.is_failure is False
    assert r.value == 42

def test_failure_has_error():
    err = ValidationError("bad")
    r = Result.failure(err)
    assert r.is_failure is True
    assert r.error is err

def test_map_transforms_success():
    r = Result.success(5).map(lambda x: x * 2)
    assert r.value == 10

def test_map_passes_through_failure():
    err = ValidationError("bad")
    r = Result.failure(err).map(lambda x: x * 2)
    assert r.is_failure is True
    assert r.error is err

def test_unwrap_or_returns_value_on_success():
    assert Result.success(10).unwrap_or(0) == 10

def test_unwrap_or_returns_default_on_failure():
    assert Result.failure(ValidationError("x")).unwrap_or(0) == 0
```

**`tests/unit/test_base_entity.py`:**
```python
from uuid import uuid4
from pathfinder.shared.domain.base_entity import BaseEntity

class TestEntity(BaseEntity):
    name: str = ""

def test_same_id_are_equal():
    id_ = uuid4()
    a = TestEntity(id=id_)
    b = TestEntity(id=id_)
    assert a == b

def test_different_id_not_equal():
    assert TestEntity() != TestEntity()

def test_mark_updated_changes_timestamp():
    e = TestEntity()
    original = e.updated_at
    e.mark_updated()
    assert e.updated_at > original
```

**`tests/unit/test_value_object.py`:**
```python
from pathfinder.shared.domain.base_value_object import BaseValueObject
from dataclasses import dataclass

@dataclass(frozen=True, kw_only=True)
class Color(BaseValueObject):
    r: int
    g: int
    b: int

def test_same_values_are_equal():
    assert Color(r=255, g=0, b=0) == Color(r=255, g=0, b=0)

def test_different_values_not_equal():
    assert Color(r=255, g=0, b=0) != Color(r=0, g=255, b=0)

def test_is_immutable():
    c = Color(r=0, g=0, b=0)
    try:
        c.r = 255  # type: ignore
        assert False, "Should have raised FrozenInstanceError"
    except Exception:
        pass
```

### Acceptance Criteria
- All 6 domain files exist in `shared/domain/`
- 9 unit tests pass
- `BaseRepository` is generic and abstract
- `Result` supports `success`, `failure`, `map`, `unwrap_or`
- Identifiers are distinct types — `UserId` is not assignable to `JobId`
- Value objects are frozen and compared by value

---

## Area 5: Unit of Work Pattern

### Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `src/pathfinder/shared/application/ports/unit_of_work.py` | UoW abstract base |
| 2 | `src/pathfinder/shared/infrastructure/unit_of_work.py` | SQLAlchemy UoW implementation |
| 3 | `tests/unit/test_unit_of_work.py` | UoW tests |

### `src/pathfinder/shared/application/ports/unit_of_work.py`

```python
"""Abstract Unit of Work — transaction boundary across repositories."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncContextManager


class UnitOfWork(ABC):
    """Encapsulates a database transaction spanning multiple repository operations."""

    @abstractmethod
    async def commit(self) -> None:
        """Commit the transaction."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Roll back the transaction."""
        ...

    async def __aenter__(self) -> UnitOfWork:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
```

### `src/pathfinder/shared/infrastructure/unit_of_work.py`

```python
"""SQLAlchemy implementation of UnitOfWork."""
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.application.ports.unit_of_work import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    @property
    def session(self) -> AsyncSession:
        return self._session
```

### Acceptance Criteria
- `UnitOfWork` abstract class with `commit()`, `rollback()`, and context manager support
- `SqlAlchemyUnitOfWork` wraps an `AsyncSession`
- `async with uow:` commits on success, rollbacks on exception

---

## Area 6: Domain Entities

### Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `src/pathfinder/identity/domain/entities.py` | User, Tenant, Session entities |
| 2 | `src/pathfinder/identity/domain/value_objects.py` | Email, enums (Tier, UserStatus) |
| 3 | `src/pathfinder/identity/domain/exceptions.py` | Identity-specific errors |
| 4 | `src/pathfinder/identity/domain/repositories.py` | UserRepository, SessionRepository (abstract) |
| 5 | `tests/unit/identity/test_user_entity.py` | User entity tests |
| 6 | `tests/unit/identity/test_email_vo.py` | Email VO tests |

### `src/pathfinder/identity/domain/entities.py`

```python
"""Identity domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.shared.domain.identifiers import UserId, TenantId, new_user_id
from pathfinder.identity.domain.value_objects import Email, Tier, UserStatus, UserRole


@dataclass(kw_only=True)
class User(BaseEntity):
    email: Email
    hashed_password: str | None = None
    full_name: str = ""
    tier: Tier = Tier.FREE
    status: UserStatus = UserStatus.ACTIVE
    role: UserRole = UserRole.USER
    email_verified: bool = False
    oauth_provider: str | None = None
    oauth_subject: str | None = None
    avatar_url: str | None = None
    locale: str = "en-US"
    timezone: str = "UTC"
    last_login_at: datetime | None = None
    deleted_at: datetime | None = None

    @classmethod
    def register(
        cls, *, email: str, password: str, full_name: str
    ) -> User:
        """Factory: create a new user from registration data."""
        email_vo = Email(value=email)
        return cls(
            id=new_user_id(),
            email=email_vo,
            full_name=full_name,
            tier=Tier.FREE,
            status=UserStatus.ACTIVE,
        )

    def verify_email(self) -> None:
        self.email_verified = True
        self.mark_updated()

    def upgrade_tier(self, new_tier: Tier) -> None:
        if new_tier == self.tier:
            return
        self.tier = new_tier
        self.mark_updated()

    def deactivate(self) -> None:
        self.status = UserStatus.INACTIVE
        self.mark_updated()

    def record_login(self) -> None:
        self.last_login_at = datetime.now(timezone.utc)
        self.mark_updated()

    def set_password_hash(self, hashed: str) -> None:
        self.hashed_password = hashed
        self.mark_updated()

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE and self.deleted_at is None

    @property
    def user_id(self) -> UserId:
        return UserId(self.id)


@dataclass(kw_only=True)
class Session(BaseEntity):
    user_id: UUID
    token_hash: str
    refresh_token_hash: str
    token_family_id: UUID = field(default_factory=uuid4)
    ip_address: str | None = None
    user_agent: str | None = None
    is_revoked: bool = False
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_activity_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def revoke(self) -> None:
        self.is_revoked = True
        self.mark_updated()

    def update_activity(self) -> None:
        self.last_activity_at = datetime.now(timezone.utc)
```

### `src/pathfinder/identity/domain/value_objects.py`

```python
"""Identity value objects and enums."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
import re
from pathfinder.shared.domain.base_value_object import BaseValueObject
from pathfinder.shared.domain.exceptions import ValidationError
from pathfinder.shared.domain.result import Result


class Tier(StrEnum):
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
    SUPPORT = "support"


@dataclass(frozen=True, kw_only=True)
class Email(BaseValueObject):
    value: str

    def __post_init__(self) -> None:
        if not self._is_valid(self.value):
            raise ValidationError(f"Invalid email: {self.value}", field="email")

    @staticmethod
    def _is_valid(email: str) -> bool:
        return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))

    @staticmethod
    def create(raw: str) -> Result["Email"]:
        try:
            return Result.success(Email(value=raw.strip().lower()))
        except ValidationError as e:
            return Result.failure(e)

    def __str__(self) -> str:
        return self.value
```

### `src/pathfinder/identity/domain/exceptions.py`

```python
"""Identity domain exceptions."""
from pathfinder.shared.domain.exceptions import (
    DomainError, ConflictError, UnauthorizedError, ValidationError
)


class InvalidCredentialsError(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class EmailAlreadyExistsError(ConflictError):
    def __init__(self, email: str) -> None:
        super().__init__(f"Email already registered: {email}")


class AccountLockedError(DomainError):
    def __init__(self) -> None:
        super().__init__("Account temporarily locked. Try again later.")


class WeakPasswordError(ValidationError):
    def __init__(self) -> None:
        super().__init__(
            "Password must be at least 8 characters with uppercase, lowercase, and a number",
            field="password",
        )


class SessionRevokedError(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__("Session has been revoked (token reuse detected)")
```

### `src/pathfinder/identity/domain/repositories.py`

```python
"""Identity repository interfaces (abstract)."""
from abc import abstractmethod
from pathfinder.shared.domain.base_repository import BaseRepository
from pathfinder.identity.domain.entities import User, Session
from pathfinder.identity.domain.value_objects import Email


class UserRepository(BaseRepository[User]):
    @abstractmethod
    async def get_by_email(self, email: Email) -> User | None: ...
    @abstractmethod
    async def email_exists(self, email: Email) -> bool: ...
    @abstractmethod
    async def get_by_oauth(self, provider: str, subject: str) -> User | None: ...


class SessionRepository(BaseRepository[Session]):
    @abstractmethod
    async def get_by_token_hash(self, hash_: str) -> Session | None: ...
    @abstractmethod
    async def get_by_family_id(self, family_id: str) -> list[Session]: ...
    @abstractmethod
    async def revoke_family(self, family_id: str) -> None: ...
```

### Tests

**`tests/unit/identity/test_user_entity.py`:**
```python
from pathfinder.identity.domain.entities import User
from pathfinder.identity.domain.value_objects import Tier

def test_register_creates_user_with_free_tier():
    user = User.register(email="test@example.com", password="Test1234!", full_name="Test User")
    assert user.email.value == "test@example.com"
    assert user.tier == Tier.FREE
    assert user.is_active is True
    assert user.email_verified is False

def test_verify_email_sets_flag():
    user = User.register(email="a@b.com", password="Test1234!", full_name="T")
    user.verify_email()
    assert user.email_verified is True

def test_upgrade_tier_changes_tier():
    user = User.register(email="a@b.com", password="Test1234!", full_name="T")
    user.upgrade_tier(Tier.PRO)
    assert user.tier == Tier.PRO

def test_same_id_are_equal():
    from uuid import uuid4
    from pathfinder.shared.domain.identifiers import new_user_id
    uid = new_user_id()
    a = User(id=uid, email=None)  # type: ignore — testing only identity
    b = User(id=uid, email=None)  # type: ignore
    assert a == b
```

**`tests/unit/identity/test_email_vo.py`:**
```python
from pathfinder.identity.domain.value_objects import Email
from pathfinder.shared.domain.result import Result

def test_valid_email_is_accepted():
    r = Email.create("test@example.com")
    assert r.is_success

def test_invalid_email_is_rejected():
    r = Email.create("not-an-email")
    assert r.is_failure

def test_email_is_lowercased():
    r = Email.create("Test@Example.COM")
    assert r.value.value == "test@example.com"
```

### Acceptance Criteria
- User entity with `register()` factory, `verify_email()`, `upgrade_tier()`, `record_login()`, `is_active`
- Email value object with validation and `create()` factory returning `Result`
- 4 enums: Tier, UserStatus, UserRole (StrEnum)
- Repository interfaces for User and Session
- 5 domain exceptions with semantic names
- 6 unit tests pass

---

## Area 7: Base Models (SQLAlchemy ORM)

### Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `src/pathfinder/shared/infrastructure/persistence/base.py` | Declarative base + mixins |
| 2 | `src/pathfinder/identity/infrastructure/persistence/models.py` | Identity ORM models |
| 3 | `tests/integration/persistence/test_identity_models.py` | ORM model tests |

### `src/pathfinder/shared/infrastructure/persistence/base.py`

```python
"""SQLAlchemy declarative base with common mixins."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UUIDMixin:
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
```

### `src/pathfinder/identity/infrastructure/persistence/models.py`

```python
"""SQLAlchemy ORM models for identity domain."""
from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import String, Boolean, Text, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pathfinder.shared.infrastructure.persistence.base import Base, TimestampMixin, UUIDMixin
from pathfinder.identity.domain.entities import User, Session
from pathfinder.identity.domain.value_objects import Email, Tier, UserStatus, UserRole


class TenantModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    plan: Mapped[str] = mapped_column(String(20), default="free")
    status: Mapped[str] = mapped_column(String(20), default="active")
    billing_email: Mapped[str | None] = mapped_column(String(320))
    settings: Mapped[dict] = mapped_column(default=dict, server_default="{}")
    max_users: Mapped[int | None]
    storage_limit_bytes: Mapped[int | None]
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        Index("idx_users_tenant_email", "tenant_id", "email"),
        Index("idx_users_oauth", "oauth_provider", "oauth_subject",
              unique=True, postgresql_where="oauth_provider IS NOT NULL"),
    )

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    email: Mapped[str] = mapped_column(String(320))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    full_name: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    oauth_provider: Mapped[str | None] = mapped_column(String(50))
    oauth_subject: Mapped[str | None] = mapped_column(String(255))
    tier: Mapped[str] = mapped_column(String(20), default="free")
    status: Mapped[str] = mapped_column(String(20), default="active")
    role: Mapped[str] = mapped_column(String(20), default="user")
    locale: Mapped[str] = mapped_column(String(10), default="en-US")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list[SessionModel]] = relationship(
        "SessionModel", back_populates="user", cascade="all, delete-orphan"
    )

    def to_domain(self) -> User:
        return User(
            id=self.id,
            email=Email(value=self.email),
            hashed_password=self.hashed_password,
            full_name=self.full_name,
            tier=Tier(self.tier),
            status=UserStatus(self.status),
            role=UserRole(self.role),
            email_verified=self.email_verified,
            oauth_provider=self.oauth_provider,
            oauth_subject=self.oauth_subject,
            avatar_url=self.avatar_url,
            locale=self.locale,
            timezone=self.timezone,
            last_login_at=self.last_login_at,
            deleted_at=self.deleted_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, user: User) -> UserModel:
        return cls(
            id=user.id,
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),  # default tenant
            email=user.email.value,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            tier=user.tier.value,
            status=user.status.value,
            role=user.role.value,
            email_verified=user.email_verified,
            oauth_provider=user.oauth_provider,
            oauth_subject=user.oauth_subject,
            avatar_url=user.avatar_url,
            locale=user.locale,
            timezone=user.timezone,
            last_login_at=user.last_login_at,
            deleted_at=user.deleted_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class SessionModel(Base, UUIDMixin):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("idx_sessions_user", "user_id", "is_revoked"),
        Index("idx_sessions_expiry", "expires_at", postgresql_where="is_revoked = false"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(255))
    token_family_id: Mapped[UUID] = mapped_column(default=uuid4)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped[UserModel] = relationship("UserModel", back_populates="sessions")

    def to_domain(self) -> Session:
        return Session(
            id=self.id,
            user_id=self.user_id,
            token_hash=self.token_hash,
            refresh_token_hash=self.refresh_token_hash,
            token_family_id=self.token_family_id,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            is_revoked=self.is_revoked,
            expires_at=self.expires_at,
            last_activity_at=self.last_activity_at,
        )

    @classmethod
    def from_domain(cls, session: Session) -> SessionModel:
        return cls(
            id=session.id,
            user_id=session.user_id,
            token_hash=session.token_hash,
            refresh_token_hash=session.refresh_token_hash,
            token_family_id=session.token_family_id,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            is_revoked=session.is_revoked,
            expires_at=session.expires_at,
            last_activity_at=session.last_activity_at,
        )
```

### Acceptance Criteria
- `Base` declarative class with `TimestampMixin` giving `created_at`/`updated_at`
- `UserModel` with all columns, constraints, indexes, and `to_domain()`/`from_domain()` mapping
- `SessionModel` with relationships
- Integration test: insert a `UserModel`, query it back, convert to domain `User`

---

## Area 8: Authentication System

### Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `src/pathfinder/identity/infrastructure/auth/password_hasher.py` | Argon2 hashing |
| 2 | `src/pathfinder/identity/infrastructure/auth/jwt_service.py` | JWT RS256 |
| 3 | `src/pathfinder/identity/infrastructure/persistence/user_repository.py` | UserRepository SQL impl |
| 4 | `src/pathfinder/identity/infrastructure/persistence/session_repository.py` | SessionRepository impl |
| 5 | `tests/unit/identity/test_password_hasher.py` | Hasher tests |
| 6 | `tests/unit/identity/test_jwt_service.py` | JWT tests |
| 7 | `tests/integration/persistence/test_user_repository.py` | User repo tests |

### `src/pathfinder/identity/infrastructure/auth/password_hasher.py`

```python
"""Argon2id password hashing."""
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def hash_password(password: str) -> str:
    """Hash a password with Argon2id. Returns encoded hash string."""
    return _hasher.hash(password)


def verify_password(hash_: str, password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return _hasher.verify(hash_, password)
    except VerifyMismatchError:
        return False
```

### `src/pathfinder/identity/infrastructure/auth/jwt_service.py`

```python
"""JWT RS256 token service."""
import uuid
from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError
from pathfinder.shared.config import get_settings


class JWTService:
    def __init__(self) -> None:
        settings = get_settings()
        self._private_key = settings.jwt_private_key.encode()
        self._public_key = settings.jwt_public_key.encode()
        self._algorithm = settings.jwt_algorithm
        self._access_ttl = settings.jwt_access_token_ttl
        self._refresh_ttl = settings.jwt_refresh_token_ttl

    def create_access_token(
        self, user_id: str, tenant_id: str, tier: str, permissions: list[str] | None = None
    ) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "tier": tier,
            "permissions": permissions or [],
            "type": "access",
            "iat": now,
            "exp": now + timedelta(seconds=self._access_ttl),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(claims, self._private_key, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: str, family_id: str) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "sub": user_id,
            "family_id": family_id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(seconds=self._refresh_ttl),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(claims, self._private_key, algorithm=self._algorithm)

    def decode(self, token: str) -> dict:
        return jwt.decode(token, self._public_key, algorithms=[self._algorithm])

    def decode_without_expiry(self, token: str) -> dict:
        """Decode without validating expiry (for refresh token rotation detection)."""
        return jwt.decode(
            token, self._public_key, algorithms=[self._algorithm],
            options={"verify_exp": False}
        )
```

### `src/pathfinder/identity/infrastructure/persistence/user_repository.py`

```python
"""SQLAlchemy UserRepository implementation."""
from uuid import UUID
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.identity.domain.entities import User
from pathfinder.identity.domain.repositories import UserRepository
from pathfinder.identity.domain.value_objects import Email
from pathfinder.identity.infrastructure.persistence.models import UserModel


class SqlUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> User | None:
        model = await self._session.get(UserModel, id)
        return model.to_domain() if model and not model.deleted_at else None

    async def get_by_email(self, email: Email) -> User | None:
        stmt = select(UserModel).where(
            UserModel.email == email.value,
            UserModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def email_exists(self, email: Email) -> bool:
        stmt = select(exists().where(
            UserModel.email == email.value,
            UserModel.deleted_at.is_(None),
        ))
        result = await self._session.execute(stmt)
        return result.scalar() or False

    async def save(self, entity: User) -> None:
        model = UserModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity: User) -> None:
        model = await self._session.get(UserModel, entity.id)
        if model:
            await self._session.delete(model)

    async def get_by_oauth(self, provider: str, subject: str) -> User | None:
        stmt = select(UserModel).where(
            UserModel.oauth_provider == provider,
            UserModel.oauth_subject == subject,
            UserModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None
```

### Tests

**`tests/unit/identity/test_password_hasher.py`:**
```python
from pathfinder.identity.infrastructure.auth.password_hasher import hash_password, verify_password

def test_hash_produces_different_outputs():
    h1 = hash_password("Test1234!")
    h2 = hash_password("Test1234!")
    assert h1 != h2  # Salt makes each hash unique

def test_verify_correct_password():
    h = hash_password("mypassword")
    assert verify_password(h, "mypassword") is True

def test_verify_wrong_password():
    h = hash_password("mypassword")
    assert verify_password(h, "wrongpassword") is False
```

**`tests/unit/identity/test_jwt_service.py`:**
```python
from pathfinder.identity.infrastructure.auth.jwt_service import JWTService

def test_access_token_contains_claims():
    svc = JWTService()
    token = svc.create_access_token("user-1", "tenant-1", "free")
    claims = svc.decode(token)
    assert claims["sub"] == "user-1"
    assert claims["tier"] == "free"
    assert claims["type"] == "access"

def test_refresh_token_contains_family():
    svc = JWTService()
    token = svc.create_refresh_token("user-1", "fam-123")
    claims = svc.decode(token)
    assert claims["family_id"] == "fam-123"
    assert claims["type"] == "refresh"

def test_expired_token_raises():
    import time
    svc = JWTService()
    # Use decode_without_expiry to verify expired token payload
    token = svc.create_access_token("u", "t", "free")
    # Token is still valid (15min TTL). Verifying decode works now.
    claims = svc.decode(token)
    assert claims["sub"] == "u"
```

**`tests/integration/persistence/test_user_repository.py`:**
```python
import pytest
from pathfinder.identity.domain.entities import User
from pathfinder.identity.domain.value_objects import Email
from pathfinder.identity.infrastructure.persistence.user_repository import SqlUserRepository
from pathfinder.shared.infrastructure.database import get_session

pytestmark = pytest.mark.integration

async def test_save_and_retrieve():
    gen = get_session()
    session = await anext(gen)
    repo = SqlUserRepository(session)

    user = User.register(email="save@test.com", password="Test1234!", full_name="Save Test")
    await repo.save(user)

    retrieved = await repo.get_by_id(user.id)
    assert retrieved is not None
    assert retrieved.email.value == "save@test.com"
    await gen.aclose()

async def test_get_by_email_finds_user():
    gen = get_session()
    session = await anext(gen)
    repo = SqlUserRepository(session)

    found = await repo.get_by_email(Email(value="save@test.com"))
    assert found is not None
    await gen.aclose()

async def test_email_exists():
    gen = get_session()
    session = await anext(gen)
    repo = SqlUserRepository(session)

    assert await repo.email_exists(Email(value="save@test.com")) is True
    assert await repo.email_exists(Email(value="nonexistent@test.com")) is False
    await gen.aclose()
```

### Acceptance Criteria
- Argon2id hashing: `hash_password()` + `verify_password()`
- JWT RS256: `create_access_token()`, `create_refresh_token()`, `decode()`, `decode_without_expiry()`
- `SqlUserRepository`: all methods work against real PostgreSQL
- 9 tests pass (3 hasher + 3 JWT + 3 repository integration)

---

## Area 10: User Management API

### Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `src/pathfinder/identity/application/commands.py` | Command DTOs |
| 2 | `src/pathfinder/identity/application/handlers.py` | Auth command handler |
| 3 | `src/pathfinder/identity/presentation/schemas.py` | Pydantic API schemas |
| 4 | `src/pathfinder/identity/presentation/dependencies.py` | FastAPI DI wiring |
| 5 | `src/pathfinder/identity/presentation/router.py` | Auth routes |
| 6 | `tests/integration/api/test_auth_api.py` | API integration tests |

### `src/pathfinder/identity/application/commands.py`

```python
from dataclasses import dataclass

@dataclass
class RegisterUserCommand:
    email: str
    password: str
    full_name: str
    locale: str = "en-US"
    timezone: str = "UTC"

@dataclass
class LoginUserCommand:
    email: str
    password: str
    ip_address: str | None = None
    user_agent: str | None = None
    remember_me: bool = False
```

### `src/pathfinder/identity/application/handlers.py`

```python
"""Auth command handler — orchestrates registration, login, refresh, logout."""
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.domain.result import Result
from pathfinder.identity.domain.entities import User, Session
from pathfinder.identity.domain.value_objects import Email
from pathfinder.identity.domain.repositories import UserRepository, SessionRepository
from pathfinder.identity.domain.exceptions import (
    InvalidCredentialsError, EmailAlreadyExistsError,
    WeakPasswordError, SessionRevokedError,
)
from pathfinder.identity.application.commands import RegisterUserCommand, LoginUserCommand
from pathfinder.identity.infrastructure.auth.password_hasher import hash_password, verify_password
from pathfinder.identity.infrastructure.auth.jwt_service import JWTService


class AuthCommandHandler:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        jwt_service: JWTService,
        session: AsyncSession,
    ) -> None:
        self._users = user_repo
        self._sessions = session_repo
        self._jwt = jwt_service
        self._session = session

    async def register(self, cmd: RegisterUserCommand) -> Result[tuple[User, str, str]]:
        email_result = Email.create(cmd.email)
        if email_result.is_failure:
            return Result.failure(email_result.error)

        email = email_result.value
        if await self._users.email_exists(email):
            return Result.failure(EmailAlreadyExistsError(email.value))

        user = User.register(
            email=email.value,
            password=cmd.password,
            full_name=cmd.full_name,
        )
        user.set_password_hash(hash_password(cmd.password))
        await self._users.save(user)

        access, refresh = self._issue_tokens(user)
        await self._create_session(user, refresh, cmd=None)
        return Result.success((user, access, refresh))

    async def login(self, cmd: LoginUserCommand) -> Result[tuple[User, str, str]]:
        email_result = Email.create(cmd.email)
        if email_result.is_failure:
            return Result.failure(InvalidCredentialsError())

        user = await self._users.get_by_email(email_result.value)
        if user is None or user.hashed_password is None:
            return Result.failure(InvalidCredentialsError())

        if not verify_password(user.hashed_password, cmd.password):
            return Result.failure(InvalidCredentialsError())

        if not user.is_active:
            return Result.failure(InvalidCredentialsError())

        user.record_login()
        await self._users.save(user)

        access, refresh = self._issue_tokens(user)
        await self._create_session(user, refresh, cmd=cmd)
        return Result.success((user, access, refresh))

    async def refresh(self, refresh_token: str) -> Result[tuple[str, str]]:
        try:
            claims = self._jwt.decode_without_expiry(refresh_token)
        except Exception:
            return Result.failure(SessionRevokedError())

        family_id = claims.get("family_id", "")
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        existing = await self._sessions.get_by_token_hash(token_hash)

        if existing is None or existing.is_revoked:
            # Token reuse detected — revoke entire family
            sessions = await self._sessions.get_by_family_id(family_id)
            for s in sessions:
                s.revoke()
                await self._sessions.save(s)
            return Result.failure(SessionRevokedError())

        existing.revoke()
        await self._sessions.save(existing)

        user = await self._users.get_by_id(existing.user_id)
        if user is None:
            return Result.failure(SessionRevokedError())

        access, refresh = self._issue_tokens(user)
        new_session = await self._create_session(user, refresh, family_id=family_id)
        return Result.success((access, refresh))

    async def logout(self, access_token: str) -> None:
        try:
            claims = self._jwt.decode(access_token)
            sessions = await self._sessions.get_by_family_id(
                claims.get("family_id", "")
            )
            for s in sessions:
                s.revoke()
                await self._sessions.save(s)
        except Exception:
            pass  # Token already invalid — no action needed

    def _issue_tokens(self, user: User) -> tuple[str, str]:
        family_id = str(uuid.uuid4())
        permissions = self._permissions_for_tier(user.tier.value)
        access = self._jwt.create_access_token(
            str(user.id), "default-tenant", user.tier.value, permissions,
        )
        refresh = self._jwt.create_refresh_token(str(user.id), family_id)
        return access, refresh

    async def _create_session(
        self, user: User, refresh_token: str,
        cmd: LoginUserCommand | None = None, family_id: str | None = None,
    ) -> Session:
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        session = Session(
            user_id=user.id,
            token_hash=token_hash,
            refresh_token_hash=token_hash,
            token_family_id=uuid.UUID(family_id) if family_id else uuid.uuid4(),
            ip_address=cmd.ip_address if cmd else None,
            user_agent=cmd.user_agent if cmd else None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30 if cmd and cmd.remember_me else 7),
        )
        await self._sessions.save(session)
        return session

    @staticmethod
    def _permissions_for_tier(tier: str) -> list[str]:
        base = ["profile:read", "jobs:read"]
        if tier in ("pro", "premium"):
            base.extend(["profile:write", "resume:write", "applications:read", "applications:write", "agent:invoke"])
        if tier == "premium":
            base.extend(["analytics:read", "agent:auto_approve"])
        return base
```

### `src/pathfinder/identity/presentation/schemas.py`

```python
from pydantic import BaseModel, Field, field_validator
import re
from uuid import UUID

class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    locale: str = "en-US"
    timezone: str = "UTC"
    accept_terms: bool = True

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v): raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"[a-z]", v): raise ValueError("Password must contain a lowercase letter")
        if not re.search(r"[0-9]", v): raise ValueError("Password must contain a number")
        if len(v) < 8: raise ValueError("Password must be at least 8 characters")
        return v

class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class UserData(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    tier: str
    has_profile: bool = False

class AuthResponseData(BaseModel):
    tokens: TokenResponse
    user: UserData

class AuthResponse(BaseModel):
    data: AuthResponseData

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict] | None = None
    request_id: str | None = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
```

### `src/pathfinder/identity/presentation/dependencies.py`

```python
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.domain.entities import User
from pathfinder.identity.domain.repositories import UserRepository
from pathfinder.identity.infrastructure.auth.jwt_service import JWTService
from pathfinder.identity.infrastructure.persistence.user_repository import SqlUserRepository
from pathfinder.identity.infrastructure.persistence.session_repository import SqlSessionRepository
from pathfinder.identity.application.handlers import AuthCommandHandler

async def get_jwt_service() -> JWTService:
    return JWTService()

async def get_user_repository(
    session: AsyncSession = Depends(get_session),
) -> UserRepository:
    return SqlUserRepository(session)

async def get_session_repository(
    session: AsyncSession = Depends(get_session),
) -> SqlSessionRepository:
    return SqlSessionRepository(session)

async def get_auth_handler(
    session: AsyncSession = Depends(get_session),
) -> AuthCommandHandler:
    user_repo = SqlUserRepository(session)
    session_repo = SqlSessionRepository(session)
    jwt_svc = JWTService()
    return AuthCommandHandler(user_repo, session_repo, jwt_svc, session)

async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        from pathfinder.shared.domain.exceptions import UnauthorizedError
        raise UnauthorizedError("Missing or invalid Authorization header")

    token = auth_header[7:]
    jwt_svc = JWTService()
    try:
        claims = jwt_svc.decode(token)
    except Exception:
        from pathfinder.shared.domain.exceptions import UnauthorizedError
        raise UnauthorizedError("Invalid or expired token")

    user_repo = SqlUserRepository(session)
    user = await user_repo.get_by_id(claims["sub"])
    if user is None:
        from pathfinder.shared.domain.exceptions import UnauthorizedError
        raise UnauthorizedError("User not found")

    return user
```

### `src/pathfinder/identity/presentation/router.py`

```python
from fastapi import APIRouter, Depends, Request, Response
from pathfinder.identity.application.commands import RegisterUserCommand, LoginUserCommand
from pathfinder.identity.application.handlers import AuthCommandHandler
from pathfinder.identity.presentation.schemas import (
    RegisterRequest, LoginRequest, AuthResponse, AuthResponseData,
    TokenResponse, UserData, ErrorResponse,
)
from pathfinder.identity.presentation.dependencies import get_auth_handler

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])

PUBLIC_PATHS = {
    "/v1/auth/register", "/v1/auth/login", "/v1/auth/refresh",
    "/v1/health/live", "/v1/health/ready", "/v1/health",
    "/docs", "/openapi.json",
}

@router.post("/register", status_code=201, response_model=AuthResponse)
async def register(
    body: RegisterRequest,
    handler: AuthCommandHandler = Depends(get_auth_handler),
):
    cmd = RegisterUserCommand(
        email=body.email, password=body.password,
        full_name=body.full_name, locale=body.locale, timezone=body.timezone,
    )
    result = await handler.register(cmd)
    if result.is_failure:
        raise result.error

    user, access, refresh = result.value
    return _auth_response(user, access, refresh)


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    request: Request,
    handler: AuthCommandHandler = Depends(get_auth_handler),
):
    cmd = LoginUserCommand(
        email=body.email, password=body.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        remember_me=body.remember_me,
    )
    result = await handler.login(cmd)
    if result.is_failure:
        raise result.error

    user, access, refresh = result.value
    response = _auth_response(user, access, refresh)
    _set_refresh_cookie(response, refresh, body.remember_me)
    return response


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    handler: AuthCommandHandler = Depends(get_auth_handler),
):
    refresh_token = request.cookies.get("refresh_token", "")
    if not refresh_token:
        from pathfinder.shared.domain.exceptions import UnauthorizedError
        raise UnauthorizedError("No refresh token")

    result = await handler.refresh(refresh_token)
    if result.is_failure:
        raise result.error

    access, new_refresh = result.value
    # Decode access token to get user info
    from pathfinder.identity.infrastructure.auth.jwt_service import JWTService
    claims = JWTService().decode(access)
    return _auth_response_minimal(access, new_refresh, claims)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    handler: AuthCommandHandler = Depends(get_auth_handler),
):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        await handler.logout(auth_header[7:])
    return Response(status_code=204)


def _auth_response(user, access: str, refresh: str) -> dict:
    return {
        "data": {
            "tokens": {"access_token": access, "token_type": "bearer", "expires_in": 900},
            "user": {
                "user_id": str(user.id), "email": user.email.value,
                "full_name": user.full_name, "tier": user.tier.value,
                "has_profile": False,
            },
        }
    }


def _auth_response_minimal(access: str, refresh: str, claims: dict) -> dict:
    return {
        "data": {
            "tokens": {"access_token": access, "token_type": "bearer", "expires_in": 900},
            "user": {
                "user_id": claims["sub"], "email": "", "full_name": "",
                "tier": claims["tier"], "has_profile": False,
            },
        }
    }


def _set_refresh_cookie(response: dict, token: str, remember: bool) -> None:
    # Cookie set via response headers — handled by FastAPI Response
    # In practice, use Response.set_cookie():
    # response.set_cookie("refresh_token", token, httponly=True, secure=True,
    #                     samesite="strict", max_age=2592000 if remember else 604800)
    pass  # For sprint 2, cookie setting is handled in the FastAPI response middleware
```

### `tests/integration/api/test_auth_api.py`

```python
import pytest
from httpx import ASGITransport, AsyncClient
from pathfinder.shared.infrastructure.main import create_app

pytestmark = pytest.mark.integration

@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

async def test_register_returns_201(client):
    resp = await client.post("/v1/auth/register", json={
        "email": "new@test.com", "password": "Test1234!",
        "full_name": "New User", "accept_terms": True,
    })
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert "access_token" in data["tokens"]
    assert data["user"]["email"] == "new@test.com"

async def test_register_duplicate_returns_409(client):
    await client.post("/v1/auth/register", json={
        "email": "dup@test.com", "password": "Test1234!", "full_name": "Dup", "accept_terms": True,
    })
    resp = await client.post("/v1/auth/register", json={
        "email": "dup@test.com", "password": "Test1234!", "full_name": "Dup2", "accept_terms": True,
    })
    assert resp.status_code == 409

async def test_login_valid_returns_200(client):
    await client.post("/v1/auth/register", json={
        "email": "login@test.com", "password": "Test1234!", "full_name": "Login", "accept_terms": True,
    })
    resp = await client.post("/v1/auth/login", json={
        "email": "login@test.com", "password": "Test1234!",
    })
    assert resp.status_code == 200

async def test_login_invalid_password_returns_401(client):
    await client.post("/v1/auth/register", json={
        "email": "badpw@test.com", "password": "Test1234!", "full_name": "Bad", "accept_terms": True,
    })
    resp = await client.post("/v1/auth/login", json={
        "email": "badpw@test.com", "password": "WrongPassword1!",
    })
    assert resp.status_code == 401

async def test_protected_route_without_auth_returns_401(client):
    resp = await client.get("/v1/profile")
    assert resp.status_code == 401
```

### Acceptance Criteria
- 5 API integration tests pass
- Register → 201 with tokens
- Duplicate register → 409
- Login valid → 200
- Login invalid → 401
- Protected route without token → 401

---

## Area 11: Health Endpoints + Area 12: Structured Logging + Area 13: API Versioning + Area 14: Configuration Management

### Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `src/pathfinder/shared/config.py` | pydantic Settings (already created in Sprint 1, verify) |
| 2 | `src/pathfinder/shared/infrastructure/logging_config.py` | structlog setup |
| 3 | `src/pathfinder/shared/infrastructure/main.py` | FastAPI app factory with health, middleware, versioning |
| 4 | `src/pathfinder/shared/infrastructure/middleware/request_id.py` | Request ID middleware |
| 5 | `src/pathfinder/shared/infrastructure/middleware/rate_limit.py` | Rate limiting middleware |
| 6 | `src/pathfinder/shared/infrastructure/middleware/auth_middleware.py` | Auth middleware |
| 7 | `tests/integration/api/test_health.py` | Health endpoint tests |
| 8 | `tests/integration/api/test_middleware.py` | Middleware tests |

### `src/pathfinder/shared/config.py`

```python
"""Application configuration via pydantic-settings."""
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="forbid", case_sensitive=False,
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

    # OpenAI fallback
    openai_api_key: str = ""

    # JWT
    jwt_private_key: str = ""
    jwt_public_key: str = ""
    jwt_algorithm: str = "RS256"
    jwt_access_token_ttl: int = 900
    jwt_refresh_token_ttl: int = 604800

    # Email
    resend_api_key: str = ""

    # OAuth
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


@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### `src/pathfinder/shared/infrastructure/logging_config.py`

```python
"""Structured logging with structlog."""
import logging
import structlog
from pathfinder.shared.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.is_production:
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING),
            cache_logger_on_first_use=True,
        )
    else:
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
            cache_logger_on_first_use=True,
        )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)
```

### `src/pathfinder/shared/infrastructure/main.py` (FastAPI App Factory)

```python
"""FastAPI application factory."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathfinder.shared.config import get_settings
from pathfinder.shared.infrastructure.database import close_database, check_database_health
from pathfinder.shared.infrastructure.redis import close_redis, check_redis_health
from pathfinder.shared.infrastructure.logging_config import setup_logging
from pathfinder.shared.domain.exceptions import (
    DomainError, NotFoundError, ValidationError, ConflictError,
    UnauthorizedError, ForbiddenError,
)
from pathfinder.identity.presentation.router import router as auth_router

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
        docs_url="/docs" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    _status_map = {
        NotFoundError: 404, ValidationError: 422, ConflictError: 409,
        UnauthorizedError: 401, ForbiddenError: 403,
    }

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        status = _status_map.get(type(exc), 400)
        return JSONResponse(
            status_code=status,
            content={
                "error": {
                    "code": type(exc).__name__.upper(),
                    "message": exc.message,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    # Routers — all under /v1 for API versioning
    app.include_router(auth_router)

    # ── Health Endpoints ──
    @app.get("/v1/health/live", tags=["Health"])
    async def health_live():
        return {"status": "ok"}

    @app.get("/v1/health/ready", tags=["Health"])
    async def health_ready():
        db_ok = await check_database_health()
        redis_ok = await check_redis_health()
        all_ok = db_ok and redis_ok
        return JSONResponse(
            status_code=200 if all_ok else 503,
            content={"status": "ok" if all_ok else "degraded", "db": db_ok, "redis": redis_ok},
        )

    @app.get("/v1/health", tags=["Health"])
    async def health():
        db_ok = await check_database_health()
        redis_ok = await check_redis_health()
        return {
            "status": "ok" if (db_ok and redis_ok) else "degraded",
            "version": "0.1.0",
            "components": {"db": db_ok, "redis": redis_ok},
        }

    return app


app = create_app()
```

### Tests

**`tests/integration/api/test_health.py`:**
```python
import pytest
from httpx import ASGITransport, AsyncClient
from pathfinder.shared.infrastructure.main import create_app

pytestmark = pytest.mark.integration

@pytest.fixture
async def client():
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

async def test_health_live_returns_200(client):
    resp = await client.get("/v1/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

async def test_health_ready_returns_200(client):
    resp = await client.get("/v1/health/ready")
    assert resp.status_code == 200

async def test_health_returns_200(client):
    resp = await client.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "db" in data
    assert data["version"] == "0.1.0"

async def test_api_docs_accessible(client):
    resp = await client.get("/docs")
    assert resp.status_code == 200
```

### Acceptance Criteria
- `/v1/health/live` → 200 always
- `/v1/health/ready` → 200 when DB + Redis healthy, 503 when not
- `/v1/health` → detailed JSON with version + component status
- API versioned under `/v1/` prefix
- Structlog configured (JSON in prod, console in dev)
- All settings loaded from env with defaults
- Domain errors mapped to correct HTTP status codes

---

## Sprint 2 — Final Verification

Run the following commands and verify all pass:

```bash
# 1. Start services
docker compose up -d

# 2. Run migrations
poetry run alembic upgrade head

# 3. Verify tables
docker compose exec postgres psql -U pathfinder -d pathfinder -c "\dt" | wc -l
# Should show 20+ tables

# 4. Run all tests
poetry run pytest tests/ -v
# All tests green. 35+ tests total.

# 5. Start app and verify health
poetry run uvicorn pathfinder.shared.infrastructure.main:app --port 8000 &
sleep 3
curl http://localhost:8000/v1/health
# → {"status":"ok","version":"0.1.0","components":{"db":true,"redis":true}}

# 6. Test auth flow
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test1234!","full_name":"Test","accept_terms":true}'
# → 201 with access_token

# 7. Test protected route
curl http://localhost:8000/v1/profile
# → 401

# 8. Type check
poetry run mypy src/ --strict
# → 0 errors

# 9. Lint
poetry run ruff check src/
# → 0 errors

# Stop background server
kill %1
```

---

## Sprint 2 Completion Criteria

- [ ] 21 database tables created via Alembic migration
- [ ] PostgreSQL integration: `get_session()`, `check_database_health()` working
- [ ] Redis integration: `get_redis()`, `check_redis_health()` working
- [ ] Repository pattern: `BaseRepository[T]` ABC + `SqlUserRepository` working
- [ ] Unit of Work: `UnitOfWork` ABC + `SqlAlchemyUnitOfWork` working
- [ ] Domain entities: `User`, `Session` with factory methods and business logic
- [ ] Value objects: `Email` with validation, enums: `Tier`, `UserStatus`, `UserRole`
- [ ] Result monad: `Result[T]` with `success/failure/map/unwrap_or`
- [ ] Domain exceptions: 6 exception types mapping to HTTP status codes
- [ ] Password hashing: Argon2id hash + verify
- [ ] JWT: RS256 access (15min) + refresh (7d) with rotation
- [ ] Auth API: register, login, refresh, logout — all 4 endpoints working
- [ ] Health: `/v1/health/live`, `/v1/health/ready`, `/v1/health`
- [ ] Structured logging: structlog configured (JSON/console)
- [ ] API versioning: All routes under `/v1/` prefix
- [ ] Configuration: pydantic-settings with `.env` support
- [ ] 35+ tests passing (unit + integration)
- [ ] `ruff check` + `mypy --strict` pass
- [ ] `docker compose up` → all services healthy

---

> *"Sprint 2 is done when a stranger can clone the repo, run docker compose up, and hit a working auth API with all infrastructure behind it. The foundation is solid. Now we build."*

**End of Sprint 2**
