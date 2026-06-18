FROM python:3.12-slim AS builder
WORKDIR /app

# Install all runtime dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi>=0.115 \
    "uvicorn[standard]>=0.32" \
    "sqlalchemy[asyncio]>=2.0" \
    asyncpg>=0.29 \
    pgvector>=0.3 \
    "redis[hiredis]>=5.2" \
    celery>=5.4 \
    langgraph>=0.3 \
    langgraph-checkpoint-postgres>=0.1 \
    pydantic>=2.9 \
    pydantic-settings>=2.6 \
    httpx>=0.28 \
    python-multipart>=0.0 \
    structlog>=24.4 \
    tenacity>=9.0 \
    "python-jose[cryptography]>=3.3" \
    argon2-cffi>=23.1 \
    alembic>=1.14 \
    PyPDF2>=3.0 \
    python-docx>=1.1 \
    sentry-sdk>=2.19 \
    prometheus-client>=0.21 \
    jsonschema>=4.23 \
    tiktoken>=0.7

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN groupadd -r pathfinder && useradd -r -g pathfinder pathfinder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ ./src/
COPY alembic.ini .
COPY alembic/ ./alembic/
RUN chown -R pathfinder:pathfinder /app
ENV PYTHONPATH=/app/src
USER pathfinder
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/v1/health/live')"
CMD ["uvicorn", "pathfinder.shared.infrastructure.main:app", "--host", "0.0.0.0", "--port", "8000"]
