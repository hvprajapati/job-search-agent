# Pathfinder — Sprint 5: Job Matching Domain

**Sprint:** 5 of 7
**Duration:** 10 Days
**Prerequisite:** Sprint 4 (jobs flowing into DB, search operational)
**Goal:** Multi-dimensional matching with LLM explanations, skill gap analysis, and personalized recommendations. The core differentiator of Pathfinder.
**Source:** FINAL_ARCHITECTURE.md §7 + EPICS_AND_TASKS.md Epic 3

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MATCHING ENGINE ARCHITECTURE                          │
│                                                                              │
│  INPUT                                     OUTPUT                            │
│  ─────                                     ──────                            │
│  ┌──────────┐                              ┌──────────────┐                 │
│  │ Profile  │──┐                           │ MatchResult  │                 │
│  │ (skills, │  │    ┌──────────────┐       │ · overall    │                 │
│  │  exp,    │  │    │              │       │ · skills     │                 │
│  │  edu)    │  ├───→│   MATCHING   │──────→│ · experience │                 │
│  └──────────┘  │    │   ENGINE     │       │ · education  │                 │
│                │    │              │       │ · location   │                 │
│  ┌──────────┐  │    │ 6 Dimension  │       │ · preference │                 │
│  │ Job      │──┤    │ Scorers      │       │ · culture    │                 │
│  │ (JD,     │  │    │              │       │              │                 │
│  │  skills, │  │    └──────┬───────┘       │ Explanation[]│                 │
│  │  company)│  │           │               │ SkillGaps[]  │                 │
│  └──────────┘  │           │               │ Strengths[]  │                 │
│                │           │               │ Weaknesses[] │                 │
│  ┌──────────┐  │           │               └──────────────┘                 │
│  │Preference│──┘           │                                                 │
│  │ weights  │              │                                                 │
│  └──────────┘              │                                                 │
│                            ▼                                                 │
│                     ┌──────────────┐                                         │
│                     │EXPLAINABILITY│──→ Natural language reasons            │
│                     │   ENGINE     │    (LLM, evidence-grounded)            │
│                     └──────────────┘                                         │
│                            │                                                 │
│                            ▼                                                 │
│                     ┌──────────────┐                                         │
│                     │ SKILL GAP    │──→ Missing skills, technologies,       │
│                     │ ANALYZER     │    certifications, learning paths      │
│                     └──────────────┘                                         │
│                            │                                                 │
│                            ▼                                                 │
│                     ┌──────────────┐                                         │
│                     │RECOMMENDATION│──→ Ranked jobs, learning plans,        │
│                     │   ENGINE     │    certifications, projects            │
│                     └──────────────┘                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Day 1–2: Domain Core

### Files to Create

```
src/pathfinder/jobs/domain/
├── matching/
│   ├── __init__.py
│   ├── entities.py        # MatchResult aggregate
│   ├── value_objects.py   # MatchScore, MatchDimension, MatchExplanation, SkillGap
│   ├── repositories.py    # MatchRepository (abstract)
│   ├── services.py        # DimensionScorer ABCs, MatchingOrchestrator
│   ├── events.py          # MatchComputed, HighScoreMatchFound
│   └── exceptions.py      # MatchingError, InsufficientProfileError

tests/unit/jobs/matching/
├── test_match_entity.py
├── test_dimension_scorers.py
├── test_match_orchestrator.py
└── test_skill_gap.py
```

### `src/pathfinder/jobs/domain/matching/value_objects.py`

```python
"""Matching domain value objects."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from datetime import datetime, timezone
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
    CRITICAL = "critical"    # Dealbreaker — missing required skill
    MAJOR = "major"          # Significant gap — needs learning plan
    MINOR = "minor"          # Nice-to-have gap
    NONE = "none"            # No gap


class StrengthCategory(StrEnum):
    SKILL_MATCH = "skill_match"
    EXPERIENCE_MATCH = "experience_match"
    DOMAIN_EXPERTISE = "domain_expertise"
    CULTURE_FIT = "culture_fit"
    TECH_STACK = "tech_stack"


class RiskCategory(StrEnum):
    MISSING_REQUIRED_SKILL = "missing_required_skill"
    EXPERIENCE_GAP = "experience_gap"
    EDUCATION_GAP = "education_gap"
    LOCATION_CONSTRAINT = "location_constraint"
    COMPENSATION_MISMATCH = "compensation_mismatch"


@dataclass(frozen=True, kw_only=True)
class DimensionScore(BaseValueObject):
    """Score for a single matching dimension (0-100). Zero means no match; 100 means perfect."""
    dimension: MatchDimensionType
    score: float  # 0-100
    weight: float  # Contribution weight to overall (0.0-1.0)
    confidence: float = 1.0  # How confident we are in this score (0.0-1.0)
    evidence: tuple[str, ...] = field(default_factory=tuple)  # What we based this on
    raw_details: dict = field(default_factory=dict)  # Dimension-specific details

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValidationError(f"Score must be 0-100, got {self.score}", field="score")
        if not 0 <= self.weight <= 1:
            raise ValidationError(f"Weight must be 0-1, got {self.weight}", field="weight")
        if not 0 <= self.confidence <= 1:
            raise ValidationError(f"Confidence must be 0-1, got {self.confidence}", field="confidence")

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass(frozen=True, kw_only=True)
class MatchExplanation(BaseValueObject):
    """A single natural-language explanation of why something matched or didn't."""
    category: str  # "strength", "weakness", "gap", "risk", "neutral"
    text: str       # Human-readable explanation
    dimension: MatchDimensionType | None = None
    evidence: tuple[str, ...] = field(default_factory=tuple)  # Profile/job facts backing this
    importance: float = 0.5  # How important is this explanation (0-1)


@dataclass(frozen=True, kw_only=True)
class SkillGap(BaseValueObject):
    """A specific skill or qualification the user lacks for this job."""
    skill_name: str
    category: str  # "technology", "certification", "experience", "education", "soft_skill"
    severity: GapSeverity = GapSeverity.MINOR
    required_for_job: bool = True  # True = job requires it, False = nice-to-have
    user_has_similar: tuple[str, ...] = field(default_factory=tuple)  # Adjacent skills user has
    learning_resources: tuple[dict, ...] = field(default_factory=tuple)  # Suggested resources
    estimated_hours_to_learn: int | None = None


@dataclass(frozen=True, kw_only=True)
class MatchRecommendation(BaseValueObject):
    """A recommended action based on match analysis."""
    recommendation_type: str  # "job", "learning_path", "certification", "project", "skill"
    title: str
    description: str = ""
    priority: int = 3  # 1=highest, 5=lowest
    action_url: str = ""
    related_job_ids: tuple[str, ...] = field(default_factory=tuple)
    estimated_impact: str = ""  # "Could increase match score by 15 points"


@dataclass(frozen=True, kw_only=True)
class MatchSummary(BaseValueObject):
    """Compact match summary for list views (avoids loading full MatchResult)."""
    job_id: str
    overall_score: float
    top_strength: str = ""       # One-line summary of top strength
    top_gap: str = ""            # One-line summary of biggest gap
    skill_match_score: float = 0.0
    computed_at: str = ""        # ISO timestamp
```

### `src/pathfinder/jobs/domain/matching/entities.py`

