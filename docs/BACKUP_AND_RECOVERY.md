# Backup & Disaster Recovery

## Automated Backups (Managed PostgreSQL)
Daily automated backups with 30-day retention. Point-in-time recovery via WAL archiving.

## Manual Backup
```bash
pg_dump -Fc pathfinder > backup_$(date +%Y%m%d_%H%M).dump
```

## Restore
```bash
pg_restore -d pathfinder --clean backup_20260101_0300.dump
```

## Point-in-Time Recovery
```bash
pgbackrest --stanza=main --type=time --target="2026-01-01 14:30:00" restore
```

## Verification
Monthly restore test: restore latest backup to staging, run smoke tests (GET /v1/health/ready), verify row counts on core tables.

## Disaster Recovery
1. Provision new PostgreSQL instance
2. Restore from latest backup
3. Update DATABASE_URL in environment
4. Restart application
5. Verify /v1/health/ready returns 200
6. Expected RTO: <4 hours
