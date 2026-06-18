"""Knowledge repository interfaces."""
from abc import abstractmethod
from uuid import UUID
from pathfinder.shared.domain.base_repository import BaseRepository
from pathfinder.knowledge.domain.entities import KnowledgeChunk, KnowledgeDocument
from pathfinder.knowledge.domain.value_objects import RetrievalQuery, RetrievalResult


class KnowledgeDocumentRepository(BaseRepository[KnowledgeDocument]):
    @abstractmethod
    async def get_by_source(self, source_type: str, source_id: str) -> KnowledgeDocument | None: ...
    @abstractmethod
    async def list_by_user(self, user_id: UUID, limit: int = 50) -> list[KnowledgeDocument]: ...


class KnowledgeChunkRepository(BaseRepository[KnowledgeChunk]):
    @abstractmethod
    async def vector_search(self, *, query_embedding: list[float], user_id: UUID,
                            limit: int = 50) -> list[KnowledgeChunk]: ...
    @abstractmethod
    async def keyword_search(self, *, query: str, user_id: UUID,
                             limit: int = 50) -> list[KnowledgeChunk]: ...
    @abstractmethod
    async def hybrid_search(self, *, query: RetrievalQuery, query_embedding: list[float],
                            ) -> list[RetrievalResult]: ...
    @abstractmethod
    async def save_batch(self, chunks: list[KnowledgeChunk]) -> None: ...
    @abstractmethod
    async def delete_by_document(self, document_id: UUID) -> int: ...
