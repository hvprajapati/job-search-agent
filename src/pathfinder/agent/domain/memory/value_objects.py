"""Memory domain value objects."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from datetime import datetime, timezone
from pathfinder.shared.domain.base_value_object import BaseValueObject


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


@dataclass(frozen=True, kw_only=True)
class ImportanceScore(BaseValueObject):
    value: float = 0.3
    source: str = "heuristic"
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True, kw_only=True)
class MemoryEmbedding(BaseValueObject):
    vector: tuple[float, ...]
    model: str = "deepseek-embed"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
