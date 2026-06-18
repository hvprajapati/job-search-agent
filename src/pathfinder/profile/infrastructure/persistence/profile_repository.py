"""SQLAlchemy ProfileRepository implementation."""
from __future__ import annotations
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.profile.domain.entities import Profile
from pathfinder.profile.infrastructure.persistence.models import ProfileModel


class SqlProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Profile | None:
        model = await self._session.get(ProfileModel, id)
        return model.to_domain() if model and model.is_active else None

    async def get_by_user_id(self, user_id: UUID) -> Profile | None:
        stmt = select(ProfileModel).where(
            ProfileModel.user_id == user_id,
            ProfileModel.is_active == True,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def save(self, profile: Profile) -> None:
        model = ProfileModel.from_domain(profile)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, profile: Profile) -> None:
        await self._session.execute(
            update(ProfileModel)
            .where(ProfileModel.id == profile.id)
            .values(is_active=False)
        )

    async def list_versions(self, user_id: UUID) -> list[dict]:
        stmt = (
            select(ProfileModel.version, ProfileModel.updated_at)
            .where(ProfileModel.user_id == user_id)
            .order_by(ProfileModel.version.desc())
        )
        result = await self._session.execute(stmt)
        return [
            {"version": row[0], "updated_at": row[1].isoformat()}
            for row in result
        ]
