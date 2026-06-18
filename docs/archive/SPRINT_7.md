# Pathfinder — Sprint 7: Memory System

**Sprint:** 7 of 7
**Duration:** 10 Days
**Prerequisite:** Sprints 3–6 (profile, jobs, matching, agent operational)
**Goal:** Transform the agent from stateless to personalized. Episodic, semantic, procedural memory. Daily consolidation. Agent context enriched with relevant memories.
**Source:** FINAL_ARCHITECTURE.md §4 + MEMORY.md

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY SYSTEM ARCHITECTURE                             │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     MEMORY CREATION (Real-time)                        │   │
│  │                                                                       │   │
│  │  Agent Execution ──→ EpisodicMemory (store immediately)               │   │
│  │  User Feedback   ──→ EpisodicMemory (thumbs up/down, application)     │   │
│  │  Tool Calls      ──→ EpisodicMemory (what was called, result)         │   │
│  │  Profile Changes ──→ EpisodicMemory (what changed)                    │   │
│  └──────────────────────────────────┬───────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                  MEMORY RETRIEVAL (Real-time)                         │   │
│  │                                                                       │   │
│  │  Agent Context Builder:                                               │   │
│  │  1. Always: Profile + Preferences + Resumes                           │   │
│  │  2. Recent: Last 20 episodic memories (recency)                       │   │
│  │  3. Relevant: Top-10 semantic memories (vector similarity)            │   │
│  │  4. Patterns: Top-3 procedural memories (intent match)                │   │
│  │  → Assembled into context within 8K token budget                      │   │
│  └──────────────────────────────────┬───────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │               MEMORY CONSOLIDATION (Daily, Celery Beat)               │   │
│  │                                                                       │   │
│  │  For each active user (03:00 UTC):                                    │   │
│  │  1. Fetch unconsolidated episodic memories (last 24h)                 │   │
│  │  2. LLM: Extract patterns, facts, preferences                         │   │
│  │  3. UPSERT semantic memories (version, evidence tracking)              │   │
│  │  4. Update preference weights (Bayesian)                               │   │
│  │  5. Update procedural patterns (success rates)                        │   │
│  │  6. Update career narrative summary                                    │   │
│  │  7. Mark episodes as consolidated                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Day 1–2: Domain Core

### Files to Create

```
src/pathfinder/agent/domain/memory/
├── __init__.py
├── entities.py           # EpisodicMemory, SemanticMemory, ProceduralMemory
├── value_objects.py      # MemoryType, ImportanceScore, MemoryEmbedding, ConsolidationRun
├── repositories.py       # MemoryRepository (abstract — all 3 types)
├── services.py           # MemoryRetrievalService, ConsolidationService, ImportanceCalculator
├── events.py             # MemoryStored, MemoryConsolidated, PreferenceShifted
├── exceptions.py         # MemoryNotFoundError, ConsolidationError

tests/unit/agent/memory/
├── test_entities.py
├── test_importance.py
├── test_retrieval.py
└── test_consolidation.py
```

### `src/pathfinder/agent/domain/memory/value_objects.py`

```python
"""Memory domain value objects."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from datetime import datetime, timezone
from pathfinder.shared.domain.base_value_object import BaseValueObject
from pathfinder.shared.domain.exceptions import ValidationError


class EpisodeType(StrEnum):
    AGENT_INVOCATION = "agent_invocation"
    TOOL_EXECUTION = "tool_execution"
    USER_FEEDBACK = "user_feedback"
    APPLICATION_EVENT = "application_event"
    PROFILE_CHANGE = "profile_change"
    PREFERENCE_SIGNAL = "preference_signal"
    SYSTEM_EVENT = "system_event"


class SemanticMemoryType(StrEnum):
    PROFILE_FACT = "profile_fact"
    SKILL_KNOWLEDGE = "skill_knowledge"
    LEARNED_INSIGHT = "learned_insight"
    PREFERENCE_FACT = "preference_fact"
    CAREER_NARRATIVE = "career_narrative"
    GENERAL_KNOWLEDGE = "general_knowledge"


class PatternType(StrEnum):
    SEARCH_BEHAVIOR = "search_behavior"
    COMMUNICATION_STYLE = "communication_style"
    WORKFLOW_PREFERENCE = "workflow_preference"
    RESPONSE_PATTERN = "response_pattern"


class MemoryImportance(StrEnum):
    CRITICAL = "critical"   # 1.0 — offer received, explicit preference stated
    HIGH = "high"           # 0.8 — interview scheduled, application submitted
    MEDIUM = "medium"       # 0.5 — job saved, resume tailored
    LOW = "low"             # 0.2 — job viewed, page scrolled
    NOISE = "noise"         # 0.05 — system event, heartbeat


@dataclass(frozen=True, kw_only=True)
class ImportanceScore(BaseValueObject):
    value: float  # 0.0 - 1.0
    source: str = "heuristic"  # "heuristic" | "consolidation" | "explicit"
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not 0 <= self.value <= 1.0:
            raise ValidationError(f"Importance must be 0-1, got {self.value}")

    def decay(self, days_since_creation: int) -> ImportanceScore:
        """Apply time-based decay. Critical memories don't decay."""
        if self.source == "explicit" or self.value >= 0.9:
            return self
        decayed = self.value * max(0.3, 1.0 - (days_since_creation / 365) * 0.7)
        return ImportanceScore(value=round(decayed, 3), source=self.source)


@dataclass(frozen=True, kw_only=True)
class MemoryEmbedding(BaseValueObject):
    vector: tuple[float, ...]  # 1536d for episodic, 3072d for semantic
    model: str = "deepseek-embed"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True, kw_only=True)
class ConsolidationRun(BaseValueObject):
    run_id: str
    user_id: str
    started_at: str
    completed_at: str = ""
    episodes_processed: int = 0
    insights_generated: int = 0
    preferences_updated: int = 0
    status: str = "running"  # running | completed | failed
    error: str = ""
    tokens_used: int = 0
```

