# Contributing to Pathfinder

## Development Setup
```bash
git clone https://github.com/pathfinder/pathfinder.git
cd pathfinder
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
docker compose up -d postgres redis
alembic upgrade head
```

## Code Standards
- Python 3.12+, type hints required (`mypy --strict`)
- Format: `black --line-length 100`
- Lint: `ruff check src/ tests/`
- Tests: `pytest tests/ -v`

## Architecture
Clean Architecture + Domain-Driven Design. Four layers per module:
- `domain/` — Entities, value objects, repository interfaces (pure Python)
- `application/` — Use cases, commands, queries, ports
- `infrastructure/` — SQLAlchemy, Redis, DeepSeek, Celery implementations
- `presentation/` — FastAPI routers, Pydantic schemas

## Pull Requests
1. Branch from `main`
2. Write tests for new code
3. Run `make check` (lint + typecheck + test)
4. Keep PRs under 400 lines
5. Use conventional commits
