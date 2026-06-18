"""SQLAlchemy ResumeRepository implementation."""
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.profile.domain.entities import Resume
from pathfinder.profile.infrastructure.persistence.models import ResumeModel


class SqlResumeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Resume | None:
        model = await self._session.get(ResumeModel, id)
        return model.to_domain() if model else None

    async def get_by_user_and_id(self, user_id: UUID, resume_id: UUID) -> Resume | None:
        stmt = select(ResumeModel).where(
            ResumeModel.user_id == user_id, ResumeModel.id == resume_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def list_by_user(self, user_id: UUID, *, is_base: bool | None = None,
                           limit: int = 20) -> list[Resume]:
        stmt = select(ResumeModel).where(ResumeModel.user_id == user_id)
        if is_base is not None:
            stmt = stmt.where(ResumeModel.is_base == is_base)
        stmt = stmt.order_by(ResumeModel.updated_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def save(self, entity: Resume) -> None:
        model = ResumeModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity: Resume) -> None:
        model = await self._session.get(ResumeModel, entity.id)
        if model:
            await self._session.delete(model)