```python
"""Matching domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.shared.domain.identifiers import UserId, JobId
from pathfinder.jobs.domain.matching.value_objects import (
    DimensionScore, MatchExplanation, SkillGap, MatchRecommendation,
    MatchDimensionType, GapSeverity, StrengthCategory, RiskCategory,
)


@dataclass(kw_only=True)
class MatchResult(BaseEntity):
    """The complete matching analysis between a user and a job."""

    # Identity
    user_id: UUID
    job_id: UUID

    # Scores
    overall_score: float = 0.0  # 0-100 weighted composite
    dimensions: list[DimensionScore] = field(default_factory=list)

    # Analysis
    strengths: list[MatchExplanation] = field(default_factory=list)
    weaknesses: list[MatchExplanation] = field(default_factory=list)
    skill_gaps: list[SkillGap] = field(default_factory=list)
    risks: list[MatchExplanation] = field(default_factory=list)

    # Metadata
    profile_version_used: int = 1
    preferences_version_used: int = 1
    job_snapshot_title: str = ""
    job_snapshot_company: str = ""
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_stale: bool = False
    feedback: str | None = None  # User feedback: "thumbs_up", "thumbs_down", "dismiss", null

    # Recommendations
    recommendations: list[MatchRecommendation] = field(default_factory=list)

    @classmethod
    def create_empty(cls, *, user_id: UUID, job_id: UUID,
                     profile_version: int = 1, pref_version: int = 1) -> MatchResult:
        return cls(
            user_id=user_id, job_id=job_id,
            profile_version_used=profile_version,
            preferences_version_used=pref_version,
        )

    def add_dimension(self, score: DimensionScore) -> None:
        existing = [d for d in self.dimensions if d.dimension == score.dimension]
        if not existing:
            self.dimensions.append(score)
        self.mark_updated()

    def compute_overall(self) -> float:
        if not self.dimensions:
            return 0.0
        total_weight = sum(d.weight for d in self.dimensions)
        if total_weight == 0:
            return 0.0
        self.overall_score = round(
            sum(d.weighted_score for d in self.dimensions) / total_weight, 1
        )
        self.mark_updated()
        return self.overall_score

    def add_strength(self, text: str, dimension: MatchDimensionType | None = None,
                     evidence: tuple[str, ...] = (), importance: float = 0.5) -> None:
        self.strengths.append(MatchExplanation(
            category="strength", text=text, dimension=dimension,
            evidence=evidence, importance=importance,
        ))

    def add_weakness(self, text: str, dimension: MatchDimensionType | None = None,
                     evidence: tuple[str, ...] = (), importance: float = 0.5) -> None:
        self.weaknesses.append(MatchExplanation(
            category="weakness", text=text, dimension=dimension,
            evidence=evidence, importance=importance,
        ))

    def add_risk(self, text: str, evidence: tuple[str, ...] = ()) -> None:
        self.risks.append(MatchExplanation(
            category="risk", text=text, evidence=evidence, importance=0.8,
        ))

    def add_gap(self, gap: SkillGap) -> None:
        self.skill_gaps.append(gap)

    def add_recommendation(self, rec: MatchRecommendation) -> None:
        self.recommendations.append(rec)

    def record_feedback(self, feedback: str) -> None:
        valid = {"thumbs_up", "thumbs_down", "dismiss"}
        if feedback not in valid:
            raise ValueError(f"Invalid feedback: {feedback}. Must be one of {valid}")
        self.feedback = feedback
        self.mark_updated()

    def mark_stale(self) -> None:
        self.is_stale = True
        self.mark_updated()

    @property
    def skill_score(self) -> float:
        return self._dimension_score(MatchDimensionType.SKILLS)

    @property
    def experience_score(self) -> float:
        return self._dimension_score(MatchDimensionType.EXPERIENCE)

    @property
    def is_high_match(self) -> bool:
        return self.overall_score >= 85

    @property
    def has_dealbreaker_gap(self) -> bool:
        return any(g.severity == GapSeverity.CRITICAL and g.required_for_job
                   for g in self.skill_gaps)

    def _dimension_score(self, dim_type: MatchDimensionType) -> float:
        for d in self.dimensions:
            if d.dimension == dim_type:
                return d.score
        return 0.0
```

### `src/pathfinder/jobs/domain/matching/repositories.py`

```python
"""Matching repository interfaces (abstract)."""
from abc import abstractmethod
from uuid import UUID
from pathfinder.shared.domain.base_repository import BaseRepository
from pathfinder.jobs.domain.matching.entities import MatchResult
from pathfinder.jobs.domain.matching.value_objects import MatchSummary


class MatchRepository(BaseRepository[MatchResult]):
    @abstractmethod
    async def get_by_user_and_job(self, user_id: UUID, job_id: UUID) -> MatchResult | None: ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID, *, min_score: float = 0.0,
                           cursor: str | None = None,
                           limit: int = 20) -> tuple[list[MatchResult], str | None]: ...

    @abstractmethod
    async def list_summaries_by_user(self, user_id: UUID, *, min_score: float = 0.0,
                                     cursor: str | None = None, limit: int = 50,
                                     ) -> tuple[list[MatchSummary], str | None]: ...

    @abstractmethod
    async def get_high_matches(self, user_id: UUID, threshold: float = 85.0,
                               limit: int = 10) -> list[MatchResult]: ...

    @abstractmethod
    async def delete_by_user_and_job(self, user_id: UUID, job_id: UUID) -> bool: ...

    @abstractmethod
    async def mark_stale_for_user(self, user_id: UUID) -> int: ...
```

### `src/pathfinder/jobs/domain/matching/services.py`