### `src/pathfinder/agent/domain/memory/entities.py`

```python
"""Memory domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.agent.domain.memory.value_objects import (
    EpisodeType, SemanticMemoryType, PatternType,
    ImportanceScore, MemoryImportance, MemoryEmbedding,
)


@dataclass(kw_only=True)
class EpisodicMemory(BaseEntity):
    """Raw event record. Append-only. Immutable after creation."""
    user_id: UUID
    session_id: UUID | None = None
    episode_type: EpisodeType = EpisodeType.SYSTEM_EVENT
    actor: str = "system"       # "user", "agent", tool name, etc.
    action: str = ""            # Human-readable description
    payload: dict = field(default_factory=dict)  # Full event data
    importance: ImportanceScore = field(
        default_factory=lambda: ImportanceScore(value=0.3)
    )
    embedding: MemoryEmbedding | None = None
    context_summary: str = ""   # One-line LLM summary (populated at creation)
    parent_episode_id: UUID | None = None
    consolidation_run_id: UUID | None = None
    is_consolidated: bool = False
    expires_at: datetime | None = None  # 90 days for normal, 730 for important

    @classmethod
    def record_agent_execution(cls, *, user_id: UUID, session_id: UUID,
                               call_id: UUID, intent: str, user_message: str,
                               tool_results: list[dict], final_response: str,
                               latency_ms: int, is_success: bool) -> EpisodicMemory:
        importance = ImportanceScore(
            value=0.5,  # Agent executions are medium importance by default
        )
        return cls(
            user_id=user_id, session_id=session_id,
            episode_type=EpisodeType.AGENT_INVOCATION,
            actor="supervisor_agent",
            action=f"Agent executed intent '{intent}' — {'success' if is_success else 'failed'}",
            payload={
                "call_id": str(call_id), "intent": intent,
                "user_message": user_message[:500],
                "tool_results": tool_results[:10],
                "final_response": final_response[:500],
                "latency_ms": latency_ms, "is_success": is_success,
            },
            importance=importance,
            context_summary=f"Agent: {intent} — {final_response[:100]}",
        )

    @classmethod
    def record_feedback(cls, *, user_id: UUID, job_id: UUID,
                        feedback: str, session_id: UUID | None = None) -> EpisodicMemory:
        return cls(
            user_id=user_id, session_id=session_id,
            episode_type=EpisodeType.USER_FEEDBACK,
            actor="user",
            action=f"User gave feedback '{feedback}' on job {job_id}",
            payload={"job_id": str(job_id), "feedback": feedback},
            importance=ImportanceScore(value=0.6),
            context_summary=f"User {feedback} job {job_id}",
        )

    def mark_consolidated(self, run_id: UUID) -> None:
        self.consolidation_run_id = run_id
        self.is_consolidated = True
        self.mark_updated()


@dataclass(kw_only=True)
class SemanticMemory(BaseEntity):
    """Structured fact or insight about the user. Versioned. Embedding-indexed."""
    user_id: UUID
    memory_type: SemanticMemoryType = SemanticMemoryType.GENERAL_KNOWLEDGE
    subject: str = ""           # What this memory is about
    content: dict = field(default_factory=dict)  # Structured body
    content_text: str = ""     # Searchable text representation
    embedding: MemoryEmbedding | None = None
    confidence: float = 0.5    # 0.0-1.0 — how certain we are
    evidence_episodes: list[UUID] = field(default_factory=list)
    evidence_count: int = 1
    importance: float = 0.5
    access_count: int = 0
    last_accessed_at: datetime | None = None
    consolidation_run_id: UUID | None = None
    version: int = 1
    is_active: bool = True

    @classmethod
    def create_fact(cls, *, user_id: UUID, memory_type: SemanticMemoryType,
                    subject: str, content: dict, confidence: float = 0.5,
                    evidence: list[UUID] | None = None) -> SemanticMemory:
        return cls(
            user_id=user_id, memory_type=memory_type,
            subject=subject, content=content,
            content_text=str(content),
            confidence=confidence,
            evidence_episodes=evidence or [],
            evidence_count=len(evidence) if evidence else 1,
        )

    def update_evidence(self, new_episodes: list[UUID], new_content: dict | None = None) -> None:
        existing = set(str(e) for e in self.evidence_episodes)
        for ep in new_episodes:
            if str(ep) not in existing:
                self.evidence_episodes.append(ep)
        self.evidence_count = len(self.evidence_episodes)
        self.confidence = min(1.0, self.confidence + 0.03 * len(new_episodes))
        if new_content:
            self.content = new_content
            self.content_text = str(new_content)
            self.version += 1
        self.mark_updated()

    def record_access(self) -> None:
        self.access_count += 1
        self.last_accessed_at = datetime.now(timezone.utc)


@dataclass(kw_only=True)
class ProceduralMemory(BaseEntity):
    """Learned behavior pattern. Tracks success rates to optimize workflows."""
    user_id: UUID
    pattern_type: PatternType = PatternType.SEARCH_BEHAVIOR
    context_signature: str = ""      # When this pattern applies
    context_embedding: MemoryEmbedding | None = None
    action_sequence: dict = field(default_factory=dict)  # What to do
    success_rate: float = 0.0
    execution_count: int = 0
    avg_latency_ms: int = 0
    last_executed_at: datetime | None = None
    is_active: bool = True

    def record_execution(self, success: bool, latency_ms: int) -> None:
        n = self.execution_count
        self.success_rate = (self.success_rate * n + (1.0 if success else 0.0)) / (n + 1)
        self.avg_latency_ms = int((self.avg_latency_ms * n + latency_ms) / (n + 1))
        self.execution_count += 1
        self.last_executed_at = datetime.now(timezone.utc)
        self.mark_updated()
```

