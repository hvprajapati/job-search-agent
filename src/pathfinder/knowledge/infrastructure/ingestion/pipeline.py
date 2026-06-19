"""Document ingestion pipeline."""
import logging
from uuid import UUID
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.knowledge.domain.entities import KnowledgeDocument, KnowledgeChunk
from pathfinder.knowledge.domain.value_objects import ChunkMetadata, KnowledgeSource
from pathfinder.knowledge.domain.services import ChunkingService
from pathfinder.knowledge.infrastructure.persistence.models import KnowledgeDocumentModel, KnowledgeChunkModel
from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)


class IngestionPipeline:
    def __init__(self) -> None:
        self._embedder = DeepSeekClient()

    async def ingest(self, document: KnowledgeDocument) -> int:
        maker = get_sessionmaker()
        async with maker() as session:
            doc_model = KnowledgeDocumentModel.from_domain(document)
            session.add(doc_model)
            await session.flush()

            chunks_text = ChunkingService.chunk(document.content_clean or document.content_raw)
            chunks: list[KnowledgeChunk] = []
            for i, text in enumerate(chunks_text):
                meta = ChunkMetadata(
                    source_type=document.source_type.value,
                    source_id=document.source_id,
                    source_name=document.title,
                    user_id=str(document.user_id),
                    chunk_index=i,
                )
                chunk = KnowledgeChunk.create(
                    document_id=doc_model.id, user_id=document.user_id,
                    content=text, metadata=meta, chunk_index=i,
                )
                try:
                    vec = await self._embedder.generate_embedding(text[:8000])
                    if len(vec) > 0:  # Accept any valid embedding dimension
                        chunk.embedding = vec
                except Exception:
                    pass
                chunks.append(chunk)

            chunk_models = [KnowledgeChunkModel.from_domain(c) for c in chunks]
            session.add_all(chunk_models)
            doc_model.chunk_count = len(chunks)
            doc_model.is_indexed = True
            from datetime import datetime, timezone
            doc_model.last_indexed_at = datetime.now(timezone.utc)
            await session.commit()
            return len(chunks)