```python
"""Matching domain services — dimension scorers and orchestrator."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID
from pathfinder.jobs.domain.matching.value_objects import (
    DimensionScore, MatchDimensionType, SkillGap, GapSeverity,
    MatchRecommendation,
)
from pathfinder.jobs.domain.matching.entities import MatchResult


@dataclass
class MatchContext:
    """All data needed to compute a match."""
    user_id: UUID
    job_id: UUID
    # User data
    user_skills: list[dict]        # [{name, proficiency, years, category}, ...]
    user_experiences: list[dict]   # [{company, title, years, description, tech_stack}, ...]
    user_education: list[dict]     # [{degree, field, institution}, ...]
    user_projects: list[dict]      # [{name, description, technologies}, ...]
    user_certifications: list[dict]
    user_languages: list[dict]
    user_location: dict | None     # {city, state, country}
    user_summary: str = ""
    # Job data
    job_title: str = ""
    job_description: str = ""
    job_required_skills: list[dict] = field(default_factory=list)  # [{name, importance}, ...]
    job_nice_to_have: list[dict] = field(default_factory=list)
    job_tech_stack: list[str] = field(default_factory=list)
    job_seniority: str = ""
    job_remote_policy: str = ""
    job_location: dict | None = None
    job_salary_range: dict | None = None
    job_company_name: str = ""
    job_company_industry: str = ""
    job_company_stage: str = ""
    # User preferences
    user_preferred_roles: list[str] = field(default_factory=list)
    user_preferred_industries: dict = field(default_factory=dict)  # name → weight
    user_preferred_locations: list[str] = field(default_factory=list)
    user_preferred_remote: str = ""
    user_min_salary: float | None = None
    user_priority_weights: dict = field(default_factory=dict)
    user_dealbreakers: list[dict] = field(default_factory=list)
    user_excluded_companies: list[str] = field(default_factory=list)


# ── Dimension Scorer Interfaces ──

class BaseDimensionScorer(ABC):
    """Each dimension (skills, experience, etc.) implements this interface."""

    @property
    @abstractmethod
    def dimension(self) -> MatchDimensionType: ...

    @property
    @abstractmethod
    def default_weight(self) -> float: ...

    @abstractmethod
    async def score(self, ctx: MatchContext) -> DimensionScore: ...

    @abstractmethod
    def extract_strengths(self, ctx: MatchContext, score: DimensionScore) -> list[str]: ...

    @abstractmethod
    def extract_gaps(self, ctx: MatchContext, score: DimensionScore) -> list[SkillGap]: ...


class SkillScorer(BaseDimensionScorer):
    dimension = MatchDimensionType.SKILLS
    default_weight = 0.30

    async def score(self, ctx: MatchContext) -> DimensionScore:
        if not ctx.user_skills or not ctx.job_required_skills:
            return DimensionScore(
                dimension=self.dimension, score=50.0, weight=self.default_weight,
                confidence=0.3, evidence=("Insufficient data for skill comparison",),
            )

        user_skill_names = {s["name"].lower() for s in ctx.user_skills}
        required_names = {s["name"].lower() for s in ctx.job_required_skills}
        nice_names = {s["name"].lower() for s in ctx.job_nice_to_have}

        required_matches = user_skill_names & required_names
        nice_matches = user_skill_names & nice_names
        all_required = required_names | nice_names

        if not all_required:
            return DimensionScore(
                dimension=self.dimension, score=60.0, weight=self.default_weight,
                confidence=0.3, evidence=("No skill requirements listed in job",),
            )

        # Weighted score: required matches count more than nice-to-have
        required_score = len(required_matches) / max(len(required_names), 1) * 70
        nice_score = len(nice_matches) / max(len(nice_names), 1) * 30 if nice_names else 0
        base_score = required_score + nice_score

        # Proficiency bonus: expert in matching skills adds up to 20 points
        prof_bonus = 0
        for skill in ctx.user_skills:
            if skill["name"].lower() in required_matches:
                prof = skill.get("proficiency", "intermediate")
                prof_bonus += {"expert": 4, "advanced": 2, "intermediate": 1}.get(prof, 0)
        prof_bonus = min(20, prof_bonus)

        final_score = min(100, base_score + prof_bonus)
        return DimensionScore(
            dimension=self.dimension, score=round(final_score, 1),
            weight=self.default_weight, confidence=0.85,
            evidence=(
                f"Matched {len(required_matches)}/{len(required_names)} required skills",
                f"Matched {len(nice_matches)}/{len(nice_names)} nice-to-have skills" if nice_names else "",
            ),
            raw_details={
                "required_matched": list(required_matches),
                "required_missing": list(required_names - user_skill_names),
                "nice_matched": list(nice_matches),
            },
        )

    def extract_strengths(self, ctx: MatchContext, score: DimensionScore) -> list[str]:
        strengths = []
        details = score.raw_details
        matched = details.get("required_matched", [])
        if matched:
            top = list(matched)[:3]
            strengths.append(f"Strong skill match: {', '.join(top).title()}")
        return strengths

    def extract_gaps(self, ctx: MatchContext, score: DimensionScore) -> list[SkillGap]:
        gaps = []
        details = score.raw_details
        missing = details.get("required_missing", [])
        for skill_name in missing:
            required = any(s["name"].lower() == skill_name and s.get("importance", "") == "critical"
                          for s in ctx.job_required_skills)
            user_has_similar = tuple(
                s["name"] for s in ctx.user_skills
                if any(kw in s["name"].lower() for kw in skill_name.lower().split())
            )
            gaps.append(SkillGap(
                skill_name=skill_name,
                category="technology",
                severity=GapSeverity.CRITICAL if required else GapSeverity.MAJOR,
                required_for_job=required,
                user_has_similar=user_has_similar,
            ))
        return gaps


class ExperienceScorer(BaseDimensionScorer):
    dimension = MatchDimensionType.EXPERIENCE
    default_weight = 0.25

    async def score(self, ctx: MatchContext) -> DimensionScore:
        total_years = sum(exp.get("years", 0) for exp in ctx.user_experiences)
        roles = [exp.get("title", "").lower() for exp in ctx.user_experiences]

        # Seniority alignment
        seniority_map = {
            "intern": (0, 1), "junior": (1, 3), "mid": (3, 6),
            "senior": (6, 10), "staff": (8, 15), "principal": (12, 99),
        }
        expected_range = seniority_map.get(ctx.job_seniority, (3, 8))
        years_score = min(100, (total_years / max(expected_range[0], 1)) * 70)

        # Title relevance (LLM-free heuristic for MVP)
        title_bonus = 0
        job_title_lower = ctx.job_title.lower()
        for role in roles:
            if any(w in job_title_lower for w in role.split()):
                title_bonus += 10
        title_bonus = min(30, title_bonus)

        score = min(100, years_score + title_bonus)
        return DimensionScore(
            dimension=self.dimension, score=round(score, 1),
            weight=self.default_weight, confidence=0.80,
            evidence=(f"User has {total_years} years of experience",),
            raw_details={"total_years": total_years, "roles": roles},
        )

    def extract_strengths(self, ctx: MatchContext, score: DimensionScore) -> list[str]:
        years = score.raw_details.get("total_years", 0)
        return [f"Years of experience ({years}y) aligns with role requirements"]

    def extract_gaps(self, ctx: MatchContext, score: DimensionScore) -> list[SkillGap]:
        gaps = []
        if score.score < 40:
            gaps.append(SkillGap(
                skill_name="General experience",
                category="experience",
                severity=GapSeverity.MAJOR,
                required_for_job=True,
            ))
        return gaps


class EducationScorer(BaseDimensionScorer):
    dimension = MatchDimensionType.EDUCATION
    default_weight = 0.10

    async def score(self, ctx: MatchContext) -> DimensionScore:
        if not ctx.user_education:
            return DimensionScore(
                dimension=self.dimension, score=50.0, weight=self.default_weight,
                confidence=0.4, evidence=("No education data in profile",),
            )
        has_degree = any(e.get("degree") for e in ctx.user_education)
        has_cs_field = any("computer" in e.get("field", "").lower() or
                          "software" in e.get("field", "").lower()
                          for e in ctx.user_education)
        score = 70.0 if has_degree else 40.0
        if has_cs_field:
            score = min(100, score + 20)
        return DimensionScore(
            dimension=self.dimension, score=score, weight=self.default_weight,
            confidence=0.7, evidence=(f"Degree: {'Yes' if has_degree else 'No'}",),
        )

    def extract_strengths(self, ctx: MatchContext, score: DimensionScore) -> list[str]:
        return ["Education background aligns with role"] if score.score >= 70 else []

    def extract_gaps(self, ctx: MatchContext, score: DimensionScore) -> list[SkillGap]:
        if score.score < 50:
            return [SkillGap(skill_name="Formal degree", category="education",
                            severity=GapSeverity.MINOR, required_for_job=False)]
        return []


class LocationScorer(BaseDimensionScorer):
    dimension = MatchDimensionType.LOCATION
    default_weight = 0.10

    async def score(self, ctx: MatchContext) -> DimensionScore:
        score = 50.0
        evidence = []

        # Remote alignment
        user_remote = ctx.user_preferred_remote
        job_remote = ctx.job_remote_policy
        if user_remote == "remote" and job_remote == "remote":
            score = 100.0
            evidence.append("Both prefer remote")
        elif job_remote == "remote":
            score = 90.0
            evidence.append("Job is remote — location flexible")
        elif user_remote == "remote" and job_remote != "remote":
            score = 20.0
            evidence.append("User wants remote but job requires presence")

        # Location match
        user_loc = ctx.user_location
        job_loc = ctx.job_location
        if user_loc and job_loc:
            user_country = (user_loc.get("country") or "").lower()
            job_country = (job_loc.get("country") or "").lower()
            if user_country and job_country and user_country == job_country:
                score = max(score, 85.0)
                evidence.append("Same country")

        return DimensionScore(
            dimension=self.dimension, score=score, weight=self.default_weight,
            confidence=0.9, evidence=tuple(evidence),
        )

    def extract_strengths(self, ctx: MatchContext, score: DimensionScore) -> list[str]:
        return ["Location aligns with preferences"] if score.score >= 80 else []

    def extract_gaps(self, ctx: MatchContext, score: DimensionScore) -> list[SkillGap]:
        if score.score < 30:
            return [SkillGap(skill_name="Location compatibility", category="experience",
                            severity=GapSeverity.MAJOR, required_for_job=True)]
        return []


class PreferenceScorer(BaseDimensionScorer):
    dimension = MatchDimensionType.PREFERENCE
    default_weight = 0.15

    async def score(self, ctx: MatchContext) -> DimensionScore:
        score = 50.0
        evidence = []

        # Industry preference
        job_industry = ctx.job_company_industry.lower()
        if job_industry and ctx.user_preferred_industries:
            if job_industry in ctx.user_preferred_industries:
                weight = ctx.user_preferred_industries[job_industry]
                score += weight * 40
                evidence.append(f"Industry '{job_industry}' is preferred")

        # Company stage preference
        # Role preference (title match)
        job_title_lower = ctx.job_title.lower()
        for role in ctx.user_preferred_roles:
            if any(w in job_title_lower for w in role.lower().split()):
                score += 20
                evidence.append(f"Role '{role}' matches preferences")
                break

        # Dealbreaker checks
        if ctx.job_company_name.lower() in [c.lower() for c in ctx.user_excluded_companies]:
            score = 0.0
            evidence.append("Company is excluded by user")

        for db in ctx.user_dealbreakers:
            field = db.get("field", "")
            value = db.get("value", "")
            if field == "industry" and job_industry in [v.lower() for v in (value if isinstance(value, list) else [value])]:
                score = 0.0
                evidence.append(f"Industry '{value}' is a dealbreaker")

        return DimensionScore(
            dimension=self.dimension, score=min(100, max(0, score)),
            weight=self.default_weight, confidence=0.75,
            evidence=tuple(evidence),
        )

    def extract_strengths(self, ctx: MatchContext, score: DimensionScore) -> list[str]:
        if score.score >= 80:
            return ["Company and role strongly align with stated preferences"]
        return []

    def extract_gaps(self, ctx: MatchContext, score: DimensionScore) -> list[SkillGap]:
        return []


class CultureScorer(BaseDimensionScorer):
    dimension = MatchDimensionType.CULTURE
    default_weight = 0.10

    async def score(self, ctx: MatchContext) -> DimensionScore:
        # Lightweight heuristic for MVP. Full LLM analysis deferred to V1.
        score = 50.0
        evidence = []
        text = f"{ctx.job_title} {ctx.job_description}".lower()

        # Signal: engineering-driven language
        eng_signals = ["engineering", "technical", "code", "architecture", "system design"]
        if any(s in text for s in eng_signals):
            score += 15
            evidence.append("Engineering-focused job description")

        # Signal: startup vs enterprise
        stage = ctx.job_company_stage.lower()
        if stage in ("seed", "series_a", "series_b"):
            score += 10
            evidence.append("Early-stage company — impact opportunity")

        return DimensionScore(
            dimension=self.dimension, score=min(100, score), weight=self.default_weight,
            confidence=0.35,  # Culture scoring is inherently low-confidence
            evidence=tuple(evidence),
            raw_details={"confidence_note": "Culture scoring is a signal, not a fact. Use as a conversation starter."},
        )

    def extract_strengths(self, ctx: MatchContext, score: DimensionScore) -> list[str]:
        return ["Potential culture alignment detected"] if score.score >= 60 else []

    def extract_gaps(self, ctx: MatchContext, score: DimensionScore) -> list[SkillGap]:
        return []


# ── Orchestrator ──

class MatchingOrchestrator:
    """Orchestrates all dimension scorers and produces a complete MatchResult."""

    def __init__(self, scorers: list[BaseDimensionScorer] | None = None) -> None:
        self._scorers = scorers or [
            SkillScorer(), ExperienceScorer(), EducationScorer(),
            LocationScorer(), PreferenceScorer(), CultureScorer(),
        ]

    async def compute_match(self, ctx: MatchContext,
                            user_id: UUID, job_id: UUID,
                            profile_version: int = 1,
                            pref_version: int = 1) -> MatchResult:
        """Run all scorers and assemble a complete MatchResult."""

        # Check dealbreakers first — if any trigger, return early with 0 score
        dealbreaker_hit = self._check_dealbreakers(ctx)
        if dealbreaker_hit:
            result = MatchResult.create_empty(
                user_id=user_id, job_id=job_id,
                profile_version=profile_version, pref_version=pref_version,
            )
            result.overall_score = 0.0
            result.add_risk(f"Dealbreaker triggered: {dealbreaker_hit}")
            return result

        result = MatchResult.create_empty(
            user_id=user_id, job_id=job_id,
            profile_version=profile_version, pref_version=pref_version,
        )
        result.job_snapshot_title = ctx.job_title
        result.job_snapshot_company = ctx.job_company_name

        for scorer in self._scorers:
            dim_score = await scorer.score(ctx)
            result.add_dimension(dim_score)

            for strength_text in scorer.extract_strengths(ctx, dim_score):
                result.add_strength(strength_text, dimension=scorer.dimension)

            for gap in scorer.extract_gaps(ctx, dim_score):
                result.add_gap(gap)

        result.compute_overall()

        # Generate human-readable weaknesses from low dimensions
        for dim in result.dimensions:
            if dim.score < 40:
                result.add_weakness(
                    f"Low {dim.dimension.value} match ({dim.score:.0f}/100)",
                    dimension=dim.dimension,
                    evidence=dim.evidence,
                )

        # Generate risks from critical gaps
        for gap in result.skill_gaps:
            if gap.severity == GapSeverity.CRITICAL:
                result.add_risk(
                    f"Missing critical skill: {gap.skill_name}. "
                    f"{'User has similar: ' + ', '.join(gap.user_has_similar) if gap.user_has_similar else 'No similar skills found.'}"
                )

        return result

    def _check_dealbreakers(self, ctx: MatchContext) -> str | None:
        for db in ctx.user_dealbreakers:
            field = db.get("field", "")
            value = db.get("value", "")
            if field == "industry" and isinstance(value, list):
                if ctx.job_company_industry.lower() in [v.lower() for v in value]:
                    return f"Industry '{ctx.job_company_industry}' is a dealbreaker"
            if field == "company" and isinstance(value, list):
                if ctx.job_company_name.lower() in [v.lower() for v in value]:
                    return f"Company '{ctx.job_company_name}' is a dealbreaker"
        if ctx.job_company_name.lower() in [c.lower() for c in ctx.user_excluded_companies]:
            return f"Company '{ctx.job_company_name}' is excluded"
        return None


# ── Explainability Service ──

class ExplainabilityService:
    """Generates natural-language match explanations using LLM.

    CRITICAL: All explanations must be evidence-grounded. No hallucinated facts.
    """

    SYSTEM_PROMPT = """You are a career matching explainability engine.
Generate concise, evidence-grounded explanations for why a job matches (or doesn't match) a user's profile.

RULES:
1. Only reference facts explicitly present in the provided profile and job data.
2. Never fabricate skills, experiences, or achievements.
3. Be specific: "Your 8 years of Python experience matches their requirement" not "You have relevant experience."
4. For gaps, be constructive: "They require Kubernetes — you have Docker experience which is adjacent. Consider a 2-week Kubernetes course."
5. Keep each explanation to 1-2 sentences. Be direct."""

    def __init__(self, llm_port) -> None:
        self._llm = llm_port

    async def generate_explanations(self, match: MatchResult,
                                     ctx: MatchContext) -> list[MatchExplanation]:
        """Generate detailed LLM explanations for a computed match."""
        # For MVP, we rely on the heuristic strengths/weaknesses from scorers.
        # LLM enhancement is added for the top-3 strengths and top-2 weaknesses
        # only when the overall score is borderline (40-80) — maximum value from LLM.

        if match.overall_score < 20 or match.overall_score > 90:
            return []  # Obvious cases don't need LLM explanation

        try:
            prompt = self._build_explanation_prompt(match, ctx)
            response = await self._llm.chat_completion(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.3,
            )
            return self._parse_explanations(response.content)
        except Exception:
            return []  # Graceful degradation — heuristic explanations are sufficient

    def _build_explanation_prompt(self, match: MatchResult, ctx: MatchContext) -> str:
        return f"""Explain why this job matches (or doesn't) the user's profile.

USER PROFILE:
Skills: {ctx.user_skills[:10]}
Experience: {ctx.user_experiences[:5]}
Education: {ctx.user_education}

JOB:
Title: {ctx.job_title}
Company: {ctx.job_company_name}
Required Skills: {ctx.job_required_skills[:10]}
Seniority: {ctx.job_seniority}

MATCH SCORES:
Overall: {match.overall_score}/100
Skills: {match.skill_score}/100
Experience: {match.experience_score}/100

Generate 3 specific, evidence-based reasons for the match quality."""

    def _parse_explanations(self, raw: str) -> list[MatchExplanation]:
        explanations = []
        for line in raw.strip().split("\n"):
            line = line.strip()
            if line and len(line) > 10:
                explanations.append(MatchExplanation(
                    category="strength" if "strong" in line.lower() or "match" in line.lower() else "neutral",
                    text=line,
                ))
        return explanations[:5]
```

