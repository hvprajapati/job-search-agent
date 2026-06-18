# Pathfinder Deployment Guide

## Prerequisites
- Docker 26+ & Docker Compose
- PostgreSQL 16 with pgvector
- Redis 7
- DeepSeek API key
- Domain with DNS configured

## Quick Start (Single VM)

```bash
git clone https://github.com/pathfinder/pathfinder.git
cd pathfinder
cp .env.example .env
# Edit .env with production values
docker compose -f docker-compose.prod.yml up -d
alembic upgrade head
```

## Environment Variables

See `.env.example` for all variables. Required for production:
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `DEEPSEEK_API_KEY` — DeepSeek API key
- `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` — RSA key pair

## Health Checks
```
GET /v1/health/live   → 200 (process alive)
GET /v1/health/ready  → 200 (DB + Redis healthy)
GET /v1/health        → Detailed component status
GET /v1/metrics       → Prometheus metrics
```

## Migration
```bash
alembic upgrade head    # Apply all migrations
alembic downgrade -1    # Rollback last migration
alembic history         # View migration history
```

## Rollback
```bash
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d  # Uses previous image tag
alembic downgrade -1  # If migration rollback needed
```

## Backup
```bash
pg_dump -Fc pathfinder > backup_$(date +%Y%m%d).dump
# Restore: pg_restore -d pathfinder backup_20260101.dump
```
