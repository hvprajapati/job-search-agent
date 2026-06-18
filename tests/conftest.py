"""Root test configuration — PostgreSQL required for integration tests.

Set TEST_DATABASE_URL env var or use default localhost PostgreSQL.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import asyncio
from httpx import ASGITransport, AsyncClient

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://pathfinder:pathfinder_dev@localhost:5432/pathfinder_test",
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Ensure test environment variables are set before any imports."""
    os.environ.setdefault("APP_ENV", "local")
    os.environ.setdefault("APP_DEBUG", "false")
    os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("DEEPSEEK_API_KEY", "")
    os.environ.setdefault("JWT_ALGORITHM", "HS256")
    os.environ.setdefault("JWT_PRIVATE_KEY", "test-secret-key-for-testing-only")
    os.environ.setdefault("JWT_PUBLIC_KEY", "test-secret-key-for-testing-only")


def _check_db():
    """Check if test database is accessible."""
    try:
        import asyncpg
        import asyncio
        async def _ping():
            conn = await asyncpg.connect(TEST_DATABASE_URL, timeout=3)
            await conn.close()
        asyncio.get_event_loop().run_until_complete(_ping())
        return True
    except Exception:
        return False


DB_AVAILABLE = _check_db()


@pytest.fixture
async def app():
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL not available — set TEST_DATABASE_URL")
    from pathfinder.shared.infrastructure.main import create_app
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_headers(client):
    """Register a test user and return auth headers."""
    email = f"test-{os.urandom(4).hex()}@example.com"
    resp = await client.post("/v1/auth/register", json={
        "email": email,
        "password": "Test1234!",
        "full_name": "Test User",
        "accept_terms": True,
    })
    if resp.status_code != 201:
        pytest.skip(f"Cannot register test user (status={resp.status_code}): {resp.text[:200]}")
    data = resp.json()["data"]
    token = data["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