### `src/pathfinder/agent/domain/memory/repositories.py`

```python
"""Memory repository interfaces."""
from abc import abstractmethod
from uuid import UUID
from pathfinder.shared.domain.base_repository import BaseRepository
from pathfinder.agent.domain.memory.entities import (
    EpisodicMemory, SemanticMemory, ProceduralMemory,
)


class EpisodicRepository(BaseRepository[EpisodicMemory]):
    @abstractmethod
    async def list_recent(self, user_id: UUID, limit: int = 20) -> list[EpisodicMemory]: ...
    @abstractmethod
    async def list_unconsolidated(self, user_id: UUID, since: str | None = None) -> list[EpisodicMemory]: ...
    @abstractmethod
    async def mark_consolidated(self, episode_ids: list[UUID], run_id: UUID) -> int: ...
    @abstractmethod
    async def search_by_embedding(self, user_id: UUID, query_embedding: list[float],
                                  limit: int = 20) -> list[EpisodicMemory]: ...


class SemanticRepository(BaseRepository[SemanticMemory]):
    @abstractmethod
    async def search_by_embedding(self, user_id: UUID, query_embedding: list[float],
                                  limit: int = 10, min_importance: float = 0.2,
                                  ) -> list[SemanticMemory]: ...
    @abstractmethod
    async def search_by_type(self, user_id: UUID, memory_type: str,
                             limit: int = 20) -> list[SemanticMemory]: ...
    @abstractmethod
    async def upsert(self, memory: SemanticMemory) -> SemanticMemory: ...
    @abstractmethod
    async def get_by_subject(self, user_id: UUID, subject: str) -> SemanticMemory | None: ...


class ProceduralRepository(BaseRepository[ProceduralMemory]):
    @abstractmethod
    async def list_active(self, user_id: UUID, limit: int = 10) -> list[ProceduralMemory]: ...
    @abstractmethod
    async def find_by_context(self, user_id: UUID, pattern_type: str | None = None,
                              limit: int = 5) -> list[ProceduralMemory]: ...
```

### `src/pathfinder/agent/domain/memory/services.py`

```python
"""Memory domain services."""
from uuid import UUID, uuid4
from pathfinder.agent.domain.memory.entities import (
    EpisodicMemory, SemanticMemory, ProceduralMemory,
)
from pathfinder.agent.domain.memory.value_objects import (
    ImportanceScore, MemoryImportance, EpisodeType, SemanticMemoryType,
)


class ImportanceCalculator:
    """Assigns initial importance scores to episodic memories."""

    DEFAULT_SCORES: dict[EpisodeType, float] = {
        EpisodeType.AGENT_INVOCATION: 0.50,
        EpisodeType.TOOL_EXECUTION: 0.30,
        EpisodeType.USER_FEEDBACK: 0.60,
        EpisodeType.APPLICATION_EVENT: 0.70,
        EpisodeType.PROFILE_CHANGE: 0.40,
        EpisodeType.PREFERENCE_SIGNAL: 0.65,
        EpisodeType.SYSTEM_EVENT: 0.10,
    }

    @classmethod
    def calculate(cls, episode_type: EpisodeType, payload: dict | None = None,
                  **overrides) -> ImportanceScore:
        base = cls.DEFAULT_SCORES.get(episode_type, 0.30)

        # Boost based on payload signals
        if payload:
            if payload.get("feedback") == "thumbs_up":
                base = max(base, 0.55)
            if payload.get("is_success") is False:
                base = max(base, 0.45)  # Failures are learning signals
            if payload.get("intent") == "apply_to_job":
                base = max(base, 0.75)

        return ImportanceScore(value=min(1.0, base))


class MemoryRetrievalService:
    """Retrieves relevant memories for agent context assembly."""

    def __init__(self, episodic_repo, semantic_repo, procedural_repo,
                 embedding_port) -> None:
        self._episodic = episodic_repo
        self._semantic = semantic_repo
        self._procedural = procedural_repo
        self._embedder = embedding_port

    async def retrieve_context(self, user_id: UUID, intent: str,
                               user_message: str = "",
                               token_budget: int = 8000) -> dict:
        """Assemble a context package for the agent from all memory types.

        Returns dict with keys: recent_episodes, relevant_semantic,
        relevant_procedural, memory_context_text.
        """
        # 1. Recent episodes (always, fast indexed query)
        recent = await self._episodic.list_recent(user_id, limit=20)

        # 2. Relevant semantic memories (vector search)
        query_text = f"{intent} {user_message}"
        query_embedding = None
        try:
            query_embedding = await self._embedder.generate_embedding(query_text)
        except Exception:
            pass

        semantic = []
        if query_embedding:
            semantic = await self._semantic.search_by_embedding(
                user_id, query_embedding, limit=10, min_importance=0.2,
            )
            for s in semantic:
                s.record_access()

        # 3. Procedural patterns
        procedural = await self._procedural.list_active(user_id, limit=3)

        # 4. Format into a text context block (token-budgeted)
        context_parts = []

        if semantic:
            context_parts.append("**What I know about you (from past interactions):**")
            for s in semantic[:8]:
                context_parts.append(f"- {s.subject}: {s.content_text[:200]}")
                token_budget -= 50

        if recent:
            context_parts.append("\n**Recent activity:**")
            for ep in recent[:10]:
                if ep.context_summary:
                    context_parts.append(f"- {ep.context_summary[:150]}")
                    token_budget -= 30
                if token_budget < 500:
                    break

        memory_context = "\n".join(context_parts)

        return {
            "recent_episodes": recent,
            "relevant_semantic": semantic,
            "relevant_procedural": procedural,
            "memory_context_text": memory_context[:token_budget],
        }
```

