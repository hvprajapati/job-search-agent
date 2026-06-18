"""Rate limiting middleware — Redis sliding window, tier-based."""
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from pathfinder.shared.infrastructure.redis import get_redis

TIER_LIMITS = {"free": 100, "pro": 300, "premium": 1000}
ENDPOINT_OVERRIDES = {
    "/v1/agent/execute": {"free": 20, "pro": 50, "premium": 200},
    "/v1/auth/login": {"free": 10, "pro": 10, "premium": 10},
    "/v1/auth/register": {"free": 5, "pro": 5, "premium": 5},
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        user_id = getattr(request.state, "user_id", None)
        tier = getattr(request.state, "tier", "free")
        key = f"rate:{user_id or request.client.host}:{path}"

        limit = ENDPOINT_OVERRIDES.get(path, {}).get(tier, TIER_LIMITS.get(tier, 100))
        window = 60

        try:
            redis_gen = get_redis()
            redis = await anext(redis_gen)
            current = await redis.get(key)
            count = int(current or 0)
            if count >= limit:
                ttl = await redis.ttl(key)
                await redis.aclose()
                return Response(
                    content='{"error":{"code":"RATE_LIMIT_EXCEEDED","message":"Too many requests"}}',
                    status_code=429,
                    headers={"Retry-After": str(max(1, ttl)), "Content-Type": "application/json"},
                )
            pipe = redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            await pipe.execute()
            await redis.aclose()
        except Exception:
            pass

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - 1))
        return response
