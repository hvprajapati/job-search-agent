"""SQLAlchemy ORM models for knowledge domain."""
from uuid import UUID
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from datetime import datetime, timezone
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin
from pathfinder.knowledge.domain.entities import KnowledgeDocument, KnowledgeChunk
from pathfinder.knowledge.domain.value_objects import ChunkMetadata, KnowledgeSource


class KnowledgeDocumentModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_documents"

    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    content_raw: Mapped[str] = mapped_column(Text)
    content_clean: Mapped[str] = mapped_column(Text)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_model: Mapped[str] = mapped_column(String(50), default="deepseek-embed")
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_domain(self) -> KnowledgeDocument:
        return KnowledgeDocument(
            id=self.id, user_id=self.user_id,
            source_type=KnowledgeSource(self.source_type),
            source_id=self.source_id or "", title=self.title or "",
            content_raw=self.content_raw or "", content_clean=self.content_clean or "",
            chunk_count=self.chunk_count or 0, embedding_model=self.embedding_model or "deepseek-embed",
            is_indexed=self.is_indexed or False, last_indexed_at=self.last_indexed_at,
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, doc: KnowledgeDocument) -> "KnowledgeDocumentModel":
        return cls(
            id=doc.id, user_id=doc.user_id, source_type=doc.source_type.value,
            source_id=doc.source_id, title=doc.title,
            content_raw=doc.content_raw, content_clean=doc.content_clean,
            chunk_count=doc.chunk_count, embedding_model=doc.embedding_model,
            is_indexed=doc.is_indexed, last_indexed_at=doc.last_indexed_at,
            created_at=doc.created_at, updated_at=doc.updated_at,
        )


class KnowledgeChunkModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_chunks"

    document_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(32))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(3072), nullable=True)
    chunk_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, server_default="{}")
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # content_tsv is a generated column — accessed via raw SQL in keyword_search

    def to_domain(self) -> KnowledgeChunk:
        meta = self.chunk_metadata or {}
        return KnowledgeChunk(
            id=self.id, document_id=self.document_id, user_id=self.user_id,
            content=self.content or "", content_hash=self.content_hash or "",
            embedding=list(self.embedding) if self.embedding is not None and len(self.embedding) > 0 else None,
            metadata=ChunkMetadata(**meta) if meta else None,
            chunk_index=self.chunk_index or 0, token_count=self.token_count or 0,
            is_active=self.is_active or True,
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, c: KnowledgeChunk) -> "KnowledgeChunkModel":
        return cls(
            id=c.id, document_id=c.document_id, user_id=c.user_id,
            content=c.content, content_hash=c.content_hash,
            embedding=c.embedding,
            metadata={**c.metadata.__dict__} if c.metadata else {},
            chunk_index=c.chunk_index, token_count=c.token_count,
            is_active=c.is_active,
            created_at=c.created_at, updated_at=c.updated_at,
        )
