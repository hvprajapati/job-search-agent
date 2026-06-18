"""Tailoring domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.profile.domain.tailoring.value_objects import (
    TailoringStrategy, KeywordAnalysis, ResumeDiff, ResumeScore, GapReport,
)


@dataclass(kw_only=True)
class TailoredResume(BaseEntity):
    user_id: UUID
    base_resume_id: UUID
    job_id: UUID
    job_title: str = ""
    company_name: str = ""
    tailored_content: dict = field(default_factory=dict)
    original_content: dict = field(default_factory=dict)
    strategy: str = TailoringStrategy.MODERATE.value
    diffs: list[ResumeDiff] = field(default_factory=list)
    keyword_analysis: KeywordAnalysis | None = None
    gap_report: GapReport | None = None
    scores: ResumeScore | None = None
    version: int = 1
    parent_version_id: UUID | None = None
    factuality_score: float = 1.0
    factuality_violations: list[dict] = field(default_factory=list)
    generation_metadata: dict = field(default_factory=dict)
    is_accepted: bool = False
    accepted_at: datetime | None = None
    is_active: bool = True

    @classmethod
    def create(cls, *, user_id: UUID, base_resume_id: UUID, job_id: UUID,
               base_content: dict, job_title: str = "", company_name: str = "",
               strategy: str = "moderate") -> TailoredResume:
        return cls(
            user_id=user_id, base_resume_id=base_resume_id,
            job_id=job_id, job_title=job_title, company_name=company_name,
            tailored_content={}, original_content=base_content, strategy=strategy,
        )

    def add_diff(self, diff: ResumeDiff) -> None:
        self.diffs.append(diff)

    def record_factuality_issue(self, section: str, claim: str, reason: str) -> None:
        self.factuality_violations.append({"section": section, "claim": claim, "reason": reason})
        self.factuality_score = max(0.0, self.factuality_score - 0.1)

    def accept(self) -> None:
        self.is_accepted = True
        self.accepted_at = datetime.now(timezone.utc)
        self.mark_updated()

    @property
    def is_clean(self) -> bool:
        return self.factuality_score >= 0.95 and len(self.factuality_violations) == 0

    @property
    def ats_improvement(self) -> float | None:
        if self.keyword_analysis:
            return round(self.keyword_analysis.coverage_after - self.keyword_analysis.coverage_before, 2)
        return None
