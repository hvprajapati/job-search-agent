"""Tailoring domain value objects."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from pathfinder.shared.domain.base_value_object import BaseValueObject


class TailoringStrategy(StrEnum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    ATS_ONLY = "ats_only"


class ChangeType(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    REORDERED = "reordered"
    UNCHANGED = "unchanged"


class KeywordImportance(StrEnum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


@dataclass(frozen=True, kw_only=True)
class KeywordEntry(BaseValueObject):
    keyword: str
    importance: str = "recommended"
    in_original: bool = False
    in_tailored: bool = False
    density: float = 0.0


@dataclass(frozen=True, kw_only=True)
class KeywordAnalysis(BaseValueObject):
    keywords: tuple[KeywordEntry, ...] = field(default_factory=tuple)
    coverage_before: float = 0.0
    coverage_after: float = 0.0
    added_count: int = 0
    removed_count: int = 0
    stuffing_risk: bool = False


@dataclass(frozen=True, kw_only=True)
class ResumeDiff(BaseValueObject):
    section: str
    change_type: str = "modified"
    before: str = ""
    after: str = ""
    rationale: str = ""
    expected_impact: str = ""


@dataclass(frozen=True, kw_only=True)
class ResumeScore(BaseValueObject):
    ats_score: int = 0
    keyword_coverage: float = 0.0
    readability_score: int = 0
    section_completeness: float = 0.0
    overall_score: int = 0


@dataclass(frozen=True, kw_only=True)
class GapReport(BaseValueObject):
    missing_skills: tuple[str, ...] = field(default_factory=tuple)
    missing_technologies: tuple[str, ...] = field(default_factory=tuple)
    missing_certifications: tuple[str, ...] = field(default_factory=tuple)
    experience_gaps: tuple[str, ...] = field(default_factory=tuple)
    honest_gaps: tuple[dict, ...] = field(default_factory=tuple)


@dataclass(frozen=True, kw_only=True)
class TailoringRequest(BaseValueObject):
    user_id: str
    base_resume_id: str
    job_id: str
    strategy: str = "moderate"
    emphasis: tuple[str, ...] = field(default_factory=tuple)
    sections_to_tailor: tuple[str, ...] = field(
        default_factory=lambda: ("summary", "skills", "experience")
    )
