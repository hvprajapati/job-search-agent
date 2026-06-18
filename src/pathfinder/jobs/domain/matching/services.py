"""Matching domain services — dimension scorers and orchestrator."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID
import asyncio
from pathfinder.jobs.domain.matching.value_objects import (
    DimensionScore, MatchDimensionType, SkillGap, GapSeverity,
)
from pathfinder.jobs.domain.matching.entities import MatchResult


@dataclass
class MatchContext:
    user_id: UUID | None = None
    job_id: UUID | None = None
    user_skills: list[dict] = field(default_factory=list)
    user_experiences: list[dict] = field(default_factory=list)
    user_education: list[dict] = field(default_factory=list)
    user_location: dict | None = None
    job_title: str = ""
    job_description: str = ""
    job_required_skills: list[dict] = field(default_factory=list)
    job_nice_to_have: list[dict] = field(default_factory=list)
    job_tech_stack: list[str] = field(default_factory=list)
    job_seniority: str = ""
    job_remote_policy: str = ""
    job_company_name: str = ""
    job_company_industry: str = ""
    job_company_stage: str = ""
    user_preferred_roles: list[str] = field(default_factory=list)
    user_preferred_industries: dict = field(default_factory=dict)
    user_preferred_remote: str = ""
    user_dealbreakers: list[dict] = field(default_factory=list)
    user_excluded_companies: list[str] = field(default_factory=list)


class BaseScorer(ABC):
    @property
    @abstractmethod
    def dimension(self) -> MatchDimensionType: ...

    @property
    @abstractmethod
    def default_weight(self) -> float: ...

    @abstractmethod
    async def score(self, ctx: MatchContext) -> DimensionScore: ...

    def extract_strengths(self, ctx: MatchContext, score: DimensionScore) -> list[str]:
        return []

    def extract_gaps(self, ctx: MatchContext, score: DimensionScore) -> list[SkillGap]:
        return []


class SkillScorer(BaseScorer):
    dimension = MatchDimensionType.SKILLS
    default_weight = 0.30

    async def score(self, ctx: MatchContext) -> DimensionScore:
        if not ctx.user_skills:
            return DimensionScore(dimension=self.dimension, score=40.0, weight=self.default_weight,
                                  confidence=0.3, evidence=("No user skills data",))

        user_names = {s["name"].lower() for s in ctx.user_skills}
        required_names = {s.get("name", s).lower() for s in (ctx.job_required_skills or [])}

        if not required_names:
            return DimensionScore(dimension=self.dimension, score=60.0, weight=self.default_weight,
                                  confidence=0.3)

        matched = user_names & required_names
        base = (len(matched) / max(len(required_names), 1)) * 70

        prof_bonus = 0
        for skill in ctx.user_skills:
            if skill["name"].lower() in matched:
                p = skill.get("proficiency", "intermediate")
                prof_bonus += {"expert": 4, "advanced": 2, "intermediate": 1}.get(p, 0)
        prof_bonus = min(20, prof_bonus)

        return DimensionScore(
            dimension=self.dimension, score=min(100, round(base + prof_bonus, 1)),
            weight=self.default_weight, confidence=0.85,
            evidence=(f"Matched {len(matched)}/{len(required_names)} required skills",),
            raw_details={"matched": list(matched), "missing": list(required_names - user_names)},
        )

    def extract_gaps(self, ctx: MatchContext, score: DimensionScore) -> list[SkillGap]:
        missing = score.raw_details.get("missing", [])
        return [
            SkillGap(skill_name=name, category="technology",
                     severity=GapSeverity.CRITICAL, required_for_job=True)
            for name in missing[:5]
        ]


class ExperienceScorer(BaseScorer):
    dimension = MatchDimensionType.EXPERIENCE
    default_weight = 0.25

    async def score(self, ctx: MatchContext) -> DimensionScore:
        total_years = sum(exp.get("years", 0) for exp in ctx.user_experiences)
        expected = {"intern": (0, 1), "junior": (1, 3), "mid": (3, 6),
                    "senior": (6, 10), "staff": (8, 15)}.get(ctx.job_seniority, (3, 8))
        years_score = min(100, (total_years / max(expected[0], 1)) * 70)
        return DimensionScore(
            dimension=self.dimension, score=round(years_score, 1),
            weight=self.default_weight, confidence=0.80,
            raw_details={"total_years": total_years},
        )


class EducationScorer(BaseScorer):
    dimension = MatchDimensionType.EDUCATION
    default_weight = 0.10

    async def score(self, ctx: MatchContext) -> DimensionScore:
        if not ctx.user_education:
            return DimensionScore(dimension=self.dimension, score=50.0, weight=self.default_weight, confidence=0.4)
        return DimensionScore(dimension=self.dimension, score=70.0, weight=self.default_weight, confidence=0.7)


class LocationScorer(BaseScorer):
    dimension = MatchDimensionType.LOCATION
    default_weight = 0.10

    async def score(self, ctx: MatchContext) -> DimensionScore:
        if ctx.user_preferred_remote == "remote" and ctx.job_remote_policy == "remote":
            return DimensionScore(dimension=self.dimension, score=100.0, weight=self.default_weight)
        if ctx.job_remote_policy == "remote":
            return DimensionScore(dimension=self.dimension, score=85.0, weight=self.default_weight)
        return DimensionScore(dimension=self.dimension, score=50.0, weight=self.default_weight)


class PreferenceScorer(BaseScorer):
    dimension = MatchDimensionType.PREFERENCE
    default_weight = 0.15

    async def score(self, ctx: MatchContext) -> DimensionScore:
        score = 50.0
        if ctx.job_company_industry.lower() in ctx.user_preferred_industries:
            score += 30
        return DimensionScore(dimension=self.dimension, score=min(100, score),
                              weight=self.default_weight, confidence=0.75)


class CultureScorer(BaseScorer):
    dimension = MatchDimensionType.CULTURE
    default_weight = 0.10

    async def score(self, ctx: MatchContext) -> DimensionScore:
        return DimensionScore(dimension=self.dimension, score=50.0, weight=self.default_weight,
                              confidence=0.35)


class MatchingOrchestrator:
    def __init__(self, scorers: list[BaseScorer] | None = None) -> None:
        self._scorers = scorers or [
            SkillScorer(), ExperienceScorer(), EducationScorer(),
            LocationScorer(), PreferenceScorer(), CultureScorer(),
        ]

    async def compute_match(self, ctx: MatchContext, user_id: UUID,
                            job_id: UUID) -> MatchResult:
        # Dealbreaker check
        if ctx.job_company_name.lower() in [c.lower() for c in ctx.user_excluded_companies]:
            result = MatchResult.create_empty(user_id=user_id, job_id=job_id)
            result.overall_score = 0.0
            result.add_risk(f"Company '{ctx.job_company_name}' is excluded by user")
            return result

        result = MatchResult.create_empty(user_id=user_id, job_id=job_id)
        result.job_snapshot_title = ctx.job_title
        result.job_snapshot_company = ctx.job_company_name

        # Run scorers concurrently
        async def _run(scorer: BaseScorer):
            try:
                return await scorer.score(ctx), scorer
            except Exception:
                return DimensionScore(
                    dimension=scorer.dimension, score=50.0,
                    weight=scorer.default_weight, confidence=0.0,
                ), scorer

        tasks = [_run(s) for s in self._scorers]
        results = await asyncio.gather(*tasks)

        for dim_score, scorer in results:
            result.add_dimension(dim_score)
            for gap in scorer.extract_gaps(ctx, dim_score):
                result.add_gap(gap)

        result.compute_overall()

        for dim in result.dimensions:
            if dim.score < 40:
                result.add_weakness(f"Low {dim.dimension.value} match ({dim.score:.0f}/100)", dim.dimension)

        for gap in result.skill_gaps:
            if gap.severity == GapSeverity.CRITICAL:
                result.add_risk(f"Missing critical skill: {gap.skill_name}")

        return result
