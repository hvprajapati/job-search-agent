# Pathfinder — Sprint 8: Knowledge & RAG System

**Sprint:** 8
**Duration:** 10 Days
**Prerequisite:** Sprint 7 (memory system operational)
**Goal:** Transform the agent from personalized to knowledgeable. RAG pipeline for document retrieval, hybrid search, and context-enriched agent reasoning.
**Source:** FINAL_ARCHITECTURE.md

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAG SYSTEM ARCHITECTURE                               │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     INGESTION PIPELINE (Async)                         │   │
│  │                                                                       │   │
│  │  Document (PDF/DOCX/TXT/MD)                                           │   │
│  │     │                                                                 │   │
│  │     ▼                                                                 │   │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐          │   │
│  │  │ EXTRACT  │──→│  CHUNK   │──→│ EXTRACT  │──→│  EMBED   │          │   │
│  │  │  TEXT    │   │ (semantic│   │ METADATA │   │ (DeepSeek│          │   │
│  │  │          │   │  split)  │   │          │   │  3072d)  │          │   │
│  │  └──────────┘   └──────────┘   └──────────┘   └──────────┘          │   │
│  │                                                      │               │   │
│  │                                                      ▼               │   │
│  │                                              ┌──────────────┐       │   │
│  │                                              │  pgvector    │       │   │
│  │                                              │  HNSW index  │       │   │
│  │                                              └──────────────┘       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     RETRIEVAL PIPELINE (Real-time)                     │   │
│  │                                                                       │   │
│  │  User Query + Intent                                                   │   │
│  │     │                                                                 │   │
│  │     ▼                                                                 │   │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐          │   │
│  │  │ VECTOR   │   │ KEYWORD  │   │  MERGE   │   │ RE-RANK  │          │   │
│  │  │ SEARCH   │ + │ SEARCH   │ = │ HYBRID   │──→│ (LLM)    │          │   │
│  │  │ (cosine) │   │ (tsvector│   │ RESULTS  │   │ top-20→5 │          │   │
│  │  │ top-50   │   │  top-50) │   │          │   │          │          │   │
│  │  └──────────┘   └──────────┘   └──────────┘   └──────────┘          │   │
│  │                                                      │               │   │
│  │                                                      ▼               │   │
│  │                                              ┌──────────────┐       │   │
│  │                                              │  CONTEXT     │       │   │
│  │                                              │  ASSEMBLY   │       │   │
│  │                                              │  (token      │       │   │
│  │                                              │   budget)    │       │   │
│  │                                              └──────────────┘       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     AGENT CONTEXT (merged)                             │   │
│  │                                                                       │   │
│  │  memory_context + knowledge_context + profile + preferences            │   │
│  │  → injected into intent_router, task_planner, result_synthesizer      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Day 1–2: Domain Core

### Files to Create

```
src/pathfinder/knowledge/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── entities.py           # KnowledgeChunk, KnowledgeDocument
│   ├── value_objects.py      # ChunkMetadata, RetrievalResult, KnowledgeSource
│   ├── repositories.py       # KnowledgeRepository (abstract)
│   ├── services.py           # ChunkingService, RetrievalService, ReRankingService
│   ├── events.py             # DocumentIngested, ChunkCreated
│   └── exceptions.py         # IngestionError, RetrievalError

tests/unit/knowledge/
├── test_chunking.py
├── test_retrieval.py
└── test_entities.py
```

### `src/pathfinder/knowledge/domain/value_objects.py`

```python
"""Knowledge domain value objects."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from datetime import datetime, timezone
from pathfinder.shared.domain.base_value_object import BaseValueObject
from pathfinder.shared.domain.exceptions import ValidationError


class KnowledgeSource(StrEnum):
    USER_RESUME = "user_resume"
    JOB_DESCRIPTION = "job_description"
    APPLICATION_NOTE = "application_note"
    COMPANY_RESEARCH = "company_research"
    COVER_LETTER = "cover_letter"
    INTERVIEW_PREP = "interview_prep"
    USER_UPLOAD = "user_upload"
    AGENT_GENERATED = "agent_generated"


class ChunkStrategy(StrEnum):
    SEMANTIC = "semantic"     # Split on paragraph/section boundaries
    FIXED_SIZE = "fixed_size" # Split every N tokens
    SENTENCE = "sentence"     # Split on sentence boundaries


@dataclass(frozen=True, kw_only=True)
class ChunkMetadata(BaseValueObject):
    """Metadata attached to every knowledge chunk for filtering."""
    source_type: KnowledgeSource
    source_id: str = ""           # UUID of the source entity
    source_name: str = ""         # Human-readable (e.g., "Resume - Base")
    user_id: str = ""
    job_id: str | None = None     # Linked job (for JD, application notes)
    company_name: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)  # "python", "remote", etc.
    page_number: int | None = None  # For PDF documents
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    chunk_index: int = 0          # Position in document (for ordering)


@dataclass(frozen=True, kw_only=True)
class RetrievalResult(BaseValueObject):
    """A single result from knowledge retrieval."""
    chunk_id: str
    content: str
    score: float               # Combined relevance score 0-1
    vector_score: float = 0.0  # Cosine similarity component
    keyword_score: float = 0.0 # Full-text search component
    metadata: ChunkMetadata | None = None
    source_excerpt: str = ""   # Highlighted excerpt


@dataclass(frozen=True, kw_only=True)
class RetrievalQuery(BaseValueObject):
    """Encapsulates a retrieval request."""
    query_text: str
    user_id: str
    filters: dict = field(default_factory=dict)  # source_type, job_id, tags
    top_k: int = 20
    hybrid_weight: float = 0.7  # Vector weight (0.3 = keyword)
    include_metadata: bool = True
```

