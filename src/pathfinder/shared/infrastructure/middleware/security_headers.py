"""Security headers middleware."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


DOCS_PATHS = {"/docs", "/openapi.json", "/redoc"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Allow CDN assets for Swagger UI docs
        if request.url.path in DOCS_PATHS or request.url.path.startswith("/docs"):
            response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' cdn.jsdelivr.net; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net"
        else:
            response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response
