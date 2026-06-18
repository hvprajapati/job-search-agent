FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction --no-ansi

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN groupadd -r pathfinder && useradd -r -g pathfinder pathfinder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ ./src/
COPY alembic.ini .
COPY alembic/ ./alembic/
RUN chown -R pathfinder:pathfinder /app
USER pathfinder
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/v1/health/live')"
CMD ["uvicorn", "pathfinder.shared.infrastructure.main:app", "--host", "0.0.0.0", "--port", "8000"]