### `src/pathfinder/jobs/domain/matching/exceptions.py`

```python
"""Matching domain exceptions."""
from pathfinder.shared.domain.exceptions import NotFoundError, ValidationError, DomainError


class MatchNotFoundError(NotFoundError):
    def __init__(self, user_id: str = "", job_id: str = "") -> None:
        super().__init__(f"Match not found for user={user_id}, job={job_id}")

class InsufficientProfileError(ValidationError):
    def __init__(self) -> None:
        super().__init__("Cannot compute match: user profile has insufficient data. Add skills and experience.")

class MatchingEngineError(DomainError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Matching engine error: {detail}")
```

### `src/pathfinder/jobs/domain/matching/events.py`

```python
"""Matching domain events."""
from dataclasses import dataclass
from uuid import UUID
from pathfinder.shared.domain.base_domain_event import BaseDomainEvent

@dataclass
class MatchComputed(BaseDomainEvent):
    user_id: UUID
    job_id: UUID
    overall_score: float

@dataclass
class HighScoreMatchFound(BaseDomainEvent):
    user_id: UUID
    job_id: UUID
    overall_score: float  # >= 85
```

---

## Day 3–4: Infrastructure — Persistence

### Files to Create

```
src/pathfinder/jobs/infrastructure/persistence/
├── match_models.py           # MatchResultModel, MatchDimensionModel, etc.
└── match_repository.py       # SqlMatchRepository

src/pathfinder/jobs/infrastructure/
└── matching/
    ├── match_context_builder.py  # Builds MatchContext from profile + job
    ├── bulk_matcher.py           # Bulk matching with Celery
    └── recommendation_engine.py  # Job + learning recommendations

tests/integration/persistence/
└── test_match_repository.py
```

