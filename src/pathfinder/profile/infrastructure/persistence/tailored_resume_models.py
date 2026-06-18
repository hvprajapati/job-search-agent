"""SQLAlchemy model for tailored resumes."""
from uuid import UUID
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin
from pathfinder.profile.domain.tailoring.entities import TailoredResume
from pathfinder.profile.domain.tailoring.value_objects import (
    ResumeDiff, KeywordAnalysis, KeywordEntry, ResumeScore, GapReport,
)


class TailoredResumeModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tailored_resumes"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    base_resume_id: Mapped[UUID] = mapped_column(
        PGUUID, ForeignKey("resumes.id"), nullable=False
    )
    job_id: Mapped[UUID] = mapped_column(
        PGUUID, ForeignKey("job_postings.id"), nullable=False
    )
    job_title: Mapped[str] = mapped_column(String(255), default="")
    company_name: Mapped[str] = mapped_column(String(255), default="")
    tailored_content: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    original_content: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    strategy: Mapped[str] = mapped_column(String(20), default="moderate")
    diffs: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    keyword_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    gap_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_version_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    factuality_score: Mapped[float] = mapped_column(Float, default=1.0)
    factuality_violations: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    generation_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_domain(self) -> TailoredResume:
        return TailoredResume(
            id=self.id, user_id=self.user_id,
            base_resume_id=self.base_resume_id, job_id=self.job_id,
            job_title=self.job_title or "", company_name=self.company_name or "",
            tailored_content=self.tailored_content or {},
            original_content=self.original_content or {},
            strategy=self.strategy or "moderate",
            diffs=[ResumeDiff(**d) for d in (self.diffs or [])],
            keyword_analysis=KeywordAnalysis(**self.keyword_analysis) if self.keyword_analysis else None,
            gap_report=GapReport(**self.gap_report) if self.gap_report else None,
            scores=ResumeScore(**self.scores) if self.scores else None,
            version=self.version or 1,
            parent_version_id=self.parent_version_id,
            factuality_score=self.factuality_score or 1.0,
            factuality_violations=self.factuality_violations or [],
            generation_metadata=self.generation_metadata or {},
            is_accepted=self.is_accepted or False,
            accepted_at=self.accepted_at,
            is_active=self.is_active or True,
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, t: TailoredResume) -> "TailoredResumeModel":
        return cls(
            id=t.id, user_id=t.user_id,
            base_resume_id=t.base_resume_id, job_id=t.job_id,
            job_title=t.job_title, company_name=t.company_name,
            tailored_content=t.tailored_content,
            original_content=t.original_content,
            strategy=t.strategy,
            diffs=[{**d.__dict__} for d in t.diffs],
            keyword_analysis=_vo_to_dict(t.keyword_analysis) if t.keyword_analysis else None,
            gap_report=_vo_to_dict(t.gap_report) if t.gap_report else None,
            scores=_vo_to_dict(t.scores) if t.scores else None,
            version=t.version, parent_version_id=t.parent_version_id,
            factuality_score=t.factuality_score,
            factuality_violations=t.factuality_violations,
            generation_metadata=t.generation_metadata,
            is_accepted=t.is_accepted, accepted_at=t.accepted_at,
            is_active=t.is_active,
            created_at=t.created_at, updated_at=t.updated_at,
        )


def _vo_to_dict(vo) -> dict:
    """Convert a frozen dataclass value object to a plain dict."""
    if vo is None:
        return None
    result = {}
    for key, value in vo.__dict__.items():
        if hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, list, dict, tuple)):
            result[key] = _vo_to_dict(value)
        elif isinstance(value, tuple):
            result[key] = list(value)
        else:
            result[key] = value
    return result
