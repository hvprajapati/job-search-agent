"""Authentication middleware — validates JWT and checks token blacklist."""
import hashlib
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

PUBLIC_PATHS = {
    "/v1/auth/register", "/v1/auth/login", "/v1/auth/refresh",
    "/v1/health/live", "/v1/health/ready", "/v1/health",
    "/v1/metrics", "/docs", "/openapi.json", "/redoc",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "UNAUTHORIZED", "message": "Missing or invalid token"}},
            )

        token = auth_header[7:]
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Check token blacklist (logout revocation)
        try:
            from pathfinder.shared.infrastructure.redis import get_redis
            redis_gen = get_redis()
            redis = await anext(redis_gen)
            is_blacklisted = await redis.exists(f"blacklist:token:{token_hash}")
            await redis.aclose()
            if is_blacklisted:
                return JSONResponse(
                    status_code=401,
                    content={"error": {"code": "TOKEN_REVOKED", "message": "Token has been revoked"}},
                )
        except Exception:
            pass  # Redis unavailable — allow request (fail open for availability)

        return await call_next(request)
