"""First-startup bootstrap — auto-generates dev keys, validates configuration."""
import os
import logging
from pathlib import Path
from pathfinder.shared.config import get_settings

logger = logging.getLogger(__name__)

DEV_JWT_SECRET = "pathfinder-dev-secret-change-in-production-min-32-chars!!"


class BootstrapReport:
    def __init__(self):
        self.checks: list[dict] = []
        self.all_passed = True

    def add(self, name: str, passed: bool, message: str):
        self.checks.append({"name": name, "passed": passed, "message": message})
        if not passed:
            self.all_passed = False

    def to_dict(self) -> dict:
        return {"all_passed": self.all_passed, "checks": self.checks}


async def run_startup_checks() -> BootstrapReport:
    report = BootstrapReport()
    from pathfinder.shared.config import get_settings
    settings = get_settings()

    # 1. Database connectivity
    try:
        from pathfinder.shared.infrastructure.database import check_database_health
        db_ok = await check_database_health()
        report.add("database", db_ok, "Connected" if db_ok else "Cannot connect to PostgreSQL")
    except Exception as e:
        report.add("database", False, str(e)[:120])

    # 2. Redis connectivity
    try:
        from pathfinder.shared.infrastructure.redis import check_redis_health
        redis_ok = await check_redis_health()
        report.add("redis", redis_ok, "Connected" if redis_ok else "Cannot connect to Redis")
    except Exception as e:
        report.add("redis", False, str(e)[:120])

    # 3. Migration status
    try:
        from pathfinder.shared.infrastructure.database import get_sessionmaker
        maker = get_sessionmaker()
        async with maker() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"))
            tables_exist = result.scalar()
            if tables_exist:
                result2 = await session.execute(text("SELECT version_num FROM _alembic_version LIMIT 1"))
                version = result2.scalar()
                report.add("migrations", True, f"Applied — version {version}")
            else:
                report.add("migrations", False, "No tables found — run 'alembic upgrade head'")
    except Exception as e:
        report.add("migrations", False, str(e)[:120])

    # 4. JWT configuration
    if settings.is_production:
        has_keys = bool(settings.jwt_private_key and settings.jwt_public_key)
        report.add("jwt", has_keys, "Keys configured" if has_keys else "JWT keys required in production")
    else:
        report.add("jwt", True, "Development mode — keys auto-generated if needed")

    # 5. DeepSeek configuration
    api_configured = bool(settings.deepseek_api_key and settings.deepseek_api_key != "sk-your-key-here")
    report.add("deepseek", api_configured,
               "API key configured" if api_configured else "API key not set — AI features will run in degraded mode")

    # 5b. Local embeddings
    try:
        from pathfinder.shared.infrastructure.embedding_service import is_available as embed_available
        if embed_available():
            from pathfinder.shared.infrastructure.embedding_service import VECTOR_DIM
            report.add("embeddings", True, f"Local model loaded ({VECTOR_DIM}d)")
        else:
            report.add("embeddings", False, "Local embedding model not loaded")
    except Exception as e:
        report.add("embeddings", False, str(e)[:80])

    # 6. LLM health
    try:
        from pathfinder.shared.infrastructure.llm_health import llm_health
        report.add("llm_circuit", True, f"Status: {llm_health.status.value}")
    except Exception as e:
        report.add("llm_circuit", False, str(e)[:120])

    return report


def bootstrap_jwt_keys():
    """Auto-generate development JWT keys if not configured and not in production."""
    settings = get_settings()
    if settings.is_production:
        return  # Never auto-generate in production

    if not settings.jwt_private_key or not settings.jwt_public_key:
        logger.info("DEVELOPMENT: Auto-generating JWT keys (HS256 + shared secret)")
        os.environ["JWT_ALGORITHM"] = "HS256"
        os.environ["JWT_PRIVATE_KEY"] = DEV_JWT_SECRET
        os.environ["JWT_PUBLIC_KEY"] = DEV_JWT_SECRET
        # Clear lru_cache so Settings re-reads from environment
        get_settings.cache_clear()  # get_settings imported at module level
        logger.info("JWT bootstrap complete — using HS256 with dev secret")
