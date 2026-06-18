"""Agent domain value objects."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from pathfinder.shared.domain.base_value_object import BaseValueObject


class Intent(StrEnum):
    SEARCH_JOBS = "search_jobs"
    MATCH_ME = "match_me"
    TAILOR_RESUME = "tailor_resume"
    GENERATE_COVER_LETTER = "generate_cover_letter"
    PREP_INTERVIEW = "prep_interview"
    TRACK_APPLICATIONS = "track_applications"
    FOLLOW_UP = "follow_up"
    ANALYZE_SKILL_GAP = "analyze_skill_gap"
    CAREER_ADVICE = "career_advice"
    UPDATE_PROFILE = "update_profile"
    GENERAL_QUESTION = "general_question"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, kw_only=True)
class ToolDefinition(BaseValueObject):
    name: str
    description: str
    parameters: dict
    requires_approval: bool = False
    is_expensive: bool = False
    tier_required: str = "free"


@dataclass(frozen=True, kw_only=True)
class ToolResult(BaseValueObject):
    tool_name: str
    success: bool
    data: dict | None = None
    error: str | None = None
    latency_ms: int = 0
    tokens_used: int = 0