### `src/pathfinder/jobs/infrastructure/persistence/match_models.py`

```python
"""SQLAlchemy ORM models for matching domain."""
from uuid import UUID
from sqlalchemy import String, Float, Integer, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin
from pathfinder.jobs.domain.matching.entities import MatchResult
from pathfinder.jobs.domain.matching.value_objects import (
    DimensionScore, MatchExplanation, SkillGap, MatchRecommendation,
    MatchDimensionType, GapSeverity,
)


class MatchResultModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "match_results"

    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    dimensions: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    strengths: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    weaknesses: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    skill_gaps: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    risks: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    profile_version_used: Mapped[int] = mapped_column(Integer, default=1)
    preferences_version_used: Mapped[int] = mapped_column(Integer, default=1)
    job_snapshot_title: Mapped[str] = mapped_column(String(255), default="")
    job_snapshot_company: Mapped[str] = mapped_column(String(255), default="")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    feedback: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recommendations: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")

    __table_args__ = (
        # One match per user-job pair
        {"postgresql_partition_by": "HASH (user_id)"},
    )

    def to_domain(self) -> MatchResult:
        return MatchResult(
            id=self.id, user_id=self.user_id, job_id=self.job_id,
            overall_score=self.overall_score,
            dimensions=[DimensionScore(**d) for d in (self.dimensions or [])],
            strengths=[MatchExplanation(**s) for s in (self.strengths or [])],
            weaknesses=[MatchExplanation(**w) for w in (self.weaknesses or [])],
            skill_gaps=[SkillGap(**g) for g in (self.skill_gaps or [])],
            risks=[MatchExplanation(**r) for r in (self.risks or [])],
            profile_version_used=self.profile_version_used,
            preferences_version_used=self.preferences_version_used,
            job_snapshot_title=self.job_snapshot_title,
            job_snapshot_company=self.job_snapshot_company,
            computed_at=self.computed_at,
            is_stale=self.is_stale,
            feedback=self.feedback,
            recommendations=[MatchRecommendation(**r) for r in (self.recommendations or [])],
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, m: MatchResult) -> "MatchResultModel":
        return cls(
            id=m.id, user_id=m.user_id, job_id=m.job_id,
            overall_score=m.overall_score,
            dimensions=[{**d.__dict__} for d in m.dimensions],
            strengths=[{**s.__dict__} for s in m.strengths],
            weaknesses=[{**w.__dict__} for w in m.weaknesses],
            skill_gaps=[{**g.__dict__} for g in m.skill_gaps],
            risks=[{**r.__dict__} for r in m.risks],
            profile_version_used=m.profile_version_used,
            preferences_version_used=m.preferences_version_used,
            job_snapshot_title=m.job_snapshot_title,
            job_snapshot_company=m.job_snapshot_company,
            computed_at=m.computed_at,
            is_stale=m.is_stale,
            feedback=m.feedback,
            recommendations=[{**r.__dict__} for r in m.recommendations],
            created_at=m.created_at, updated_at=m.updated_at,
        )
```

### `src/pathfinder/jobs/infrastructure/persistence/match_repository.py`

```python
"""SQLAlchemy MatchRepository implementation."""
from uuid import UUID
from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.jobs.domain.matching.entities import MatchResult
from pathfinder.jobs.domain.matching.repositories import MatchRepository
from pathfinder.jobs.domain.matching.value_objects import MatchSummary
from pathfinder.jobs.infrastructure.persistence.match_models import MatchResultModel


class SqlMatchRepository(MatchRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> MatchResult | None:
        model = await self._session.get(MatchResultModel, id)
        return model.to_domain() if model else None

    async def get_by_user_and_job(self, user_id: UUID, job_id: UUID) -> MatchResult | None:
        stmt = select(MatchResultModel).where(
            MatchResultModel.user_id == user_id,
            MatchResultModel.job_id == job_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def save(self, entity: MatchResult) -> None:
        model = MatchResultModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity: MatchResult) -> None:
        model = await self._session.get(MatchResultModel, entity.id)
        if model:
            await self._session.delete(model)

    async def list_by_user(self, user_id: UUID, *, min_score: float = 0.0,
                           cursor: str | None = None,
                           limit: int = 20) -> tuple[list[MatchResult], str | None]:
        stmt = select(MatchResultModel).where(
            MatchResultModel.user_id == user_id,
            MatchResultModel.overall_score >= min_score,
        ).order_by(MatchResultModel.overall_score.desc()).limit(limit + 1)

        result = await self._session.execute(stmt)
        models = result.scalars().all()
        has_more = len(models) > limit
        if has_more:
            models = models[:limit]
        next_cursor = str(models[-1].id) if has_more else None
        return [m.to_domain() for m in models], next_cursor

    async def list_summaries_by_user(self, user_id: UUID, *, min_score: float = 0.0,
                                     cursor: str | None = None, limit: int = 50,
                                     ) -> tuple[list[MatchSummary], str | None]:
        stmt = select(MatchResultModel).where(
            MatchResultModel.user_id == user_id,
            MatchResultModel.overall_score >= min_score,
        ).order_by(MatchResultModel.overall_score.desc()).limit(limit + 1)

        result = await self._session.execute(stmt)
        models = result.scalars().all()
        has_more = len(models) > limit
        if has_more:
            models = models[:limit]

        summaries = []
        for m in models:
            top_strength = m.strengths[0]["text"] if m.strengths else ""
            top_gap = m.skill_gaps[0]["skill_name"] if m.skill_gaps else ""
            dims = {d["dimension"]: d["score"] for d in (m.dimensions or [])}
            summaries.append(MatchSummary(
                job_id=str(m.job_id),
                overall_score=m.overall_score,
                top_strength=top_strength,
                top_gap=top_gap,
                skill_match_score=dims.get("skills", 0.0),
                computed_at=m.computed_at.isoformat() if m.computed_at else "",
            ))

        next_cursor = str(models[-1].id) if has_more else None
        return summaries, next_cursor

    async def get_high_matches(self, user_id: UUID, threshold: float = 85.0,
                               limit: int = 10) -> list[MatchResult]:
        stmt = select(MatchResultModel).where(
            MatchResultModel.user_id == user_id,
            MatchResultModel.overall_score >= threshold,
        ).order_by(MatchResultModel.overall_score.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def delete_by_user_and_job(self, user_id: UUID, job_id: UUID) -> bool:
        stmt = delete(MatchResultModel).where(
            MatchResultModel.user_id == user_id,
            MatchResultModel.job_id == job_id,
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def mark_stale_for_user(self, user_id: UUID) -> int:
        stmt = (
            update(MatchResultModel)
            .where(MatchResultModel.user_id == user_id)
            .values(is_stale=True)
        )
        result = await self._session.execute(stmt)
        return result.rowcount or 0
```