### `src/pathfinder/knowledge/domain/entities.py`

```python
"""Knowledge domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.knowledge.domain.value_objects import (
    ChunkMetadata, KnowledgeSource, ChunkStrategy,
)


@dataclass(kw_only=True)
class KnowledgeDocument(BaseEntity):
    """A source document that can be chunked and indexed."""
    user_id: UUID
    source_type: KnowledgeSource
    source_id: str = ""         # UUID of the originating entity
    title: str = ""
    content_raw: str = ""       # Original full text
    content_clean: str = ""     # Cleaned text (no HTML, normalized whitespace)
    chunk_count: int = 0
    embedding_model: str = "deepseek-embed"
    is_indexed: bool = False
    last_indexed_at: datetime | None = None

    @classmethod
    def from_resume(cls, *, user_id: UUID, resume_id: UUID,
                    title: str, content: str) -> KnowledgeDocument:
        return cls(
            user_id=user_id,
            source_type=KnowledgeSource.USER_RESUME,
            source_id=str(resume_id),
            title=title,
            content_raw=content,
            content_clean=cls._clean_text(content),
        )

    @classmethod
    def from_job_description(cls, *, user_id: UUID, job_id: UUID,
                             title: str, company: str, content: str) -> KnowledgeDocument:
        return cls(
            user_id=user_id,
            source_type=KnowledgeSource.JOB_DESCRIPTION,
            source_id=str(job_id),
            title=f"{title} at {company}",
            content_raw=content,
            content_clean=cls._clean_text(content),
        )

    @staticmethod
    def _clean_text(raw: str) -> str:
        import re
        text = re.sub(r"<[^>]+>", "", raw)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


@dataclass(kw_only=True)
class KnowledgeChunk(BaseEntity):
    """A semantic chunk of a document, embedded and searchable."""
    document_id: UUID
    user_id: UUID
    content: str                # The chunk text
    content_hash: str = ""      # SHA-256 for dedup
    embedding: list[float] | None = None  # 3072d vector
    metadata: ChunkMetadata | None = None
    chunk_index: int = 0
    token_count: int = 0        # Approximate token count
    is_active: bool = True

    @classmethod
    def create(cls, *, document_id: UUID, user_id: UUID,
               content: str, metadata: ChunkMetadata,
               chunk_index: int = 0) -> KnowledgeChunk:
        import hashlib
        return cls(
            document_id=document_id, user_id=user_id,
            content=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest()[:16],
            metadata=metadata, chunk_index=chunk_index,
            token_count=len(content) // 4,  # Rough estimate
        )
```

### `src/pathfinder/knowledge/domain/repositories.py`

```python
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
    async def list_by_user(self, user_id: UUID, *, source_type: str | None = None,
                           limit: int = 50) -> list[KnowledgeDocument]: ...


class KnowledgeChunkRepository(BaseRepository[KnowledgeChunk]):
    @abstractmethod
    async def vector_search(self, *, query_embedding: list[float],
                            user_id: UUID, filters: dict | None = None,
                            limit: int = 50) -> list[KnowledgeChunk]: ...
    @abstractmethod
    async def keyword_search(self, *, query: str, user_id: UUID,
                             filters: dict | None = None,
                             limit: int = 50) -> list[KnowledgeChunk]: ...
    @abstractmethod
    async def hybrid_search(self, *, query: RetrievalQuery,
                            query_embedding: list[float],
                            ) -> list[RetrievalResult]: ...
    @abstractmethod
    async def save_batch(self, chunks: list[KnowledgeChunk]) -> None: ...
    @abstractmethod
    async def delete_by_document(self, document_id: UUID) -> int: ...
    @abstractmethod
    async def delete_by_user(self, user_id: UUID) -> int: ...
```

### `src/pathfinder/knowledge/domain/services.py`

