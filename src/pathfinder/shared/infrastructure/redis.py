"""Redis async integration."""
from __future__ import annotations
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