---

## Day 3–4: Infrastructure — Persistence

### `src/pathfinder/agent/infrastructure/memory/models.py`

```python
"""SQLAlchemy ORM models for memory domain."""
from uuid import UUID
from sqlalchemy import String, Float, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from datetime import datetime, timezone
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin
from pathfinder.agent.domain.memory.entities import (
    EpisodicMemory, SemanticMemory, ProceduralMemory,
)
from pathfinder.agent.domain.memory.value_objects import (
    ImportanceScore, MemoryEmbedding, EpisodeType, SemanticMemoryType, PatternType,
)


class EpisodicMemoryModel(Base, UUIDMixin):
    __tablename__ = "episodic_memories"

    tenant_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("tenants.id"))
    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    episode_type: Mapped[str] = mapped_column(String(50))
    actor: Mapped[str] = mapped_column(String(50), default="system")
    action: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    importance_score: Mapped[float] = mapped_column(Float, default=0.3)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    context_summary: Mapped[str | None] = mapped_column(Text)
    parent_episode_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    consolidation_run_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    is_consolidated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(timezone.utc))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                   default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Partitioned by created_at (daily) — handled in migration
    )

    def to_domain(self) -> EpisodicMemory:
        return EpisodicMemory(
            id=self.id, user_id=self.user_id, session_id=self.session_id,
            episode_type=EpisodeType(self.episode_type),
            actor=self.actor, action=self.action or "",
            payload=self.payload or {},
            importance=ImportanceScore(value=self.importance_score or 0.3),
            embedding=MemoryEmbedding(vector=tuple(self.embedding)) if self.embedding else None,
            context_summary=self.context_summary or "",
            parent_episode_id=self.parent_episode_id,
            consolidation_run_id=self.consolidation_run_id,
            is_consolidated=self.is_consolidated or False,
            expires_at=self.expires_at,
            created_at=self.created_at, updated_at=self.recorded_at,
        )

    @classmethod
    def from_domain(cls, e: EpisodicMemory) -> "EpisodicMemoryModel":
        return cls(
            id=e.id, user_id=e.user_id, session_id=e.session_id,
            episode_type=e.episode_type.value,
            actor=e.actor, action=e.action,
            payload=e.payload,
            importance_score=e.importance.value,
            embedding=list(e.embedding.vector) if e.embedding else None,
            context_summary=e.context_summary,
            parent_episode_id=e.parent_episode_id,
            consolidation_run_id=e.consolidation_run_id,
            is_consolidated=e.is_consolidated,
            expires_at=e.expires_at,
            created_at=e.created_at, recorded_at=e.updated_at,
        )


class SemanticMemoryModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "semantic_memories"

    tenant_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("tenants.id"))
    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    memory_type: Mapped[str] = mapped_column(String(50))
    subject: Mapped[str] = mapped_column(Text)
    content: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    content_text: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(3072), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_episodes: Mapped[list | None] = mapped_column(ARRAY(PGUUID), server_default="{}")
    evidence_count: Mapped[int] = mapped_column(Integer, default=1)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consolidation_run_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_domain(self) -> SemanticMemory:
        return SemanticMemory(
            id=self.id, user_id=self.user_id,
            memory_type=SemanticMemoryType(self.memory_type),
            subject=self.subject or "", content=self.content or {},
            content_text=self.content_text or "",
            embedding=MemoryEmbedding(vector=tuple(self.embedding)) if self.embedding else None,
            confidence=self.confidence or 0.5,
            evidence_episodes=self.evidence_episodes or [],
            evidence_count=self.evidence_count or 1,
            importance=self.importance or 0.5,
            access_count=self.access_count or 0,
            last_accessed_at=self.last_accessed_at,
            consolidation_run_id=self.consolidation_run_id,
            version=self.version or 1, is_active=self.is_active or True,
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, m: SemanticMemory) -> "SemanticMemoryModel":
        return cls(
            id=m.id, user_id=m.user_id, memory_type=m.memory_type.value,
            subject=m.subject, content=m.content,
            content_text=m.content_text,
            embedding=list(m.embedding.vector) if m.embedding else None,
            confidence=m.confidence, evidence_episodes=m.evidence_episodes,
            evidence_count=m.evidence_count, importance=m.importance,
            access_count=m.access_count, last_accessed_at=m.last_accessed_at,
            consolidation_run_id=m.consolidation_run_id,
            version=m.version, is_active=m.is_active,
            created_at=m.created_at, updated_at=m.updated_at,
        )


class ProceduralMemoryModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "procedural_memories"

    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    pattern_type: Mapped[str] = mapped_column(String(50))
    context_signature: Mapped[str] = mapped_column(Text)
    context_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    action_sequence: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    last_executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_domain(self) -> ProceduralMemory:
        return ProceduralMemory(
            id=self.id, user_id=self.user_id,
            pattern_type=PatternType(self.pattern_type),
            context_signature=self.context_signature or "",
            context_embedding=MemoryEmbedding(vector=tuple(self.context_embedding)) if self.context_embedding else None,
            action_sequence=self.action_sequence or {},
            success_rate=self.success_rate or 0.0,
            execution_count=self.execution_count or 0,
            avg_latency_ms=self.avg_latency_ms or 0,
            last_executed_at=self.last_executed_at,
            is_active=self.is_active or True,
            created_at=self.created_at, updated_at=self.updated_at,
        )
```