### `src/pathfinder/jobs/infrastructure/matching/match_context_builder.py`

```python
"""Builds MatchContext from profile, preferences, and job data."""
from uuid import UUID
from pathfinder.jobs.domain.matching.services import MatchContext
from pathfinder.profile.domain.repositories import ProfileRepository
from pathfinder.jobs.domain.repositories import JobRepository
from pathfinder.identity.domain.repositories import UserRepository


class MatchContextBuilder:
    def __init__(self, profile_repo: ProfileRepository,
                 job_repo: JobRepository) -> None:
        self._profiles = profile_repo
        self._jobs = job_repo

    async def build(self, user_id: UUID, job_id: UUID) -> MatchContext | None:
        profile = await self._profiles.get_by_user_id(user_id)
        job = await self._jobs.get_by_id(job_id)
        if not profile or not job:
            return None

        return MatchContext(
            user_id=user_id, job_id=job_id,
            user_skills=[{
                "name": s.name, "proficiency": s.proficiency.value,
                "years": s.years, "category": s.category.value,
            } for s in profile.skills],
            user_experiences=[{
                "company": e.company, "title": e.title,
                "years": ((e.end_date or date.today()) - e.start_date).days / 365.25 if e.start_date else 0,
                "description": e.description,
                "tech_stack": list(e.tech_stack),
            } for e in profile.work_experiences],
            user_education=[{
                "degree": e.degree, "field": e.field, "institution": e.institution,
            } for e in profile.education],
            user_projects=[{
                "name": p.name, "description": p.description,
                "technologies": list(p.technologies),
            } for p in profile.projects],
            user_certifications=[dict(c) for c in profile.certifications],
            user_languages=[dict(l) for l in profile.languages],
            user_location=profile.location,
            user_summary=profile.summary,
            job_title=job.title,
            job_description=job.description_clean or job.description_raw,
            job_required_skills=job.required_skills if job.required_skills else [
                {"name": s, "importance": "required"}
                for s in (job.tech_stack or [])
            ],
            job_nice_to_have=job.nice_to_have_skills if job.nice_to_have_skills else [],
            job_tech_stack=job.tech_stack or [],
            job_seniority=job.seniority.value,
            job_remote_policy=job.remote_policy.value,
            job_location=job.location.__dict__ if job.location else None,
            job_salary_range={
                "min": job.salary_range.min_amount, "max": job.salary_range.max_amount,
            } if job.salary_range else None,
            job_company_name=job.company_name,
            job_company_industry="",  # Populated if company loaded
            job_company_stage="",
        )
```

---

## Day 5–6: Application Layer + APIs

### Files to Create

```
src/pathfinder/jobs/application/
├── matching_commands.py    # ComputeMatch, BulkMatch, RefreshMatch
├── matching_queries.py     # GetMatch, ListMatches, GetRecommendations
└── matching_handlers.py    # MatchingCommandHandler

src/pathfinder/jobs/presentation/
├── matching_router.py      # /v1/match/* endpoints
└── matching_schemas.py     # Pydantic schemas

src/pathfinder/agent/infrastructure/celery_tasks/
└── matching.py             # bulk_match_for_user task
```

### `src/pathfinder/jobs/application/matching_handlers.py`

```python
"""Matching command/query handler."""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.domain.result import Result
from pathfinder.jobs.domain.matching.entities import MatchResult
from pathfinder.jobs.domain.matching.services import MatchingOrchestrator, ExplainabilityService
from pathfinder.jobs.domain.matching.repositories import MatchRepository
from pathfinder.jobs.domain.matching.exceptions import (
    MatchNotFoundError, InsufficientProfileError,
)
from pathfinder.jobs.infrastructure.matching.match_context_builder import MatchContextBuilder


class MatchingCommandHandler:
    def __init__(self, match_repo: MatchRepository,
                 context_builder: MatchContextBuilder,
                 orchestrator: MatchingOrchestrator,
                 explainer: ExplainabilityService | None = None,
                 session: AsyncSession = None) -> None:
        self._matches = match_repo
        self._ctx_builder = context_builder
        self._orchestrator = orchestrator
        self._explainer = explainer
        self._session = session

    async def compute(self, user_id: UUID, job_id: UUID,
                      force_refresh: bool = False) -> Result[MatchResult]:
        if not force_refresh:
            existing = await self._matches.get_by_user_and_job(user_id, job_id)
            if existing and not existing.is_stale:
                return Result.success(existing)

        ctx = await self._ctx_builder.build(user_id, job_id)
        if ctx is None:
            return Result.failure(MatchNotFoundError(str(user_id), str(job_id)))
        if not ctx.user_skills and not ctx.user_experiences:
            return Result.failure(InsufficientProfileError())

        match = await self._orchestrator.compute_match(
            ctx, user_id=user_id, job_id=job_id,
        )
        await self._matches.save(match)

        # Generate LLM explanations for borderline cases
        if self._explainer:
            explanations = await self._explainer.generate_explanations(match, ctx)
            for exp in explanations:
                if exp.category == "strength":
                    match.strengths.append(exp)
                else:
                    match.weaknesses.append(exp)

        return Result.success(match)

    async def bulk_compute(self, user_id: UUID, job_ids: list[UUID],
                           limit: int = 50) -> Result[list[MatchResult]]:
        results = []
        for job_id in job_ids[:limit]:
            r = await self.compute(user_id, job_id)
            if r.is_success:
                results.append(r.value)
        results.sort(key=lambda m: m.overall_score, reverse=True)
        return Result.success(results)

    async def get_recommendations(self, user_id: UUID,
                                   limit: int = 10) -> Result[list[MatchResult]]:
        return Result.success(
            await self._matches.get_high_matches(user_id, threshold=75.0, limit=limit)
        )

    async def record_feedback(self, user_id: UUID, job_id: UUID,
                              feedback: str) -> Result[MatchResult]:
        match = await self._matches.get_by_user_and_job(user_id, job_id)
        if not match:
            return Result.failure(MatchNotFoundError(str(user_id), str(job_id)))
        match.record_feedback(feedback)
        await self._matches.save(match)
        return Result.success(match)
```

### `src/pathfinder/jobs/presentation/matching_router.py`

