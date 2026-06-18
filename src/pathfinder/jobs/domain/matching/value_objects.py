"""Matching domain value objects."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from pathfinder.shared.domain.base_value_object import BaseValueObject
from pathfinder.shared.domain.exceptions import ValidationError


class MatchDimensionType(StrEnum):
    SKILLS = "skills"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    LOCATION = "location"
    PREFERENCE = "preference"
    CULTURE = "culture"


class GapSeverity(StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    NONE = "none"


@dataclass(frozen=True, kw_only=True)
class DimensionScore(BaseValueObject):
    dimension: MatchDimensionType
    score: float
    weight: float
    confidence: float = 1.0
    evidence: tuple[str, ...] = field(default_factory=tuple)
    raw_details: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValidationError(f"Score must be 0-100, got {self.score}")

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass(frozen=True, kw_only=True)
class MatchExplanation(BaseValueObject):
    category: str = "strength"
    text: str = ""
    dimension: MatchDimensionType | None = None
    evidence: tuple[str, ...] = field(default_factory=tuple)
    importance: float = 0.5


@dataclass(frozen=True, kw_only=True)
class SkillGap(BaseValueObject):
    skill_name: str
    category: str = "technology"
    severity: GapSeverity = GapSeverity.MINOR
    required_for_job: bool = True
    user_has_similar: tuple[str, ...] = field(default_factory=tuple)
    learning_resources: tuple[dict, ...] = field(default_factory=tuple)
    estimated_hours_to_learn: int | None = None


@dataclass(frozen=True, kw_only=True)
class MatchRecommendation(BaseValueObject):
    recommendation_type: str = "job"
    title: str = ""
    description: str = ""
    priority: int = 3
    action_url: str = ""