### `src/pathfinder/agent/infrastructure/memory/repositories.py`

```python
"""SQLAlchemy memory repository implementations."""
from uuid import UUID
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.agent.domain.memory.entities import EpisodicMemory, SemanticMemory, ProceduralMemory
from pathfinder.agent.domain.memory.repositories import EpisodicRepository, SemanticRepository, ProceduralRepository
from pathfinder.agent.infrastructure.memory.models import (
    EpisodicMemoryModel, SemanticMemoryModel, ProceduralMemoryModel,
)


class SqlEpisodicRepository(EpisodicRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> EpisodicMemory | None:
        model = await self._session.get(EpisodicMemoryModel, id)
        return model.to_domain() if model else None

    async def save(self, entity: EpisodicMemory) -> None:
        model = EpisodicMemoryModel.from_domain(entity)
        self._session.add(model)
        await self._session.flush()

    async def delete(self, entity: EpisodicMemory) -> None:
        model = await self._session.get(EpisodicMemoryModel, entity.id)
        if model:
            await self._session.delete(model)

    async def list_recent(self, user_id: UUID, limit: int = 20) -> list[EpisodicMemory]:
        stmt = (select(EpisodicMemoryModel)
                .where(EpisodicMemoryModel.user_id == user_id)
                .order_by(EpisodicMemoryModel.created_at.desc())
                .limit(limit))
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def list_unconsolidated(self, user_id: UUID, since: str | None = None) -> list[EpisodicMemory]:
        stmt = select(EpisodicMemoryModel).where(
            EpisodicMemoryModel.user_id == user_id,
            EpisodicMemoryModel.is_consolidated == False,  # noqa: E712
        )
        if since:
            stmt = stmt.where(EpisodicMemoryModel.created_at >= since)
        stmt = stmt.order_by(EpisodicMemoryModel.created_at.asc()).limit(500)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def mark_consolidated(self, episode_ids: list[UUID], run_id: UUID) -> int:
        stmt = (update(EpisodicMemoryModel)
                .where(EpisodicMemoryModel.id.in_(episode_ids))
                .values(is_consolidated=True, consolidation_run_id=run_id))
        result = await self._session.execute(stmt)
        return result.rowcount or 0

    async def search_by_embedding(self, user_id: UUID, query_embedding: list[float],
                                  limit: int = 20) -> list[EpisodicMemory]:
        stmt = (select(EpisodicMemoryModel)
                .where(EpisodicMemoryModel.user_id == user_id,
                       EpisodicMemoryModel.embedding.is_not(None))
                .order_by(EpisodicMemoryModel.embedding.cosine_distance(query_embedding))
                .limit(limit))
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]


class SqlSemanticRepository(SemanticRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> SemanticMemory | None:
        model = await self._session.get(SemanticMemoryModel, id)
        return model.to_domain() if model else None

    async def save(self, entity: SemanticMemory) -> None:
        model = SemanticMemoryModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity: SemanticMemory) -> None:
        model = await self._session.get(SemanticMemoryModel, entity.id)
        if model:
            model.is_active = False

    async def search_by_embedding(self, user_id: UUID, query_embedding: list[float],
                                  limit: int = 10, min_importance: float = 0.2,
                                  ) -> list[SemanticMemory]:
        stmt = (select(SemanticMemoryModel)
                .where(SemanticMemoryModel.user_id == user_id,
                       SemanticMemoryModel.is_active == True,  # noqa: E712
                       SemanticMemoryModel.importance >= min_importance,
                       SemanticMemoryModel.embedding.is_not(None))
                .order_by(SemanticMemoryModel.embedding.cosine_distance(query_embedding))
                .limit(limit))
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def search_by_type(self, user_id: UUID, memory_type: str,
                             limit: int = 20) -> list[SemanticMemory]:
        stmt = (select(SemanticMemoryModel)
                .where(SemanticMemoryModel.user_id == user_id,
                       SemanticMemoryModel.memory_type == memory_type,
                       SemanticMemoryModel.is_active == True)  # noqa: E712
                .order_by(SemanticMemoryModel.importance.desc())
                .limit(limit))
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def upsert(self, memory: SemanticMemory) -> SemanticMemory:
        existing = await self.get_by_subject(memory.user_id, memory.subject)
        if existing:
            existing.update_evidence(memory.evidence_episodes, memory.content)
            await self.save(existing)
            return existing
        await self.save(memory)
        return memory

    async def get_by_subject(self, user_id: UUID, subject: str) -> SemanticMemory | None:
        stmt = select(SemanticMemoryModel).where(
            SemanticMemoryModel.user_id == user_id,
            SemanticMemoryModel.subject == subject,
            SemanticMemoryModel.is_active == True,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None


class SqlProceduralRepository(ProceduralRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> ProceduralMemory | None:
        model = await self._session.get(ProceduralMemoryModel, id)
        return model.to_domain() if model else None

    async def save(self, entity: ProceduralMemory) -> None:
        model = ProceduralMemoryModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity: ProceduralMemory) -> None:
        model = await self._session.get(ProceduralMemoryModel, entity.id)
        if model:
            model.is_active = False

    async def list_active(self, user_id: UUID, limit: int = 10) -> list[ProceduralMemory]:
        stmt = (select(ProceduralMemoryModel)
                .where(ProceduralMemoryModel.user_id == user_id,
                       ProceduralMemoryModel.is_active == True)  # noqa: E712
                .order_by(ProceduralMemoryModel.success_rate.desc())
                .limit(limit))
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def find_by_context(self, user_id: UUID, pattern_type: str | None = None,
                              limit: int = 5) -> list[ProceduralMemory]:
        stmt = select(ProceduralMemoryModel).where(
            ProceduralMemoryModel.user_id == user_id,
            ProceduralMemoryModel.is_active == True,  # noqa: E712
        )
        if pattern_type:
            stmt = stmt.where(ProceduralMemoryModel.pattern_type == pattern_type)
        stmt = stmt.order_by(ProceduralMemoryModel.success_rate.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]
```