```python
"""Matching API routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User
from pathfinder.jobs.domain.matching.repositories import MatchRepository
from pathfinder.jobs.domain.matching.services import MatchingOrchestrator
from pathfinder.jobs.domain.matching.exceptions import MatchNotFoundError, InsufficientProfileError
from pathfinder.jobs.infrastructure.persistence.match_repository import SqlMatchRepository
from pathfinder.jobs.infrastructure.matching.match_context_builder import MatchContextBuilder
from pathfinder.jobs.application.matching_handlers import MatchingCommandHandler
from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository

router = APIRouter(prefix="/v1/match", tags=["Matching"])


async def get_match_repo(session: AsyncSession = Depends(get_session)) -> MatchRepository:
    return SqlMatchRepository(session)


async def get_match_handler(
    session: AsyncSession = Depends(get_session),
) -> MatchingCommandHandler:
    profile_repo = SqlProfileRepository(session)
    job_repo = SqlJobRepository(session)
    match_repo = SqlMatchRepository(session)
    ctx_builder = MatchContextBuilder(profile_repo, job_repo)
    orchestrator = MatchingOrchestrator()
    return MatchingCommandHandler(match_repo, ctx_builder, orchestrator, session=session)


@router.post("/compute")
async def compute_match(
    job_id: UUID = Query(..., description="Job ID to match against"),
    force_refresh: bool = Query(False, description="Force recomputation"),
    current_user: User = Depends(get_current_user),
    handler: MatchingCommandHandler = Depends(get_match_handler),
):
    result = await handler.compute(current_user.id, job_id, force_refresh=force_refresh)
    if result.is_failure:
        raise result.error
    return {"data": _match_to_response(result.value)}


@router.post("/bulk")
async def bulk_match(
    job_ids: list[UUID] = Query(..., description="Job IDs (max 50)"),
    current_user: User = Depends(get_current_user),
    handler: MatchingCommandHandler = Depends(get_match_handler),
):
    result = await handler.bulk_compute(current_user.id, job_ids[:50])
    if result.is_failure:
        raise result.error
    return {
        "data": [_match_to_response(m) for m in result.value],
        "meta": {"count": len(result.value)},
    }


@router.get("/{job_id}")
async def get_match(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    handler: MatchingCommandHandler = Depends(get_match_handler),
):
    result = await handler.compute(current_user.id, job_id)
    if result.is_failure:
        raise result.error
    return {"data": _match_to_response(result.value)}


@router.get("")
async def list_matches(
    min_score: float = Query(0.0, ge=0, le=100),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    match_repo: MatchRepository = Depends(get_match_repo),
):
    matches, cursor = await match_repo.list_by_user(
        current_user.id, min_score=min_score, limit=limit,
    )
    return {
        "data": [_match_summary_to_response(m) for m in matches],
        "meta": {"cursor_next": cursor, "limit": limit},
    }


@router.post("/{job_id}/feedback")
async def record_feedback(
    job_id: UUID,
    feedback: str = Query(..., pattern="^(thumbs_up|thumbs_down|dismiss)$"),
    current_user: User = Depends(get_current_user),
    handler: MatchingCommandHandler = Depends(get_match_handler),
):
    result = await handler.record_feedback(current_user.id, job_id, feedback)
    if result.is_failure:
        raise result.error
    return {"data": {"status": "feedback_recorded"}}


@router.get("/recommendations/personalized")
async def personalized_recommendations(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    handler: MatchingCommandHandler = Depends(get_match_handler),
):
    result = await handler.get_recommendations(current_user.id, limit=limit)
    if result.is_failure:
        raise result.error
    return {
        "data": [_match_to_response(m) for m in result.value],
        "meta": {"count": len(result.value)},
    }


def _match_to_response(m) -> dict:
    return {
        "match_id": str(m.id),
        "job_id": str(m.job_id),
        "overall_score": m.overall_score,
        "dimensions": {
            d.dimension.value: {
                "score": d.score, "weight": d.weight,
                "confidence": d.confidence,
            } for d in m.dimensions
        },
        "strengths": [{"text": s.text, "importance": s.importance} for s in m.strengths[:5]],
        "weaknesses": [{"text": w.text} for w in m.weaknesses[:3]],
        "skill_gaps": [{
            "skill": g.skill_name, "severity": g.severity.value,
            "required": g.required_for_job,
            "user_has_similar": list(g.user_has_similar),
        } for g in m.skill_gaps[:10]],
        "risks": [{"text": r.text} for r in m.risks],
        "recommendations": [{
            "type": r.recommendation_type, "title": r.title,
            "description": r.description, "priority": r.priority,
        } for r in m.recommendations],
        "feedback": m.feedback,
        "is_stale": m.is_stale,
        "computed_at": m.computed_at.isoformat() if m.computed_at else None,
        "job_snapshot": {
            "title": m.job_snapshot_title,
            "company": m.job_snapshot_company,
        },
    }


def _match_summary_to_response(m) -> dict:
    return {
        "job_id": m.job_id if hasattr(m, 'job_id') else str(getattr(m, 'job_id', '')),
        "overall_score": m.overall_score,
        "top_strength": getattr(m, 'top_strength', ''),
        "top_gap": getattr(m, 'top_gap', ''),
    }
```

### Celery Task — `src/pathfinder/agent/infrastructure/celery_tasks/matching.py`

```python
"""Celery task for bulk background matching (e.g., nightly sweep for all users)."""
import asyncio
from celery.utils.log import get_task_logger
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository
from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
from pathfinder.jobs.infrastructure.persistence.match_repository import SqlMatchRepository
from pathfinder.jobs.infrastructure.matching.match_context_builder import MatchContextBuilder
from pathfinder.jobs.domain.matching.services import MatchingOrchestrator

logger = get_task_logger(__name__)


async def _bulk_match_for_user_async(user_id: str, job_limit: int = 100):
    maker = get_sessionmaker()
    async with maker() as session:
        profile_repo = SqlProfileRepository(session)
        job_repo = SqlJobRepository(session)
        match_repo = SqlMatchRepository(session)
        ctx_builder = MatchContextBuilder(profile_repo, job_repo)
        orchestrator = MatchingOrchestrator()

        # Mark old matches as stale
        await match_repo.mark_stale_for_user(user_id)

        # Get active jobs
        jobs = await job_repo.list_active(limit=job_limit)
        new_matches = 0

        for job in jobs:
            ctx = await ctx_builder.build(user_id, job.id)
            if ctx is None:
                continue
            match = await orchestrator.compute_match(ctx, user_id=user_id, job_id=job.id)
            await match_repo.save(match)
            new_matches += 1

        await session.commit()
        logger.info(f"Bulk match for user {user_id}: {new_matches} matches computed")
        return {"user_id": user_id, "matches_computed": new_matches}
```

---

## Day 7: Registration, Migration, Redis Caching

### `src/pathfinder/shared/infrastructure/main.py` — Update

```python
from pathfinder.jobs.presentation.matching_router import router as matching_router
app.include_router(matching_router)
```

### Migration — `alembic/versions/005_match_results.py`

```python
"""005_match_results table."""
revision = "005"
down_revision = "004"

def upgrade():
    op.create_table("match_results",
        sa.Column("id", PGUUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", PGUUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", PGUUID(), sa.ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("overall_score", sa.Float(), default=0.0),
        sa.Column("dimensions", JSONB(), default=list, server_default="[]"),
        sa.Column("strengths", JSONB(), default=list, server_default="[]"),
        sa.Column("weaknesses", JSONB(), default=list, server_default="[]"),
        sa.Column("skill_gaps", JSONB(), default=list, server_default="[]"),
        sa.Column("risks", JSONB(), default=list, server_default="[]"),
        sa.Column("profile_version_used", sa.Integer(), default=1),
        sa.Column("preferences_version_used", sa.Integer(), default=1),
        sa.Column("job_snapshot_title", sa.String(255), default=""),
        sa.Column("job_snapshot_company", sa.String(255), default=""),
        sa.Column("computed_at", sa.DateTime(timezone=True)),
        sa.Column("is_stale", sa.Boolean(), default=False),
        sa.Column("feedback", sa.String(20), nullable=True),
        sa.Column("recommendations", JSONB(), default=list, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_match_user_job", "match_results", ["user_id", "job_id"], unique=True)
    op.create_index("idx_match_user_score", "match_results", ["user_id", "overall_score"])

def downgrade():
    op.drop_table("match_results")
```

### Redis Caching — in `matching_handlers.py`