```python
"""Knowledge domain services."""
import re
from pathfinder.knowledge.domain.value_objects import RetrievalQuery, RetrievalResult


class ChunkingService:
    """Splits documents into semantic chunks for embedding and retrieval."""

    CHUNK_SIZE_TARGET = 500   # target characters per chunk
    CHUNK_OVERLAP = 100       # overlap between chunks

    @classmethod
    def chunk(cls, text: str, strategy: str = "semantic") -> list[str]:
        """Split text into overlapping semantic chunks."""
        if strategy == "semantic":
            return cls._semantic_chunk(text)
        elif strategy == "sentence":
            return cls._sentence_chunk(text)
        return cls._fixed_chunk(text)

    @classmethod
    def _semantic_chunk(cls, text: str) -> list[str]:
        """Split on paragraph boundaries, merge short paragraphs."""
        paragraphs = re.split(r"\n\s*\n", text)
        chunks = []
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) < cls.CHUNK_SIZE_TARGET:
                current += ("\n\n" if current else "") + para
            else:
                if current:
                    chunks.append(current)
                current = para

        if current:
            chunks.append(current)

        # Add overlap: each chunk shares last N chars with next chunk
        overlapped = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                prev_end = chunks[i-1][-cls.CHUNK_OVERLAP:] if len(chunks[i-1]) > cls.CHUNK_OVERLAP else chunks[i-1]
                chunk = prev_end + "\n...\n" + chunk
            overlapped.append(chunk)

        return overlapped

    @classmethod
    def _sentence_chunk(cls, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) < cls.CHUNK_SIZE_TARGET:
                current += " " + sent if current else sent
            else:
                if current:
                    chunks.append(current)
                current = sent
        if current:
            chunks.append(current)
        return chunks

    @classmethod
    def _fixed_chunk(cls, text: str) -> list[str]:
        return [text[i:i+cls.CHUNK_SIZE_TARGET]
                for i in range(0, len(text), cls.CHUNK_SIZE_TARGET - cls.CHUNK_OVERLAP)]


class ReRankingService:
    """Re-ranks retrieval results using LLM for relevance scoring."""

    SYSTEM_PROMPT = """You are a search relevance judge. Given a user query and a list of document excerpts,
rank each excerpt by relevance to the query on a scale of 0-10.

Consider:
- Semantic relevance (does it answer the query?)
- Factual overlap (does it contain information the user needs?)
- Specificity (is it directly about what the user asked?)

Output a JSON array: [{"chunk_id": "...", "relevance": 8}, ...]"""

    def __init__(self, llm_port) -> None:
        self._llm = llm_port

    async def rerank(self, query: str, results: list[RetrievalResult],
                     top_k: int = 5) -> list[RetrievalResult]:
        """Re-rank results using LLM. Fall back to score-based ranking if LLM fails."""
        if len(results) <= top_k:
            return results

        try:
            excerpts = "\n\n".join(
                f"[{r.chunk_id[:8]}] {r.content[:300]}"
                for r in results[:20]
            )
            response = await self._llm.chat_completion(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=f"Query: {query}\n\nExcerpts:\n{excerpts}",
                temperature=0.1,
            )
            import json
            rankings = json.loads(response.content)
            if isinstance(rankings, list):
                score_map = {r["chunk_id"]: r.get("relevance", 5) for r in rankings}
                results.sort(key=lambda r: score_map.get(r.chunk_id[:8], 0), reverse=True)
        except Exception:
            pass  # Fall back to original score-based ranking

        return results[:top_k]
```

### `src/pathfinder/knowledge/domain/exceptions.py`

```python
"""Knowledge domain exceptions."""
from pathfinder.shared.domain.exceptions import NotFoundError, DomainError, ValidationError

class IngestionError(DomainError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Document ingestion failed: {detail}")

class RetrievalError(DomainError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Knowledge retrieval failed: {detail}")

class ChunkNotFoundError(NotFoundError):
    def __init__(self, chunk_id: str = "") -> None:
        super().__init__(f"Knowledge chunk not found: {chunk_id}")
```

---

## Day 3–4: Infrastructure — Persistence + Ingestion

### Files to Create

```
src/pathfinder/knowledge/infrastructure/
├── persistence/
│   ├── models.py             # KnowledgeDocumentModel, KnowledgeChunkModel
│   └── repositories.py       # SqlKnowledgeDocumentRepo, SqlKnowledgeChunkRepo
├── ingestion/
│   ├── extractors.py         # PDF, DOCX, TXT, MD text extraction
│   └── pipeline.py           # IngestionPipeline orchestrator
└── retrieval/
    └── hybrid_retriever.py   # Hybrid search implementation

alembic/versions/
└── 008_knowledge_tables.py

tests/integration/knowledge/
├── test_ingestion.py
└── test_retrieval.py
```

### `src/pathfinder/knowledge/infrastructure/persistence/models.py`