---

## Day 5–6: Consolidation + Celery

### `src/pathfinder/agent/infrastructure/memory/consolidation.py`

```python
"""Memory consolidation pipeline — runs daily via Celery Beat."""
import json
from uuid import UUID, uuid4
from datetime import datetime, timezone
from celery.utils.log import get_task_logger
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.agent.infrastructure.memory.repositories import (
    SqlEpisodicRepository, SqlSemanticRepository, SqlProceduralRepository,
)
from pathfinder.agent.domain.memory.entities import SemanticMemory
from pathfinder.agent.domain.memory.value_objects import SemanticMemoryType
from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient

logger = get_task_logger(__name__)

CONSOLIDATION_PROMPT = """You are a memory consolidation engine. Analyze the user's recent interactions and extract structured knowledge.

For each insight discovered, output a JSON object with:
{{
    "type": "profile_fact|skill_knowledge|learned_insight|preference_fact",
    "subject": "short label (max 100 chars)",
    "content": {{structured fact data}},
    "confidence": 0.0-1.0
}}

RULES:
1. Only extract facts EXPLICITLY supported by the provided interactions.
2. If a fact contradicts a previous fact, flag it.
3. Merge similar facts rather than duplicating.
4. Output a JSON array of insight objects. Max 10 insights per consolidation run."""


async def consolidate_user_memories(user_id: str) -> dict:
    """Run full consolidation pipeline for one user."""
    maker = get_sessionmaker()
    run_id = uuid4()
    started_at = datetime.now(timezone.utc)

    async with maker() as session:
        episodic_repo = SqlEpisodicRepository(session)
        semantic_repo = SqlSemanticRepository(session)
        procedural_repo = SqlProceduralRepository(session)

        # 1. Fetch unconsolidated episodes
        episodes = await episodic_repo.list_unconsolidated(UUID(user_id))
        if not episodes:
            return {"status": "no_new_episodes", "user_id": user_id}

        # 2. LLM extraction
        llm = DeepSeekClient()
        episode_text = "\n".join(
            f"[{ep.episode_type.value}] {ep.action} | {ep.context_summary}"
            for ep in episodes[:200]  # Limit context window
        )

        insights = []
        tokens_used = 0
        try:
            response = await llm.chat_completion(
                system_prompt=CONSOLIDATION_PROMPT,
                user_prompt=f"Recent user interactions:\n\n{episode_text}",
                temperature=0.2,
            )
            tokens_used = response.tokens_used
            insights = json.loads(response.content)
            if not isinstance(insights, list):
                insights = []
        except Exception as e:
            logger.error(f"LLM consolidation failed for user {user_id}: {e}")
            return {"status": "llm_failed", "error": str(e)[:200]}

        # 3. UPSERT semantic memories
        insights_generated = 0
        for insight in insights[:10]:
            try:
                memory_type = SemanticMemoryType(insight.get("type", "general_knowledge"))
                memory = SemanticMemory.create_fact(
                    user_id=UUID(user_id),
                    memory_type=memory_type,
                    subject=insight.get("subject", "")[:100],
                    content=insight.get("content", {}),
                    confidence=float(insight.get("confidence", 0.5)),
                    evidence=[ep.id for ep in episodes[:10]],
                )
                await semantic_repo.upsert(memory)
                insights_generated += 1
            except Exception as e:
                logger.warning(f"Failed to upsert insight: {e}")

        # 4. Mark episodes consolidated
        episode_ids = [ep.id for ep in episodes]
        marked = await episodic_repo.mark_consolidated(episode_ids, run_id)

        await session.commit()

    return {
        "status": "completed",
        "user_id": user_id,
        "run_id": str(run_id),
        "episodes_processed": len(episodes),
        "marked_consolidated": marked,
        "insights_generated": insights_generated,
        "tokens_used": tokens_used,
        "started_at": started_at.isoformat(),
    }
```

### `src/pathfinder/agent/infrastructure/celery_tasks/memory_tasks.py`

