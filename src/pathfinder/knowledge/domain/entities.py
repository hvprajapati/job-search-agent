"""Knowledge domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.knowledge.domain.value_objects import ChunkMetadata, KnowledgeSource


@dataclass(kw_only=True)
class KnowledgeDocument(BaseEntity):
    user_id: UUID
    source_type: KnowledgeSource
    source_id: str = ""
    title: str = ""
    content_raw: str = ""
    content_clean: str = ""
    chunk_count: int = 0
    embedding_model: str = "deepseek-embed"
    is_indexed: bool = False
    last_indexed_at: datetime | None = None

    @classmethod
    def from_text(cls, *, user_id: UUID, source_type: KnowledgeSource,
                  source_id: str, title: str, content: str) -> KnowledgeDocument:
        import re
        cleaned = re.sub(r"<[^>]+>", "", content)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cls(user_id=user_id, source_type=source_type, source_id=source_id,
                   title=title, content_raw=content, content_clean=cleaned)


@dataclass(kw_only=True)
class KnowledgeChunk(BaseEntity):
    document_id: UUID
    user_id: UUID
    content: str
    content_hash: str = ""
    embedding: list[float] | None = None
    metadata: ChunkMetadata | None = None
    chunk_index: int = 0
    token_count: int = 0
    is_active: bool = True

    @classmethod
    def create(cls, *, document_id: UUID, user_id: UUID, content: str,
               metadata: ChunkMetadata, chunk_index: int = 0) -> KnowledgeChunk:
        import hashlib
        return cls(document_id=document_id, user_id=user_id, content=content,
                   content_hash=hashlib.sha256(content.encode()).hexdigest()[:16],
                   metadata=metadata, chunk_index=chunk_index,
                   token_count=len(content) // 4)
