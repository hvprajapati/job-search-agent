"""SQLAlchemy TailoredResumeRepository implementation."""
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.profile.domain.tailoring.entities import TailoredResume
from pathfinder.profile.domain.tailoring.repositories import TailoredResumeRepository
from pathfinder.profile.infrastructure.persistence.tailored_resume_models import TailoredResumeModel


class SqlTailoredResumeRepository(TailoredResumeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> TailoredResume | None:
        model = await self._session.get(TailoredResumeModel, id)
        return model.to_domain() if model else None

    async def save(self, entity: TailoredResume) -> None:
        model = TailoredResumeModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity: TailoredResume) -> None:
        model = await self._session.get(TailoredResumeModel, entity.id)
        if model:
            model.is_active = False

    async def get_latest_for_job(self, user_id: UUID, job_id: UUID) -> TailoredResume | None:
        stmt = (
            select(TailoredResumeModel)
            .where(
                TailoredResumeModel.user_id == user_id,
                TailoredResumeModel.job_id == job_id,
                TailoredResumeModel.is_active == True,
            )
            .order_by(TailoredResumeModel.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def list_by_user(self, user_id: UUID, *, job_id: UUID | None = None,
                           limit: int = 20) -> list[TailoredResume]:
        stmt = select(TailoredResumeModel).where(
            TailoredResumeModel.user_id == user_id,
            TailoredResumeModel.is_active == True,
        )
        if job_id:
            stmt = stmt.where(TailoredResumeModel.job_id == job_id)
        stmt = stmt.order_by(TailoredResumeModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def list_versions(self, base_resume_id: UUID, job_id: UUID) -> list[TailoredResume]:
        stmt = (
            select(TailoredResumeModel)
            .where(
                TailoredResumeModel.base_resume_id == base_resume_id,
                TailoredResumeModel.job_id == job_id,
                TailoredResumeModel.is_active == True,
            )
            .order_by(TailoredResumeModel.version.desc())
        )
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def get_by_user_and_id(self, user_id: UUID, tailored_id: UUID) -> TailoredResume | None:
        stmt = select(TailoredResumeModel).where(
            TailoredResumeModel.user_id == user_id,
            TailoredResumeModel.id == tailored_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None