```python
"""Celery tasks for memory operations."""
import asyncio
from celery.utils.log import get_task_logger
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.agent.infrastructure.memory.consolidation import consolidate_user_memories

logger = get_task_logger(__name__)


async def _consolidate_all_active_users_async(batch_size: int = 100) -> dict:
    """Consolidate memories for all users active in the last 7 days."""
    maker = get_sessionmaker()
    async with maker() as session:
        from sqlalchemy import select, text
        # Find users with unconsolidated episodes
        stmt = text("""
            SELECT DISTINCT user_id FROM episodic_memories
            WHERE is_consolidated = false
            AND created_at > NOW() - INTERVAL '7 days'
            LIMIT :limit
        """)
        result = await session.execute(stmt, {"limit": batch_size})
        user_ids = [row[0] for row in result]

    total_insights = 0
    successes = 0
    failures = 0

    for user_id in user_ids:
        try:
            res = await consolidate_user_memories(str(user_id))
            if res.get("status") == "completed":
                successes += 1
                total_insights += res.get("insights_generated", 0)
            else:
                failures += 1
        except Exception as e:
            logger.error(f"Consolidation failed for user {user_id}: {e}")
            failures += 1

    logger.info(f"Consolidation complete: {successes} users, {total_insights} insights, {failures} failures")
    return {"users_processed": successes + failures, "successes": successes,
            "failures": failures, "insights_generated": total_insights}


async def _cleanup_expired_memories_async() -> dict:
    """Delete episodic memories past their expiration date."""
    maker = get_sessionmaker()
    async with maker() as session:
        from sqlalchemy import text
        result = await session.execute(text(
            "DELETE FROM episodic_memories WHERE expires_at < NOW()"
        ))
        await session.commit()
        deleted = result.rowcount or 0
        logger.info(f"Cleaned up {deleted} expired episodic memories")
        return {"deleted_count": deleted}


# Celery task wrappers
def consolidate_all_active_users(batch_size: int = 100):
    return asyncio.run(_consolidate_all_active_users_async(batch_size))

def cleanup_expired_memories():
    return asyncio.run(_cleanup_expired_memories_async())
```

### Celery Beat Schedule — Update `scraping.py`:

```python
# Add to existing beat_schedule:
"consolidate-memories": {
    "task": "consolidate_all_active_users",
    "schedule": crontab(hour="3", minute="17"),  # Daily at 03:17 UTC
    "kwargs": {"batch_size": 100},
},
"cleanup-expired-memories": {
    "task": "cleanup_expired_memories",
    "schedule": crontab(hour="4", minute="47"),  # Daily at 04:47 UTC
},
```

---

## Day 7: Agent Integration

### Update `context_builder_node` to load memories

**File:** `src/pathfinder/agent/infrastructure/langgraph/nodes/context_builder.py`

```python
# ADD after profile/preferences loading:
from pathfinder.agent.infrastructure.memory.repositories import (
    SqlEpisodicRepository, SqlSemanticRepository, SqlProceduralRepository,
)

# ── Memory retrieval (added to context_builder) ──
episodic_repo = SqlEpisodicRepository(session)
semantic_repo = SqlSemanticRepository(session)
procedural_repo = SqlProceduralRepository(session)

# Recent episodes
recent = await episodic_repo.list_recent(UUID(user_id), limit=20)

# Relevant semantic memories (if user_message and intent are available)
intent = state.get("intent", "")
user_message = state.get("user_message", "")
semantic = []
if intent:
    semantic = await semantic_repo.search_by_type(
        UUID(user_id), memory_type="learned_insight", limit=10,
    )

# Procedural patterns
procedural = await procedural_repo.list_active(UUID(user_id), limit=3)

# Build memory context text
memory_lines = []
if semantic:
    memory_lines.append("**What I know about you:**")
    for s in semantic[:5]:
        memory_lines.append(f"- {s.subject}: {s.content_text[:200]}")
if recent:
    memory_lines.append("\n**Recent context:**")
    for ep in recent[:10]:
        if ep.context_summary:
            memory_lines.append(f"- {ep.context_summary[:150]}")

context = {
    # ... existing fields ...
    "recent_history": [
        {"type": ep.episode_type.value, "summary": ep.context_summary,
         "timestamp": ep.created_at.isoformat() if ep.created_at else ""}
        for ep in recent[:15]
    ],
    "memory_context": "\n".join(memory_lines) if memory_lines else "",
    # ...
}
```

### Episodic logging on every agent execution

**File:** `src/pathfinder/agent/presentation/router.py` — After agent execution completes:

```python
# After final_state is obtained, log episodic memory:
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.agent.domain.memory.entities import EpisodicMemory
from pathfinder.agent.domain.memory.value_objects import ImportanceCalculator

async def _log_agent_episode(user_id: UUID, session_id: UUID, call_id: UUID,
                              intent: str, user_message: str, final_state: dict):
    maker = get_sessionmaker()
    async with maker() as session:
        repo = SqlEpisodicRepository(session)
        episode = EpisodicMemory.record_agent_execution(
            user_id=user_id, session_id=session_id, call_id=call_id,
            intent=intent or "unknown",
            user_message=user_message,
            tool_results=[{"step": k, "result": v}
                         for k, v in final_state.get("tool_results", {}).items()],
            final_response=final_state.get("final_response", ""),
            latency_ms=final_state.get("total_latency_ms", 0),
            is_success=not final_state.get("errors"),
        )
        await repo.save(episode)
        await session.commit()
```

---

## Day 8–9: API + Migration + Agent State Update

### Migration — `alembic/versions/007_memory_indexes.py`

```python
"""007_memory_indexes — Add HNSW indexes on memory embedding columns."""
revision = "007"
down_revision = "006"

def upgrade():
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_episodic_embedding ON episodic_memories "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 12, ef_construction = 150)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_semantic_embedding ON semantic_memories "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 200)"
    )

def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_episodic_embedding")
    op.execute("DROP INDEX IF EXISTS idx_semantic_embedding")
```

