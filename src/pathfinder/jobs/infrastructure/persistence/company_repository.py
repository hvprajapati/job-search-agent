"""SQLAlchemy CompanyRepository implementation."""
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.jobs.domain.entities import Company
from pathfinder.jobs.infrastructure.persistence.models import CompanyModel


class SqlCompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Company | None:
        model = await self._session.get(CompanyModel, id)
        return model.to_domain() if model else None

    async def get_by_canonical_name(self, canonical_name: str) -> Company | None:
        stmt = select(CompanyModel).where(CompanyModel.canonical_name == canonical_name)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def save(self, entity: Company) -> None:
        model = CompanyModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def get_or_create(self, name: str) -> Company:
        canonical = name.strip().lower()
        existing = await self.get_by_canonical_name(canonical)
        if existing:
            return existing
        company = Company.create(name=name.strip())
        await self.save(company)
        return company

    async def search(self, *, query: str | None = None, limit: int = 20) -> list[Company]:
        stmt = select(CompanyModel)
        if query:
            stmt = stmt.where(CompanyModel.name.ilike(f"%{query}%"))
        stmt = stmt.order_by(CompanyModel.name.asc()).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]
