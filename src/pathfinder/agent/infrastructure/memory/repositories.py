"""Memory repository implementations."""
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.agent.infrastructure.memory.models import EpisodicMemoryModel, SemanticMemoryModel


class SqlEpisodicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, model: EpisodicMemoryModel) -> None:
        self._session.add(model)
        await self._session.flush()

    async def list_recent(self, user_id: UUID, limit: int = 20) -> list[EpisodicMemoryModel]:
        stmt = (select(EpisodicMemoryModel)
                .where(EpisodicMemoryModel.user_id == user_id)
                .order_by(EpisodicMemoryModel.created_at.desc())
                .limit(limit))
        result = await self._session.execute(stmt)
        return list(result.scalars())

    async def list_unconsolidated(self, user_id: UUID, limit: int = 500) -> list[EpisodicMemoryModel]:
        stmt = (select(EpisodicMemoryModel)
                .where(EpisodicMemoryModel.user_id == user_id,
                       EpisodicMemoryModel.is_consolidated == False)
                .order_by(EpisodicMemoryModel.created_at.asc())
                .limit(limit))
        result = await self._session.execute(stmt)
        return list(result.scalars())

    async def mark_consolidated(self, episode_ids: list[UUID], run_id: UUID) -> int:
        stmt = (update(EpisodicMemoryModel)
                .where(EpisodicMemoryModel.id.in_(episode_ids))
                .values(is_consolidated=True, consolidation_run_id=run_id))
        result = await self._session.execute(stmt)
        return result.rowcount or 0


class SqlSemanticRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, model: SemanticMemoryModel) -> None:
        await self._session.merge(model)
        await self._session.flush()

    async def get_by_subject(self, user_id: UUID, subject: str) -> SemanticMemoryModel | None:
        stmt = select(SemanticMemoryModel).where(
            SemanticMemoryModel.user_id == user_id,
            SemanticMemoryModel.subject == subject,
            SemanticMemoryModel.is_active == True,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_by_type(self, user_id: UUID, memory_type: str | None = None,
                             limit: int = 20) -> list[SemanticMemoryModel]:
        stmt = select(SemanticMemoryModel).where(
            SemanticMemoryModel.user_id == user_id,
            SemanticMemoryModel.is_active == True,
        )
        if memory_type:
            stmt = stmt.where(SemanticMemoryModel.memory_type == memory_type)
        stmt = stmt.order_by(SemanticMemoryModel.importance.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars())

    async def search_by_embedding(self, user_id: UUID, query_embedding: list[float],
                                  limit: int = 10) -> list[SemanticMemoryModel]:
        stmt = (select(SemanticMemoryModel)
                .where(SemanticMemoryModel.user_id == user_id,
                       SemanticMemoryModel.is_active == True,
                       SemanticMemoryModel.embedding.is_not(None),
                       SemanticMemoryModel.importance >= 0.2)
                .order_by(SemanticMemoryModel.embedding.cosine_distance(query_embedding))
                .limit(limit))
        result = await self._session.execute(stmt)
        return list(result.scalars())
