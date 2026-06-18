"""SQLAlchemy UserRepository implementation."""
from uuid import UUID
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.identity.domain.entities import User
from pathfinder.identity.domain.value_objects import Email
from pathfinder.identity.infrastructure.persistence.models import UserModel


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> User | None:
        model = await self._session.get(UserModel, id)
        return model.to_domain() if model and not model.deleted_at else None

    async def get_by_email(self, email: Email) -> User | None:
        stmt = select(UserModel).where(
            UserModel.email == email.value,
            UserModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def email_exists(self, email: Email) -> bool:
        stmt = select(exists().where(
            UserModel.email == email.value,
            UserModel.deleted_at.is_(None),
        ))
        result = await self._session.execute(stmt)
        return result.scalar() or False

    async def save(self, user: User) -> None:
        model = UserModel.from_domain(user)
        await self._session.merge(model)
        await self._session.flush()

    async def get_by_oauth(self, provider: str, subject: str) -> User | None:
        stmt = select(UserModel).where(
            UserModel.oauth_provider == provider,
            UserModel.oauth_subject == subject,
            UserModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None
