"""SQLAlchemy ORM models for profile domain."""
from __future__ import annotations
from uuid import UUID
from sqlalchemy import String, Boolean, Integer, Float, Text, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin
from pathfinder.profile.domain.entities import Profile, Resume
from pathfinder.profile.domain.value_objects import (
    Skill, WorkExperience, Education, Project,
    SkillProficiency, SkillCategory,
)


class ProfileModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "profiles"

    tenant_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    structured_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsing_confidence: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    enrichment_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    source: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    full_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headline_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skill_names_snapshot: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    def to_domain(self) -> Profile:
        data = self.structured_data or {}
        return Profile(
            id=self.id, user_id=self.user_id,
            version=self.version or 1,
            is_active=self.is_active or True,
            full_name=data.get("full_name", ""),
            headline=data.get("headline", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            location=data.get("location"),
            summary=data.get("summary", ""),
            work_experiences=[_deserialize_work_experience(e) for e in data.get("work_experiences", [])],
            education=[_deserialize_education(e) for e in data.get("education", [])],
            skills=[_deserialize_skill(s) for s in data.get("skills", [])],
            projects=[Project(**p) for p in data.get("projects", [])],
            certifications=data.get("certifications", []),
            publications=data.get("publications", []),
            languages=data.get("languages", []),
            links=data.get("links", {}),
            parsing_confidence=self.parsing_confidence or {},
            enrichment_data=self.enrichment_data or {},
            source=self.source or [],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, profile: Profile) -> "ProfileModel":
        data = {
            "full_name": profile.full_name,
            "headline": profile.headline,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.location,
            "summary": profile.summary,
            "work_experiences": [_serialize_vo(e) for e in profile.work_experiences],
            "education": [_serialize_vo(e) for e in profile.education],
            "skills": [_serialize_vo(s) for s in profile.skills],
            "projects": [_serialize_vo(p) for p in profile.projects],
            "certifications": profile.certifications,
            "publications": profile.publications,
            "languages": profile.languages,
            "links": profile.links,
        }
        return cls(
            id=profile.id,
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            user_id=profile.user_id,
            version=profile.version,
            is_active=profile.is_active,
            structured_data=data,
            embedding=None,
            summary=profile.summary,
            parsing_confidence=profile.parsing_confidence,
            enrichment_data=profile.enrichment_data,
            source=profile.source,
            full_name_snapshot=profile.full_name,
            headline_snapshot=profile.headline,
            skill_names_snapshot=[s.name for s in profile.skills],
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )


class ResumeModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resumes"

    tenant_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_id: Mapped[str] = mapped_column(String(50), default="modern_professional")
    content: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_format: Mapped[str] = mapped_column(String(10), default="pdf")
    is_base: Mapped[bool] = mapped_column(Boolean, default=False)
    tailored_for_job_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    tailored_for_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    performance_metrics: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    ats_parse_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    versions: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")

    def to_domain(self) -> Resume:
        return Resume(
            id=self.id, user_id=self.user_id,
            name=self.name, description=self.description or "",
            template_id=self.template_id,
            content=self.content or {},
            file_url=self.file_url,
            file_format=self.file_format or "pdf",
            is_base=self.is_base or False,
            tailored_for_job_id=self.tailored_for_job_id,
            tailored_for_role=self.tailored_for_role,
            performance_metrics=self.performance_metrics or {},
            ats_parse_score=self.ats_parse_score,
            versions=self.versions or [],
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, r: Resume) -> "ResumeModel":
        return cls(
            id=r.id,
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            user_id=r.user_id, name=r.name,
            description=r.description, template_id=r.template_id,
            content=r.content, file_url=r.file_url,
            file_format=r.file_format, is_base=r.is_base,
            tailored_for_job_id=r.tailored_for_job_id,
            tailored_for_role=r.tailored_for_role,
            performance_metrics=r.performance_metrics,
            ats_parse_score=r.ats_parse_score,
            versions=r.versions if hasattr(r, 'versions') else [],
            created_at=r.created_at, updated_at=r.updated_at,
        )


def _serialize_vo(vo) -> dict:
    """Serialize a value object to a plain dict, handling non-JSON types."""
    from datetime import date, datetime
    from uuid import UUID as _UUID
    result = {}
    for k, v in vo.__dict__.items():
        if isinstance(v, tuple):
            result[k] = list(v)
        elif hasattr(v, 'value'):
            result[k] = v.value
        elif isinstance(v, (date, datetime)):
            result[k] = v.isoformat()
        elif isinstance(v, _UUID):
            result[k] = str(v)
        else:
            result[k] = v
    return result


def _deserialize_skill(data: dict) -> Skill:
    """Parse a JSONB skill dict back to a Skill VO, handling enum strings."""
    for field, enum_cls in (("proficiency", SkillProficiency), ("category", SkillCategory)):
        val = data.get(field)
        if isinstance(val, str) and val.strip():
            try:
                data[field] = enum_cls(val)
            except ValueError:
                data[field] = enum_cls.OTHER if enum_cls is SkillCategory else enum_cls.INTERMEDIATE
    return Skill(**data)


def _deserialize_work_experience(data: dict) -> WorkExperience:
    """Parse a JSONB work experience dict back to a WorkExperience VO, handling date strings."""
    from datetime import date as _date
    for field in ("start_date", "end_date"):
        val = data.get(field)
        if isinstance(val, str) and val.strip():
            try:
                data[field] = _date.fromisoformat(val.strip()[:10])
            except (ValueError, TypeError):
                data[field] = None
        elif not val:
            data[field] = None
    return WorkExperience(**data)


def _deserialize_education(data: dict) -> Education:
    """Parse a JSONB education dict back to an Education VO."""
    return Education(**data)