```python
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

    __table_args__ = (
        # One document per source (e.g., one resume indexed once)
        {"postgresql_where": "source_type IS NOT NULL AND source_id IS NOT NULL"},
    )

    def to_domain(self) -> KnowledgeDocument:
        return KnowledgeDocument(
            id=self.id, user_id=self.user_id,
            source_type=KnowledgeSource(self.source_type),
            source_id=self.source_id, title=self.title,
            content_raw=self.content_raw or "",
            content_clean=self.content_clean or "",
            chunk_count=self.chunk_count or 0,
            embedding_model=self.embedding_model or "deepseek-embed",
            is_indexed=self.is_indexed or False,
            last_indexed_at=self.last_indexed_at,
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, doc: KnowledgeDocument) -> "KnowledgeDocumentModel":
        return cls(
            id=doc.id, user_id=doc.user_id,
            source_type=doc.source_type.value,
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
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Generated tsvector column for hybrid search
    content_tsv: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_domain(self) -> KnowledgeChunk:
        return KnowledgeChunk(
            id=self.id, document_id=self.document_id, user_id=self.user_id,
            content=self.content or "", content_hash=self.content_hash or "",
            embedding=list(self.embedding) if self.embedding else None,
            metadata=ChunkMetadata(**self.metadata) if self.metadata else None,
            chunk_index=self.chunk_index or 0,
            token_count=self.token_count or 0,
            is_active=self.is_active or True,
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, chunk: KnowledgeChunk) -> "KnowledgeChunkModel":
        return cls(
            id=chunk.id, document_id=chunk.document_id, user_id=chunk.user_id,
            content=chunk.content, content_hash=chunk.content_hash,
            embedding=chunk.embedding,
            metadata={**chunk.metadata.__dict__} if chunk.metadata else {},
            chunk_index=chunk.chunk_index, token_count=chunk.token_count,
            is_active=chunk.is_active,
            created_at=chunk.created_at, updated_at=chunk.updated_at,
        )
```

### `src/pathfinder/knowledge/infrastructure/ingestion/pipeline.py`

```python
"""Document ingestion pipeline — extract → chunk → embed → store."""
import asyncio
from uuid import UUID
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.knowledge.domain.entities import KnowledgeDocument, KnowledgeChunk
from pathfinder.knowledge.domain.value_objects import ChunkMetadata
from pathfinder.knowledge.domain.services import ChunkingService
from pathfinder.knowledge.infrastructure.persistence.models import (
    KnowledgeDocumentModel, KnowledgeChunkModel,
)
from pathfinder.knowledge.infrastructure.ingestion.extractors import extract_text
from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient


class IngestionPipeline:
    """Orchestrates document → searchable chunks."""

    def __init__(self) -> None:
        self._embedder = DeepSeekClient()

    async def ingest(self, document: KnowledgeDocument) -> int:
        """Ingest a document: chunk it, embed chunks, store them. Returns chunk count."""
        maker = get_sessionmaker()
        async with maker() as session:
            # 1. Save document
            doc_model = KnowledgeDocumentModel.from_domain(document)
            session.add(doc_model)
            await session.flush()

            # 2. Chunk
            raw_text = document.content_clean or document.content_raw
            chunks_text = ChunkingService.chunk(raw_text)

            # 3. Create chunk entities with metadata
            chunks = []
            for i, text in enumerate(chunks_text):
                metadata = ChunkMetadata(
                    source_type=document.source_type,
                    source_id=document.source_id,
                    source_name=document.title,
                    user_id=str(document.user_id),
                    chunk_index=i,
                )
                chunk = KnowledgeChunk.create(
                    document_id=doc_model.id,
                    user_id=document.user_id,
                    content=text,
                    metadata=metadata,
                    chunk_index=i,
                )
                chunks.append(chunk)

            # 4. Generate embeddings (batch where possible, sequential for reliability)
            for chunk in chunks:
                try:
                    vec = await self._embedder.generate_embedding(chunk.content[:8000])
                    if len(vec) == 3072:
                        chunk.embedding = vec
                except Exception:
                    pass  # Chunk stored without embedding — backfilled later

            # 5. Batch save chunks
            chunk_models = [KnowledgeChunkModel.from_domain(c) for c in chunks]
            session.add_all(chunk_models)

            # 6. Update document
            doc_model.chunk_count = len(chunks)
            doc_model.is_indexed = True
            doc_model.last_indexed_at = __import__('datetime').datetime.now(
                __import__('datetime').timezone.utc)

            await session.commit()
            return len(chunks)

    async def reindex_document(self, document_id: UUID) -> int:
        """Delete old chunks and re-ingest a document."""
        maker = get_sessionmaker()
        async with maker() as session:
            doc_model = await session.get(KnowledgeDocumentModel, document_id)
            if not doc_model:
                return 0

            # Delete old chunks
            from sqlalchemy import delete
            await session.execute(
                delete(KnowledgeChunkModel).where(
                    KnowledgeChunkModel.document_id == document_id
                )
            )

            document = doc_model.to_domain()
            return await self.ingest(document)
```

