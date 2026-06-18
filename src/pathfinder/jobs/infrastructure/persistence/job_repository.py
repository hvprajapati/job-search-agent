"""SQLAlchemy JobRepository implementation."""
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.jobs.domain.entities import JobPosting
from pathfinder.jobs.infrastructure.persistence.models import JobPostingModel

VALID_SORT_FIELDS = {"first_seen_at", "last_seen_at", "title", "salary_max"}


class SqlJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> JobPosting | None:
        model = await self._session.get(JobPostingModel, id)
        return model.to_domain() if model else None

    async def get_by_canonical_id(self, canonical_id: str) -> JobPosting | None:
        stmt = select(JobPostingModel).where(JobPostingModel.canonical_job_id == canonical_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def save(self, entity: JobPosting) -> None:
        model = JobPostingModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def search(self, *, query: str | None = None, filters: dict | None = None,
                     sort: str = "-first_seen_at", limit: int = 20,
                     ) -> tuple[list[JobPosting], str | None, int]:
        stmt = select(JobPostingModel).where(JobPostingModel.is_active == True)
        count_stmt = select(func.count()).select_from(JobPostingModel).where(JobPostingModel.is_active == True)

        filters = filters or {}
        if query:
            ts_query = func.plainto_tsquery("english", query)
            stmt = stmt.where(
                func.to_tsvector("english", JobPostingModel.description_clean).op("@@")(ts_query)
            )
            count_stmt = count_stmt.where(
                func.to_tsvector("english", JobPostingModel.description_clean).op("@@")(ts_query)
            )
        if "remote_policy" in filters:
            stmt = stmt.where(JobPostingModel.remote_policy == filters["remote_policy"])
        if "seniority" in filters:
            stmt = stmt.where(JobPostingModel.seniority == filters["seniority"])
        if "company_id" in filters:
            stmt = stmt.where(JobPostingModel.company_id == filters["company_id"])
        if "salary_min" in filters:
            stmt = stmt.where(JobPostingModel.salary_min >= filters["salary_min"])
        if "source_type" in filters:
            stmt = stmt.where(JobPostingModel.source_type == filters["source_type"])

        col = sort.lstrip("-")
        if col in VALID_SORT_FIELDS:
            order_col = getattr(JobPostingModel, col)
            stmt = stmt.order_by(order_col.desc() if sort.startswith("-") else order_col.asc())
        else:
            stmt = stmt.order_by(JobPostingModel.first_seen_at.desc())

        stmt = stmt.limit(limit + 1)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        has_more = len(models) > limit
        next_cursor = str(models[-1].id) if has_more else None

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        return [m.to_domain() for m in (models[:limit] if has_more else models)], next_cursor, total

    async def list_active(self, *, limit: int = 100) -> list[JobPosting]:
        stmt = select(JobPostingModel).where(
            JobPostingModel.is_active == True,
        ).order_by(JobPostingModel.first_seen_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def mark_stale_jobs(self, older_than_days: int = 30) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        stmt = (
            update(JobPostingModel)
            .where(JobPostingModel.last_seen_at < cutoff, JobPostingModel.is_active == True)
            .values(is_active=False, expires_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount or 0
