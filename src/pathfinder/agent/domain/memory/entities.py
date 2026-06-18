"""Memory domain entities — Episodic, Semantic, Procedural."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.agent.domain.memory.value_objects import (
    EpisodeType, SemanticMemoryType, PatternType,
    ImportanceScore, MemoryEmbedding,
)


@dataclass(kw_only=True)
class EpisodicMemory(BaseEntity):
    user_id: UUID
    session_id: UUID | None = None
    episode_type: EpisodeType = EpisodeType.SYSTEM_EVENT
    actor: str = "system"
    action: str = ""
    payload: dict = field(default_factory=dict)
    importance: ImportanceScore = field(default_factory=lambda: ImportanceScore(value=0.3))
    embedding: MemoryEmbedding | None = None
    context_summary: str = ""
    parent_episode_id: UUID | None = None
    consolidation_run_id: UUID | None = None
    is_consolidated: bool = False
    expires_at: datetime | None = None

    @classmethod
    def record_agent_execution(cls, *, user_id: UUID, session_id: UUID,
                               call_id: UUID, intent: str, user_message: str,
                               tool_results: list[dict], final_response: str,
                               latency_ms: int, is_success: bool) -> EpisodicMemory:
        importance = 0.7 if is_success else 0.5
        return cls(
            user_id=user_id, session_id=session_id,
            episode_type=EpisodeType.AGENT_INVOCATION,
            actor="supervisor_agent",
            action=f"Agent executed intent '{intent}' — {'success' if is_success else 'failed'}",
            payload={"call_id": str(call_id), "intent": intent, "user_message": user_message[:500],
                     "tool_results": tool_results[:10], "final_response": final_response[:500],
                     "latency_ms": latency_ms, "is_success": is_success},
            importance=ImportanceScore(value=importance),
            context_summary=f"Agent: {intent} — {final_response[:100]}",
            expires_at=datetime.now(timezone.utc) + timedelta(days=730 if importance >= 0.7 else 90),
        )

    @classmethod
    def record_feedback(cls, *, user_id: UUID, job_id: UUID,
                        feedback: str, session_id: UUID | None = None) -> EpisodicMemory:
        return cls(
            user_id=user_id, session_id=session_id,
            episode_type=EpisodeType.USER_FEEDBACK, actor="user",
            action=f"User gave feedback '{feedback}' on job {job_id}",
            payload={"job_id": str(job_id), "feedback": feedback},
            importance=ImportanceScore(value=0.6),
            context_summary=f"User {feedback} job {job_id}",
            expires_at=datetime.now(timezone.utc) + timedelta(days=730),
        )

    def mark_consolidated(self, run_id: UUID) -> None:
        self.consolidation_run_id = run_id
        self.is_consolidated = True
        self.mark_updated()


@dataclass(kw_only=True)
class SemanticMemory(BaseEntity):
    user_id: UUID
    memory_type: SemanticMemoryType = SemanticMemoryType.GENERAL_KNOWLEDGE
    subject: str = ""
    content: dict = field(default_factory=dict)
    content_text: str = ""
    embedding: MemoryEmbedding | None = None
    confidence: float = 0.5
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
            user_id=user_id, memory_type=memory_type, subject=subject,
            content=content, content_text=str(content), confidence=confidence,
            evidence_episodes=evidence or [], evidence_count=len(evidence) if evidence else 1,
        )

    def update_evidence(self, new_episodes: list[UUID], new_content: dict | None = None) -> None:
        existing = {str(e) for e in self.evidence_episodes}
        for ep in new_episodes:
            if str(ep) not in existing:
                self.evidence_episodes.append(ep)
        self.evidence_count = len(self.evidence_episodes)
        self.confidence = min(0.95, self.confidence + 0.03 * len(new_episodes))
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
    user_id: UUID
    pattern_type: PatternType = PatternType.SEARCH_BEHAVIOR
    context_signature: str = ""
    context_embedding: MemoryEmbedding | None = None
    action_sequence: dict = field(default_factory=dict)
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