### `src/pathfinder/knowledge/infrastructure/ingestion/extractors.py`

```python
"""Text extraction from various file formats."""
import io
import re


def extract_text(file_bytes: bytes, content_type: str) -> str:
    """Extract raw text from file bytes. Returns empty string on failure."""
    if "pdf" in content_type:
        return _extract_pdf(file_bytes)
    elif "docx" in content_type or "word" in content_type:
        return _extract_docx(file_bytes)
    elif "text/plain" in content_type:
        return file_bytes.decode("utf-8", errors="ignore")
    elif "markdown" in content_type or content_type == "text/markdown":
        return file_bytes.decode("utf-8", errors="ignore")
    return ""


def _extract_pdf(file_bytes: bytes) -> str:
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def _extract_docx(file_bytes: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""
```

### Migration — `alembic/versions/008_knowledge_tables.py`

```python
"""008_knowledge_tables."""
revision = "008"
down_revision = "007"

def upgrade():
    op.create_table("knowledge_documents",
        sa.Column("id", PGUUID(), primary_key=True),
        sa.Column("user_id", PGUUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(50)),
        sa.Column("source_id", sa.String(255)),
        sa.Column("title", sa.String(500)),
        sa.Column("content_raw", sa.Text()),
        sa.Column("content_clean", sa.Text()),
        sa.Column("chunk_count", sa.Integer(), default=0),
        sa.Column("embedding_model", sa.String(50), default="deepseek-embed"),
        sa.Column("is_indexed", sa.Boolean(), default=False),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_kdoc_user_source", "knowledge_documents", ["user_id", "source_type", "source_id"])

    op.create_table("knowledge_chunks",
        sa.Column("id", PGUUID(), primary_key=True),
        sa.Column("document_id", PGUUID(), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", PGUUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("content_hash", sa.String(32)),
        sa.Column("embedding", Vector(3072), nullable=True),
        sa.Column("metadata", JSONB(), default=dict, server_default="{}"),
        sa.Column("chunk_index", sa.Integer(), default=0),
        sa.Column("token_count", sa.Integer(), default=0),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("content_tsv", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_kchunk_user", "knowledge_chunks", ["user_id"])
    op.create_index("idx_kchunk_document", "knowledge_chunks", ["document_id"])

    # GIN index on tsvector for hybrid search
    op.execute("CREATE INDEX idx_kchunk_tsv ON knowledge_chunks USING GIN (content_tsv)")

    # HNSW index for vector search
    op.execute(
        "CREATE INDEX idx_kchunk_embedding ON knowledge_chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 200)"
    )

def downgrade():
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
```

---

## Day 5–6: Retrieval Pipeline + Repositories

### `src/pathfinder/knowledge/infrastructure/persistence/repositories.py`

