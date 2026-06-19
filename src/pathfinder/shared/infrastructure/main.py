"""FastAPI application factory — all routers registered here."""
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
from pathfinder.profile.presentation.router import router as profile_router
from pathfinder.profile.presentation.tailoring_router import router as tailoring_router
from pathfinder.jobs.presentation.router import router as jobs_router
from pathfinder.jobs.presentation.matching_router import router as matching_router
from pathfinder.agent.presentation.router import router as agent_router
from pathfinder.knowledge.presentation.router import router as knowledge_router
from pathfinder.tracking.presentation.router import router as tracking_router
from pathfinder.admin.presentation.router import router as admin_router
from pathfinder.shared.infrastructure.middleware.request_id import RequestIdMiddleware
from pathfinder.shared.infrastructure.middleware.security_headers import SecurityHeadersMiddleware
from pathfinder.shared.infrastructure.middleware.rate_limit import RateLimitMiddleware
from pathfinder.shared.infrastructure.middleware.auth import AuthMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    from pathfinder.shared.infrastructure.bootstrap import bootstrap_jwt_keys, run_startup_checks
    bootstrap_jwt_keys()
    report = await run_startup_checks()
    logger = __import__('logging').getLogger(__name__)
    if not report.all_passed:
        logger.warning("Startup checks failed — see /v1/health/startup for details")
        for c in report.checks:
            if not c["passed"]:
                logger.warning(f"  {c['name']}: {c['message']}")
    from pathfinder.shared.infrastructure.tenant import ensure_default_tenant_exists
    try:
        await ensure_default_tenant_exists()
    except Exception as e:
        logger.error(f"Default tenant check failed (migrations may not be applied): {e}")
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

    app.add_middleware(AuthMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)

    _status_map = {
        NotFoundError: 404, ValidationError: 422, ConflictError: 409,
        UnauthorizedError: 401, ForbiddenError: 403,
    }

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        status = 400
        for cls in type(exc).__mro__:
            if cls in _status_map:
                status = _status_map[cls]
                break
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

    # Register all routers
    app.include_router(auth_router)
    app.include_router(profile_router)
    app.include_router(tailoring_router)
    app.include_router(jobs_router)
    app.include_router(matching_router)
    app.include_router(agent_router)
    app.include_router(knowledge_router)
    app.include_router(tracking_router)
    app.include_router(admin_router)

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

    @app.get("/v1/health/startup", tags=["Health"])
    async def startup_health():
        from pathfinder.shared.infrastructure.bootstrap import run_startup_checks
        report = await run_startup_checks()
        return report.to_dict()

    @app.get("/v1/metrics", tags=["Observability"])
    async def metrics_endpoint():
        from pathfinder.shared.infrastructure.metrics import metrics as m
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=m.get_metrics(), media_type="text/plain")

    @app.get("/v1/health", tags=["Health"])
    async def health():
        db_ok = await check_database_health()
        redis_ok = await check_redis_health()
        from pathfinder.shared.infrastructure.llm_health import llm_health
        llm_status = llm_health.metrics
        all_ok = db_ok and redis_ok and llm_health.status.value != "unavailable"
        return {
            "status": "ok" if all_ok else "degraded",
            "version": "0.1.0",
            "components": {"db": db_ok, "redis": redis_ok, "llm": llm_status},
        }

    return app


app = create_app()
