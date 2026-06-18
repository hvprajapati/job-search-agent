.PHONY: help install lint format typecheck test docker-up docker-down clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies with pip
	pip install -e .[dev]

lint:  ## Run linter
	ruff check src/ tests/

format:  ## Format code
	black src/ tests/
	ruff check --fix src/ tests/

typecheck:  ## Run type checker
	mypy src/

test:  ## Run tests
	pytest tests/ -v

docker-up:  ## Start Docker services
	docker compose up -d

docker-down:  ## Stop Docker services
	docker compose down

migrate:  ## Run database migrations
	alembic upgrade head

clean:  ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml dist/ build/
