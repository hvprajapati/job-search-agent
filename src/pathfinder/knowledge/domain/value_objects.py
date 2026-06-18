"""Knowledge domain value objects."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from datetime import datetime, timezone
from pathfinder.shared.domain.base_value_object import BaseValueObject


class KnowledgeSource(StrEnum):
    USER_RESUME = "user_resume"
    JOB_DESCRIPTION = "job_description"
    USER_UPLOAD = "user_upload"
    AGENT_GENERATED = "agent_generated"


@dataclass(frozen=True, kw_only=True)
class ChunkMetadata(BaseValueObject):
    source_type: str = ""
    source_id: str = ""
    source_name: str = ""
    user_id: str = ""
    job_id: str | None = None
    company_name: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    chunk_index: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True, kw_only=True)
class RetrievalResult(BaseValueObject):
    chunk_id: str
    content: str
    score: float = 0.0
    vector_score: float = 0.0
    keyword_score: float = 0.0
    metadata: ChunkMetadata | None = None
    source_excerpt: str = ""


@dataclass(frozen=True, kw_only=True)
class RetrievalQuery(BaseValueObject):
    query_text: str
    user_id: str
    filters: dict = field(default_factory=dict)
    top_k: int = 20
    hybrid_weight: float = 0.7
