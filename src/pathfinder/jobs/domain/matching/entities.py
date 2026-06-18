"""Matching domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.jobs.domain.matching.value_objects import (
    DimensionScore, MatchExplanation, SkillGap, MatchRecommendation,
    MatchDimensionType, GapSeverity,
)


@dataclass(kw_only=True)
class MatchResult(BaseEntity):
    user_id: UUID
    job_id: UUID
    overall_score: float = 0.0
    dimensions: list[DimensionScore] = field(default_factory=list)
    strengths: list[MatchExplanation] = field(default_factory=list)
    weaknesses: list[MatchExplanation] = field(default_factory=list)
    skill_gaps: list[SkillGap] = field(default_factory=list)
    risks: list[MatchExplanation] = field(default_factory=list)
    profile_version_used: int = 1
    preferences_version_used: int = 1
    job_snapshot_title: str = ""
    job_snapshot_company: str = ""
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_stale: bool = False
    feedback: str | None = None
    recommendations: list[MatchRecommendation] = field(default_factory=list)

    @classmethod
    def create_empty(cls, *, user_id: UUID, job_id: UUID) -> MatchResult:
        return cls(user_id=user_id, job_id=job_id)

    def add_dimension(self, score: DimensionScore) -> None:
        self.dimensions.append(score)

    def compute_overall(self, expected_total_weight: float = 1.0) -> float:
        if not self.dimensions:
            return 0.0
        total_weight = sum(d.weight for d in self.dimensions)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(d.weighted_score for d in self.dimensions)
        completeness = min(1.0, total_weight / max(expected_total_weight, 0.01))
        self.overall_score = round((weighted_sum / total_weight) * completeness, 1)
        self.mark_updated()
        return self.overall_score

    def add_strength(self, text: str, dimension: MatchDimensionType | None = None) -> None:
        self.strengths.append(MatchExplanation(
            category="strength", text=text, dimension=dimension,
        ))

    def add_weakness(self, text: str, dimension: MatchDimensionType | None = None) -> None:
        self.weaknesses.append(MatchExplanation(
            category="weakness", text=text, dimension=dimension,
        ))

    def add_gap(self, gap: SkillGap) -> None:
        self.skill_gaps.append(gap)

    def add_risk(self, text: str) -> None:
        self.risks.append(MatchExplanation(category="risk", text=text))

    def record_feedback(self, feedback: str) -> None:
        valid = {"thumbs_up", "thumbs_down", "dismiss"}
        if feedback not in valid:
            raise ValueError(f"Invalid feedback: {feedback}")
        self.feedback = feedback
        self.mark_updated()

    @property
    def is_high_match(self) -> bool:
        return self.overall_score >= 85

    @property
    def has_dealbreaker_gap(self) -> bool:
        return any(g.severity == GapSeverity.CRITICAL and g.required_for_job
                   for g in self.skill_gaps)

    @property
    def skill_score(self) -> float:
        return self._dim_score(MatchDimensionType.SKILLS)

    @property
    def experience_score(self) -> float:
        return self._dim_score(MatchDimensionType.EXPERIENCE)

    def _dim_score(self, dim_type: MatchDimensionType) -> float:
        for d in self.dimensions:
            if d.dimension == dim_type:
                return d.score
        return 0.0