### Update SupervisorState (add memory fields)

**File:** `src/pathfinder/agent/domain/state.py` — Add to `SupervisorState`:

```python
# ── Memory (populated by context_builder node) ──
recent_history: list[dict]       # Last 15 episodic memories
memory_context: str              # Formatted memory text for LLM prompts
```

### Memory API (minimal)

**File:** `src/pathfinder/agent/presentation/router.py` — Add endpoint:

```python
@router.get("/memory/context")
async def get_memory_context(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return what the system remembers about the user. Transparency endpoint."""
    semantic_repo = SqlSemanticRepository(session)
    episodic_repo = SqlEpisodicRepository(session)

    facts = await semantic_repo.search_by_type(current_user.id, limit=50)
    recent = await episodic_repo.list_recent(current_user.id, limit=10)

    return {
        "data": {
            "facts_about_you": [
                {"subject": f.subject, "content": f.content_text,
                 "confidence": f.confidence, "type": f.memory_type.value}
                for f in facts if f.is_active
            ],
            "facts_count": len([f for f in facts if f.is_active]),
            "recent_interactions": [
                {"action": ep.action, "timestamp": ep.created_at.isoformat()}
                for ep in recent[:10]
            ],
            "total_episodes": "Computed separately",  # Heavy query — defer
        }
    }
```

---

## Day 10: Tests + Gate Review

### `tests/unit/agent/memory/test_entities.py`

```python
from uuid import uuid4
from pathfinder.agent.domain.memory.entities import EpisodicMemory, SemanticMemory
from pathfinder.agent.domain.memory.value_objects import (
    EpisodeType, SemanticMemoryType, ImportanceScore, MemoryImportance,
)

def test_record_agent_execution():
    ep = EpisodicMemory.record_agent_execution(
        user_id=uuid4(), session_id=uuid4(), call_id=uuid4(),
        intent="search_jobs", user_message="find python jobs",
        tool_results=[], final_response="Found 5 jobs",
        latency_ms=1200, is_success=True,
    )
    assert ep.episode_type == EpisodeType.AGENT_INVOCATION
    assert ep.importance.value >= 0.4

def test_record_feedback():
    ep = EpisodicMemory.record_feedback(
        user_id=uuid4(), job_id=uuid4(), feedback="thumbs_up",
    )
    assert ep.importance.value >= 0.5

def test_semantic_update_evidence():
    m = SemanticMemory.create_fact(
        user_id=uuid4(), memory_type=SemanticMemoryType.LEARNED_INSIGHT,
        subject="User prefers remote", content={"preference": "remote"},
    )
    assert m.confidence == 0.5
    m.update_evidence([uuid4(), uuid4()])
    assert m.confidence > 0.5
    assert m.evidence_count == 3  # 1 original + 2 new

def test_importance_decay():
    imp = ImportanceScore(value=0.5)
    decayed = imp.decay(days_since_creation=365)
    assert decayed.value < 0.5

def test_critical_importance_does_not_decay():
    imp = ImportanceScore(value=0.95)
    decayed = imp.decay(days_since_creation=365)
    assert decayed.value == 0.95
```

### `tests/unit/agent/memory/test_importance.py`

```python
from pathfinder.agent.domain.memory.services import ImportanceCalculator
from pathfinder.agent.domain.memory.value_objects import EpisodeType

def test_application_event_is_high_importance():
    score = ImportanceCalculator.calculate(EpisodeType.APPLICATION_EVENT)
    assert score.value >= 0.6

def test_system_event_is_low_importance():
    score = ImportanceCalculator.calculate(EpisodeType.SYSTEM_EVENT)
    assert score.value <= 0.2

def test_feedback_thumbs_up_boosted():
    score = ImportanceCalculator.calculate(
        EpisodeType.USER_FEEDBACK,
        payload={"feedback": "thumbs_up"},
    )
    assert score.value >= 0.5
```

### `tests/integration/api/test_memory_api.py`

```python
import pytest
from httpx import ASGITransport, AsyncClient
from pathfinder.shared.infrastructure.main import create_app

pytestmark = pytest.mark.integration

async def test_memory_context_endpoint():
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/v1/auth/register", json={
            "email": "mem-test@test.com", "password": "Test1234!",
            "full_name": "Memory Tester", "accept_terms": True,
        })
        token = resp.json()["data"]["tokens"]["access_token"]
        resp = await c.get("/v1/agent/memory/context",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "facts_about_you" in data
        assert "recent_interactions" in data
```

### Gate Checklist

```
☐ EpisodicMemory: recorded on every agent execution
☐ SemanticMemory: UPSERT with evidence tracking
☐ ProceduralMemory: pattern tracking with success rates
☐ Vector search: semantic memories retrieved by cosine similarity (HNSW)
☐ Recent episodes: retrieved by user_id + created_at DESC
☐ Consolidation pipeline: fetch → LLM extract → UPSERT → mark consolidated
☐ Celery Beat: daily consolidation at 03:17 UTC
☐ Celery Beat: cleanup expired at 04:47 UTC
☐ Agent context builder updated: loads recent + semantic + procedural
☐ GET /v1/agent/memory/context → 200 with memory transparency
☐ Migration 007: HNSW indexes created
☐ Agent state: recent_history + memory_context fields populated
☐ All unit tests pass (12+)
☐ All integration tests pass (4+)
☐ ruff check → 0. mypy --strict → 0
```

---

> *"Sprint 7: The agent now remembers. Every interaction teaches it something. Consolidation extracts wisdom from the noise. This is the moat."*

**End of Sprint 7**