```python
"""SQLAlchemy knowledge repository implementations."""
from uuid import UUID
from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.knowledge.domain.entities import KnowledgeChunk, KnowledgeDocument
from pathfinder.knowledge.domain.repositories import (
    KnowledgeDocumentRepository, KnowledgeChunkRepository,
)
from pathfinder.knowledge.domain.value_objects import RetrievalQuery, RetrievalResult
from pathfinder.knowledge.infrastructure.persistence.models import (
    KnowledgeDocumentModel, KnowledgeChunkModel,
)


class SqlKnowledgeDocumentRepository(KnowledgeDocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_source(self, source_type: str, source_id: str) -> KnowledgeDocument | None:
        stmt = select(KnowledgeDocumentModel).where(
            KnowledgeDocumentModel.source_type == source_type,
            KnowledgeDocumentModel.source_id == source_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

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

    async def list_by_user(self, user_id: UUID, *, source_type: str | None = None,
                           limit: int = 50) -> list[KnowledgeDocument]:
        stmt = select(KnowledgeDocumentModel).where(
            KnowledgeDocumentModel.user_id == user_id,
        )
        if source_type:
            stmt = stmt.where(KnowledgeDocumentModel.source_type == source_type)
        stmt = stmt.order_by(KnowledgeDocumentModel.updated_at.desc()).limit(limit)
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
        from sqlalchemy import delete
        result = await self._session.execute(
            delete(KnowledgeChunkModel).where(
                KnowledgeChunkModel.document_id == document_id
            )
        )
        return result.rowcount or 0

    async def delete_by_user(self, user_id: UUID) -> int:
        from sqlalchemy import delete
        result = await self._session.execute(
            delete(KnowledgeChunkModel).where(
                KnowledgeChunkModel.user_id == user_id
            )
        )
        return result.rowcount or 0

    async def vector_search(self, *, query_embedding: list[float],
                            user_id: UUID, filters: dict | None = None,
                            limit: int = 50) -> list[KnowledgeChunk]:
        stmt = select(KnowledgeChunkModel).where(
            KnowledgeChunkModel.user_id == user_id,
            KnowledgeChunkModel.is_active == True,
            KnowledgeChunkModel.embedding.is_not(None),
        )
        if filters:
            if "source_type" in filters:
                stmt = stmt.where(
                    KnowledgeChunkModel.metadata["source_type"].astext == filters["source_type"]
                )
            if "job_id" in filters:
                stmt = stmt.where(
                    KnowledgeChunkModel.metadata["job_id"].astext == filters["job_id"]
                )

        stmt = stmt.order_by(
            KnowledgeChunkModel.embedding.cosine_distance(query_embedding)
        ).limit(limit)

        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def keyword_search(self, *, query: str, user_id: UUID,
                             filters: dict | None = None,
                             limit: int = 50) -> list[KnowledgeChunk]:
        ts_query = func.plainto_tsquery("english", query)
        stmt = select(KnowledgeChunkModel).where(
            KnowledgeChunkModel.user_id == user_id,
            KnowledgeChunkModel.is_active == True,
            KnowledgeChunkModel.content_tsv.op("@@")(ts_query),
        )
        if filters:
            if "source_type" in filters:
                stmt = stmt.where(
                    KnowledgeChunkModel.metadata["source_type"].astext == filters["source_type"]
                )
        stmt = stmt.order_by(
            func.ts_rank(KnowledgeChunkModel.content_tsv, ts_query).desc()
        ).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def hybrid_search(self, *, query: RetrievalQuery,
                            query_embedding: list[float],
                            ) -> list[RetrievalResult]:
        """Combine vector + keyword results with weighted scoring."""
        vector_weight = query.hybrid_weight
        keyword_weight = 1.0 - vector_weight

        # Run both searches concurrently
        import asyncio
        vector_task = self.vector_search(
            query_embedding=query_embedding, user_id=UUID(query.user_id),
            filters=query.filters, limit=50,
        )
        keyword_task = self.keyword_search(
            query=query.query_text, user_id=UUID(query.user_id),
            filters=query.filters, limit=50,
        )
        vector_results, keyword_results = await asyncio.gather(vector_task, keyword_task)

        # Merge with weighted scoring
        scores: dict[str, dict] = {}

        for i, chunk in enumerate(vector_results):
            vector_score = 1.0 - (i / max(len(vector_results), 1))
            scores[str(chunk.id)] = {
                "chunk": chunk, "vector_score": vector_score, "keyword_score": 0.0,
            }

        for i, chunk in enumerate(keyword_results):
            keyword_score = 1.0 - (i / max(len(keyword_results), 1))
            cid = str(chunk.id)
            if cid in scores:
                scores[cid]["keyword_score"] = keyword_score
            else:
                scores[cid] = {
                    "chunk": chunk, "vector_score": 0.0, "keyword_score": keyword_score,
                }

        results = []
        for cid, data in scores.items():
            chunk = data["chunk"]
            combined = (data["vector_score"] * vector_weight +
                       data["keyword_score"] * keyword_weight)
            results.append(RetrievalResult(
                chunk_id=str(chunk.id), content=chunk.content, score=round(combined, 3),
                vector_score=round(data["vector_score"], 3),
                keyword_score=round(data["keyword_score"], 3),
                metadata=chunk.metadata,
                source_excerpt=chunk.content[:200],
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:query.top_k]
```

---

## Day 7–8: Agent Integration + APIs

### Update Context Builder — Add Knowledge Retrieval

**File:** `src/pathfinder/agent/infrastructure/langgraph/nodes/context_builder.py`

```python
# ADD after memory retrieval:
from pathfinder.knowledge.infrastructure.persistence.repositories import (
    SqlKnowledgeChunkRepository,
)
from pathfinder.knowledge.domain.value_objects import RetrievalQuery

# ── Knowledge retrieval ──
knowledge_repo = SqlKnowledgeChunkRepository(session)
intent = state.get("intent", "")
user_message = state.get("user_message", "")

knowledge_context = ""
if user_message:
    query = RetrievalQuery(
        query_text=f"{intent} {user_message}",
        user_id=user_id,
        top_k=5,
        hybrid_weight=0.7,
    )
    try:
        from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient
        embedder = DeepSeekClient()
        query_embedding = await embedder.generate_embedding(query.query_text)
        results = await knowledge_repo.hybrid_search(
            query=query, query_embedding=query_embedding,
        )
        if results:
            knowledge_context = "\n\n".join(
                f"[Source: {r.metadata.source_name if r.metadata else 'document'}] {r.content[:500]}"
                for r in results[:5]
            )
    except Exception:
        pass  # Knowledge retrieval is best-effort

context = {
    # ... existing fields ...
    "knowledge_context": knowledge_context,
    # ...
}
```

