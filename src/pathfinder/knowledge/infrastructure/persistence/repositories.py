"""SQLAlchemy knowledge repository implementations."""
from uuid import UUID
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.knowledge.domain.entities import KnowledgeChunk, KnowledgeDocument
from pathfinder.knowledge.domain.repositories import KnowledgeDocumentRepository, KnowledgeChunkRepository
from pathfinder.knowledge.domain.value_objects import RetrievalQuery, RetrievalResult
from pathfinder.knowledge.infrastructure.persistence.models import KnowledgeDocumentModel, KnowledgeChunkModel


class SqlKnowledgeDocumentRepository(KnowledgeDocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> KnowledgeDocument | None:
        model = await self._session.get(KnowledgeDocumentModel, id)
        return model.to_domain() if model else None

    async def save(self, entity: KnowledgeDocument) -> None:
        model = KnowledgeDocumentModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity: KnowledgeDocument) -> None:
        model = await self._session.get(KnowledgeDocumentModel, entity.id)
        if model:
            await self._session.delete(model)

    async def get_by_source(self, source_type: str, source_id: str) -> KnowledgeDocument | None:
        stmt = select(KnowledgeDocumentModel).where(
            KnowledgeDocumentModel.source_type == source_type,
            KnowledgeDocumentModel.source_id == source_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def list_by_user(self, user_id: UUID, limit: int = 50) -> list[KnowledgeDocument]:
        stmt = select(KnowledgeDocumentModel).where(
            KnowledgeDocumentModel.user_id == user_id,
        ).order_by(KnowledgeDocumentModel.updated_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]


class SqlKnowledgeChunkRepository(KnowledgeChunkRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> KnowledgeChunk | None:
        model = await self._session.get(KnowledgeChunkModel, id)
        return model.to_domain() if model else None

    async def save(self, entity: KnowledgeChunk) -> None:
        model = KnowledgeChunkModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity: KnowledgeChunk) -> None:
        model = await self._session.get(KnowledgeChunkModel, entity.id)
        if model:
            await self._session.delete(model)

    async def save_batch(self, chunks: list[KnowledgeChunk]) -> None:
        models = [KnowledgeChunkModel.from_domain(c) for c in chunks]
        self._session.add_all(models)
        await self._session.flush()

    async def delete_by_document(self, document_id: UUID) -> int:
        result = await self._session.execute(
            delete(KnowledgeChunkModel).where(KnowledgeChunkModel.document_id == document_id)
        )
        return result.rowcount or 0

    async def vector_search(self, *, query_embedding: list[float], user_id: UUID,
                            limit: int = 50) -> list[KnowledgeChunk]:
        stmt = select(KnowledgeChunkModel).where(
            KnowledgeChunkModel.user_id == user_id,
            KnowledgeChunkModel.is_active == True,
            KnowledgeChunkModel.embedding.is_not(None),
        ).order_by(KnowledgeChunkModel.embedding.cosine_distance(query_embedding)).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def keyword_search(self, *, query: str, user_id: UUID,
                             limit: int = 50) -> list[KnowledgeChunk]:
        ts_query = func.plainto_tsquery("english", query)
        stmt = select(KnowledgeChunkModel).where(
            KnowledgeChunkModel.user_id == user_id,
            KnowledgeChunkModel.is_active == True,
            KnowledgeChunkModel.content_tsv.op("@@")(ts_query),
        ).order_by(func.ts_rank(KnowledgeChunkModel.content_tsv, ts_query).desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def hybrid_search(self, *, query: RetrievalQuery, query_embedding: list[float],
                            ) -> list[RetrievalResult]:
        vw = query.hybrid_weight
        kw = 1.0 - vw

        import asyncio
        v_task = self.vector_search(query_embedding=query_embedding, user_id=UUID(query.user_id), limit=50)
        k_task = self.keyword_search(query=query.query_text, user_id=UUID(query.user_id), limit=50)
        v_results, k_results = await asyncio.gather(v_task, k_task)

        scores: dict[str, dict] = {}
        for i, chunk in enumerate(v_results):
            vs = 1.0 - (i / max(len(v_results), 1))
            scores[str(chunk.id)] = {"chunk": chunk, "vector_score": vs, "keyword_score": 0.0}
        for i, chunk in enumerate(k_results):
            ks = 1.0 - (i / max(len(k_results), 1))
            cid = str(chunk.id)
            if cid in scores:
                scores[cid]["keyword_score"] = ks
            else:
                scores[cid] = {"chunk": chunk, "vector_score": 0.0, "keyword_score": ks}

        results = []
        for _cid, data in scores.items():
            chunk = data["chunk"]
            combined = data["vector_score"] * vw + data["keyword_score"] * kw
            results.append(RetrievalResult(
                chunk_id=str(chunk.id), content=chunk.content, score=round(combined, 3),
                vector_score=round(data["vector_score"], 3),
                keyword_score=round(data["keyword_score"], 3),
                metadata=chunk.metadata, source_excerpt=chunk.content[:200],
            ))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:query.top_k]