```python
# Cache match result in Redis for 1 hour
# Key: match:{user_id}:{job_id}
# Value: JSON serialized match summary
async def _cache_match(self, user_id: UUID, job_id: UUID, match: MatchResult) -> None:
    redis = await get_redis()
    key = f"match:{user_id}:{job_id}"
    await redis.setex(key, 3600, json.dumps(_match_to_response(match)))

async def _get_cached_match(self, user_id: UUID, job_id: UUID) -> dict | None:
    redis = await get_redis()
    key = f"match:{user_id}:{job_id}"
    data = await redis.get(key)
    return json.loads(data) if data else None
```

---

## Day 8–9: Tests

### Test Files

```
tests/unit/jobs/matching/
├── test_dimension_scorers.py    # 12 tests
├── test_match_entity.py         # 8 tests
├── test_match_context_builder.py # 3 tests
└── test_skill_gap.py            # 4 tests

tests/integration/api/
└── test_matching_api.py         # 8 tests

tests/integration/persistence/
└── test_match_repository.py     # 5 tests
```

### `tests/unit/jobs/matching/test_dimension_scorers.py`

```python
import pytest
from pathfinder.jobs.domain.matching.services import (
    SkillScorer, ExperienceScorer, EducationScorer,
    LocationScorer, PreferenceScorer, CultureScorer,
    MatchContext, MatchingOrchestrator,
)
from pathfinder.jobs.domain.matching.value_objects import MatchDimensionType

def _make_ctx(**overrides) -> MatchContext:
    defaults = {
        "user_id": None, "job_id": None,
        "user_skills": [{"name": "Python", "proficiency": "expert", "years": 8, "category": "programming_language"}],
        "user_experiences": [{"company": "Acme", "title": "Senior SWE", "years": 5}],
        "user_education": [{"degree": "BS", "field": "Computer Science", "institution": "MIT"}],
        "user_projects": [], "user_certifications": [], "user_languages": [],
        "user_location": {"country": "US"},
        "job_title": "Senior Software Engineer",
        "job_required_skills": [{"name": "Python", "importance": "critical"}],
        "job_nice_to_have": [{"name": "Docker", "importance": "nice"}],
        "job_tech_stack": ["Python", "AWS"],
        "job_seniority": "senior",
        "job_remote_policy": "remote",
        "job_company_name": "TechCorp",
    }
    return MatchContext(**{**defaults, **overrides})


class TestSkillScorer:
    async def test_perfect_skill_match(self):
        scorer = SkillScorer()
        ctx = _make_ctx()
        score = await scorer.score(ctx)
        assert score.score >= 80

    async def test_no_skill_overlap(self):
        scorer = SkillScorer()
        ctx = _make_ctx(
            job_required_skills=[{"name": "Rust", "importance": "critical"}],
            user_skills=[{"name": "Python", "proficiency": "expert"}],
        )
        score = await scorer.score(ctx)
        assert score.score < 40

    async def test_extracts_missing_skills_as_gaps(self):
        scorer = SkillScorer()
        ctx = _make_ctx(job_required_skills=[{"name": "Kubernetes", "importance": "critical"}])
        score = await scorer.score(ctx)
        gaps = scorer.extract_gaps(ctx, score)
        assert any(g.skill_name == "Kubernetes" for g in gaps)


class TestExperienceScorer:
    async def test_seniority_alignment(self):
        scorer = ExperienceScorer()
        ctx = _make_ctx()
        score = await scorer.score(ctx)
        assert score.score >= 60

    async def test_intern_for_senior_role_scores_low(self):
        scorer = ExperienceScorer()
        ctx = _make_ctx(
            user_experiences=[{"company": "A", "title": "Intern", "years": 0.5}],
            job_seniority="senior",
        )
        score = await scorer.score(ctx)
        assert score.score < 40


class TestMatchingOrchestrator:
    async def test_full_match_computes_all_dimensions(self):
        orch = MatchingOrchestrator()
        ctx = _make_ctx()
        result = await orch.compute_match(ctx, user_id=None, job_id=None)
        assert len(result.dimensions) == 6
        assert 0 <= result.overall_score <= 100

    async def test_dealbreaker_triggers_zero_score(self):
        orch = MatchingOrchestrator()
        ctx = _make_ctx(
            user_excluded_companies=["TechCorp"],
            job_company_name="TechCorp",
        )
        result = await orch.compute_match(ctx, user_id=None, job_id=None)
        assert result.overall_score == 0.0
        assert len(result.risks) >= 1

    async def test_high_skill_match_produces_strengths(self):
        orch = MatchingOrchestrator()
        ctx = _make_ctx()
        result = await orch.compute_match(ctx, user_id=None, job_id=None)
        assert len(result.strengths) > 0
```

### `tests/unit/jobs/matching/test_match_entity.py`

```python
from pathfinder.jobs.domain.matching.entities import MatchResult
from pathfinder.jobs.domain.matching.value_objects import (
    DimensionScore, MatchDimensionType, SkillGap, GapSeverity,
)

def test_empty_match_has_zero_score():
    m = MatchResult(user_id=None, job_id=None)
    assert m.overall_score == 0.0

def test_compute_overall_weighted_average():
    m = MatchResult(user_id=None, job_id=None)
    m.add_dimension(DimensionScore(dimension=MatchDimensionType.SKILLS, score=90, weight=0.4))
    m.add_dimension(DimensionScore(dimension=MatchDimensionType.EXPERIENCE, score=60, weight=0.3))
    m.add_dimension(DimensionScore(dimension=MatchDimensionType.LOCATION, score=80, weight=0.3))
    score = m.compute_overall()
    expected = (36 + 18 + 24) / 1.0  # = 78.0
    assert abs(score - expected) < 1.0

def test_is_high_match():
    m = MatchResult(user_id=None, job_id=None, overall_score=90.0)
    assert m.is_high_match is True

def test_has_dealbreaker_gap():
    m = MatchResult(user_id=None, job_id=None)
    m.add_gap(SkillGap(skill_name="K8s", category="technology",
                       severity=GapSeverity.CRITICAL, required_for_job=True))
    assert m.has_dealbreaker_gap is True

def test_record_feedback():
    m = MatchResult(user_id=None, job_id=None)
    m.record_feedback("thumbs_up")
    assert m.feedback == "thumbs_up"
```

---

## Day 10: Gate Review

### Sprint 5 Gate Checklist

```
☐ 6 dimension scorers implemented (Skills, Experience, Education, Location, Preference, Culture)
☐ MatchingOrchestrator compiles all 6 into a MatchResult
☐ ExplainabilityService generates LLM explanations for borderline matches
☐ MatchContextBuilder assembles all data from profile + job
☐ SqlMatchRepository: CRUD, list_by_user, get_high_matches, mark_stale
☐ POST /v1/match/compute?job_id=X → 200 with full match result
☐ POST /v1/match/bulk?job_ids=X,Y,Z → 200 with ranked list
☐ GET /v1/match/{job_id} → 200 (from cache or computed)
☐ GET /v1/match?min_score=70 → 200 with paginated matches
☐ POST /v1/match/{job_id}/feedback → 200
☐ GET /v1/match/recommendations/personalized → 200
☐ Dealbreaker check produces 0-score match
☐ Insufficient profile → 422
☐ Redis caching: second request hits cache
☐ Migration 005 creates match_results table
☐ All unit tests pass (27+)
☐ All integration tests pass (13+)
☐ ruff check → 0. mypy --strict → 0
```

### Sprint 5 Metrics

| Metric | Count |
|--------|-------|
| Dimension scorers | 6 |
| Domain entities | 1 (MatchResult) |
| Value objects | 7 (DimensionScore, MatchExplanation, SkillGap, MatchRecommendation, MatchSummary, enums) |
| Repository interface methods | 7 |
| API endpoints | 6 |
| Celery tasks | 1 |
| Migration | 1 |
| Unit tests | 27 |
| Integration tests | 13 |

---

> *"Sprint 5: Matching is where Pathfinder becomes intelligent. A 90% match with clear explanations builds trust. A 30% match with honest gap analysis builds even more."*

**End of Sprint 5**