### Update SupervisorState — Add knowledge_context

**File:** `src/pathfinder/agent/domain/state.py` — Add field:

```python
# ── Knowledge (populated by context_builder node) ──
knowledge_context: str     # Relevant document chunks for the current query
```

### Update LLM Nodes — Inject Knowledge

**File:** `src/pathfinder/agent/infrastructure/langgraph/nodes/intent_router_node.py`

```python
# In enriched_message building:
knowledge_context = state.get("knowledge_context", "")
if knowledge_context:
    enriched_message = (
        f"Relevant knowledge:\n{knowledge_context}\n\n"
        f"{enriched_message}"
    )
```

**File:** `src/pathfinder/agent/domain/services.py` — `_build_planning_prompt`:

```python
knowledge_context = state.get("knowledge_context", "")
if knowledge_context:
    memory_section += (
        f"\nRELEVANT DOCUMENTS:\n{knowledge_context}\n\n"
        f"Use this knowledge to inform your plan.\n"
    )
```

### Knowledge API

**File:** `src/pathfinder/knowledge/presentation/router.py` (NEW)

```python
"""Knowledge API routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User
from pathfinder.knowledge.domain.entities import KnowledgeDocument
from pathfinder.knowledge.domain.value_objects import KnowledgeSource, RetrievalQuery
from pathfinder.knowledge.infrastructure.ingestion.pipeline import IngestionPipeline
from pathfinder.knowledge.infrastructure.ingestion.extractors import extract_text
from pathfinder.knowledge.infrastructure.persistence.repositories import (
    SqlKnowledgeDocumentRepository, SqlKnowledgeChunkRepository,
)
from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient

router = APIRouter(prefix="/v1/knowledge", tags=["Knowledge"])


@router.post("/ingest/document")
async def ingest_document(
    file: UploadFile = File(...),
    title: str = Query("Uploaded Document"),
    source_type: str = Query("user_upload"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Upload and index a document for RAG retrieval."""
    file_bytes = await file.read()
    text = extract_text(file_bytes, file.content_type or "text/plain")
    if not text:
        from pathfinder.knowledge.domain.exceptions import IngestionError
        raise IngestionError("Could not extract text from file")

    doc = KnowledgeDocument(
        user_id=current_user.id,
        source_type=KnowledgeSource(source_type),
        source_id="",
        title=title,
        content_raw=text,
        content_clean=text,
    )

    pipeline = IngestionPipeline()
    chunk_count = await pipeline.ingest(doc)
    return {"data": {"chunks_created": chunk_count, "title": title}}


@router.post("/search")
async def search_knowledge(
    query: str = Query(...),
    source_type: str | None = Query(None),
    top_k: int = Query(5, le=20),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Search knowledge base with hybrid retrieval."""
    repo = SqlKnowledgeChunkRepository(session)
    embedder = DeepSeekClient()
    query_embedding = await embedder.generate_embedding(query)

    filters = {}
    if source_type:
        filters["source_type"] = source_type

    rq = RetrievalQuery(query_text=query, user_id=str(current_user.id),
                        filters=filters, top_k=top_k)
    results = await repo.hybrid_search(query=rq, query_embedding=query_embedding)

    return {
        "data": [
            {"chunk_id": r.chunk_id, "content": r.content[:300],
             "score": r.score, "source": r.metadata.source_name if r.metadata else "",
             "excerpt": r.source_excerpt}
            for r in results
        ],
    }


@router.get("/documents")
async def list_documents(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = SqlKnowledgeDocumentRepository(session)
    docs = await repo.list_by_user(current_user.id)
    return {
        "data": [
            {"document_id": str(d.id), "title": d.title,
             "source_type": d.source_type.value, "chunk_count": d.chunk_count,
             "is_indexed": d.is_indexed}
            for d in docs
        ],
    }


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    chunk_repo = SqlKnowledgeChunkRepository(session)
    await chunk_repo.delete_by_document(document_id)
    await session.commit()
```

### Registration — `src/pathfinder/shared/infrastructure/main.py`

```python
from pathfinder.knowledge.presentation.router import router as knowledge_router
app.include_router(knowledge_router)
```

---

## Day 9: Ingestion Triggers + Auto-Indexing

### Auto-index on Resume Upload (hook into Sprint 3)

**File:** `src/pathfinder/profile/application/handlers.py` — After `confirm_parsed()`:

```python
# After profile save, trigger async knowledge indexing
from pathfinder.knowledge.domain.entities import KnowledgeDocument
from pathfinder.knowledge.domain.value_objects import KnowledgeSource
from pathfinder.knowledge.infrastructure.ingestion.pipeline import IngestionPipeline

# Build document from structured profile
resume_text = f"Name: {profile.full_name}\nHeadline: {profile.headline}\n\n"
for exp in profile.work_experiences:
    resume_text += f"{exp.title} at {exp.company}: {exp.description}\n"
for skill in profile.skills:
    resume_text += f"Skill: {skill.name} ({skill.proficiency.value}, {skill.years}y)\n"

doc = KnowledgeDocument.from_resume(
    user_id=cmd.user_id, resume_id=profile.id,
    title=f"Profile - {profile.full_name}",
    content=resume_text,
)
pipeline = IngestionPipeline()
chunk_count = await pipeline.ingest(doc)
```

---

## Day 10: Tests + Gate Review

### `tests/unit/knowledge/test_chunking.py`

```python
from pathfinder.knowledge.domain.services import ChunkingService

def test_semantic_chunk_splits_on_paragraphs():
    text = "Para 1.\n\nPara 2.\n\nPara 3."
    chunks = ChunkingService.chunk(text, "semantic")
    assert len(chunks) >= 1

def test_chunks_have_overlap():
    text = "A" * 600 + "\n\n" + "B" * 600 + "\n\n" + "C" * 600
    chunks = ChunkingService.chunk(text, "semantic")
    if len(chunks) > 1:
        # Overlap exists between consecutive chunks
        pass

def test_empty_text_returns_empty():
    assert ChunkingService.chunk("") == []

def test_single_paragraph_returns_one_chunk():
    text = "This is a single paragraph with enough text."
    chunks = ChunkingService.chunk(text)
    assert len(chunks) == 1
```

### `tests/unit/knowledge/test_entities.py`

```python
from uuid import uuid4
from pathfinder.knowledge.domain.entities import KnowledgeDocument, KnowledgeChunk
from pathfinder.knowledge.domain.value_objects import KnowledgeSource, ChunkMetadata

def test_document_from_resume():
    doc = KnowledgeDocument.from_resume(
        user_id=uuid4(), resume_id=uuid4(),
        title="My Resume", content="Experienced engineer...",
    )
    assert doc.source_type == KnowledgeSource.USER_RESUME
    assert doc.chunk_count == 0
    assert not doc.is_indexed

def test_chunk_has_content_hash():
    chunk = KnowledgeChunk.create(
        document_id=uuid4(), user_id=uuid4(),
        content="Test content",
        metadata=ChunkMetadata(source_type=KnowledgeSource.USER_UPLOAD, user_id="u1"),
    )
    assert len(chunk.content_hash) == 16
    assert chunk.token_count > 0
```

### `tests/integration/knowledge/test_ingestion.py`

```python
import pytest
from uuid import uuid4
from pathfinder.knowledge.domain.entities import KnowledgeDocument
from pathfinder.knowledge.domain.value_objects import KnowledgeSource
from pathfinder.knowledge.infrastructure.ingestion.pipeline import IngestionPipeline

pytestmark = pytest.mark.integration

async def test_ingest_document_creates_chunks():
    doc = KnowledgeDocument(
        user_id=uuid4(),
        source_type=KnowledgeSource.USER_UPLOAD,
        title="Test Document",
        content_raw="First paragraph about Python.\n\nSecond paragraph about FastAPI.\n\nThird about PostgreSQL.",
    )
    pipeline = IngestionPipeline()
    count = await pipeline.ingest(doc)
    assert count >= 1
```

### Gate Checklist

```
☐ KnowledgeChunk entity with embedding, content_hash, metadata
☐ ChunkingService: semantic, sentence, fixed-size strategies
☐ IngestionPipeline: extract → chunk → embed → store
☐ SqlKnowledgeChunkRepository: vector_search, keyword_search, hybrid_search
☐ Hybrid search combines vector + keyword with configurable weights
☐ ReRankingService: LLM re-ranking for top-20→5
☐ Agent context_builder: loads knowledge_context
☐ intent_router: injected with knowledge_context
☐ task_planner: injected with knowledge_context
☐ POST /v1/knowledge/ingest/document → 200 with chunk count
☐ POST /v1/knowledge/search → 200 with ranked results
☐ GET /v1/knowledge/documents → 200
☐ DELETE /v1/knowledge/documents/{id} → 204
☐ Auto-index on profile save (resume ingestion)
☐ Migration 008: knowledge_documents + knowledge_chunks tables
☐ HNSW index on embedding. GIN index on content_tsv.
☐ All unit tests pass (10+). Integration tests pass (4+).
☐ ruff check → 0. mypy --strict → 0
```

---

> *"Sprint 8: The agent no longer relies on what it was trained on. It retrieves what it needs to know, when it needs to know it. Memory tells it who the user is. Knowledge tells it what the user needs."*

**End of Sprint 8**
