"""SQLAlchemy ORM models for job domain."""
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, Float, Text, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin
from pathfinder.jobs.domain.entities import JobPosting, Company
from pathfinder.jobs.domain.value_objects import (
    RemotePolicy, JobSeniority, SourceType, CanonicalJobId, JobLocation, SalaryRange,
)


class CompanyModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    website: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(100))
    industry_tags: Mapped[list | None] = mapped_column(ARRAY(Text), server_default="{}")
    size_range: Mapped[str | None] = mapped_column(String(20))
    employee_count: Mapped[int | None] = mapped_column(Integer)
    funding_stage: Mapped[str | None] = mapped_column(String(50))
    total_funding: Mapped[int | None] = mapped_column(Integer)
    founded_year: Mapped[int | None] = mapped_column(Integer)
    headquarters: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    tech_stack: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    culture_tags: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    glassdoor_rating: Mapped[float | None] = mapped_column(Float)
    career_page_url: Mapped[str | None] = mapped_column(Text)

    def to_domain(self) -> Company:
        return Company(
            id=self.id, name=self.name, canonical_name=self.canonical_name,
            website=self.website or "", industry=self.industry or "",
            industry_tags=list(self.industry_tags or []),
            size_range=self.size_range or "", employee_count=self.employee_count,
            funding_stage=self.funding_stage or "", total_funding=self.total_funding,
            founded_year=self.founded_year, headquarters=self.headquarters or {},
            tech_stack=list(self.tech_stack or {}), culture_tags=self.culture_tags or {},
            glassdoor_rating=self.glassdoor_rating,
            career_page_url=self.career_page_url or "",
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, c: Company) -> "CompanyModel":
        return cls(
            id=c.id, name=c.name, canonical_name=c.canonical_name,
            website=c.website, industry=c.industry,
            industry_tags=c.industry_tags, size_range=c.size_range,
            employee_count=c.employee_count, funding_stage=c.funding_stage,
            total_funding=c.total_funding, founded_year=c.founded_year,
            headquarters=c.headquarters,
            tech_stack=c.tech_stack, culture_tags=c.culture_tags,
            glassdoor_rating=c.glassdoor_rating,
            career_page_url=c.career_page_url,
            created_at=c.created_at, updated_at=c.updated_at,
        )


class JobPostingModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_postings"

    canonical_job_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    company_id: Mapped[UUID | None] = mapped_column(PGUUID, ForeignKey("companies.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_title: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    remote_policy: Mapped[str] = mapped_column(String(20))
    description_raw: Mapped[str | None] = mapped_column(Text)
    description_clean: Mapped[str | None] = mapped_column(Text)
    description_summary: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50))
    application_url: Mapped[str | None] = mapped_column(Text)
    job_embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    refreshed_at: Mapped[datetime | None] = mapped_column()
    expires_at: Mapped[datetime | None] = mapped_column()
    tech_stack: Mapped[list | None] = mapped_column(ARRAY(Text), server_default="{}")
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    salary_currency: Mapped[str] = mapped_column(String(3), default="USD")
    seniority: Mapped[str] = mapped_column(String(30), default="unspecified")
    source_ids: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    source_urls: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    def to_domain(self) -> JobPosting:
        salary = None
        if self.salary_min is not None or self.salary_max is not None:
            salary = SalaryRange(
                min_amount=self.salary_min, max_amount=self.salary_max,
                currency=self.salary_currency or "USD",
            )
        return JobPosting(
            id=self.id, canonical_job_id=CanonicalJobId(value=self.canonical_job_id),
            company_id=self.company_id, title=self.title,
            normalized_title=self.normalized_title or "",
            location=JobLocation(**self.location) if self.location else JobLocation(),
            remote_policy=RemotePolicy(self.remote_policy) if self.remote_policy else RemotePolicy.UNSPECIFIED,
            description_raw=self.description_raw or "",
            description_clean=self.description_clean or "",
            description_summary=self.description_summary or "",
            source_url=self.source_url or "",
            source_type=SourceType(self.source_type) if self.source_type else SourceType.OTHER,
            application_url=self.application_url or "",
            is_active=self.is_active or True,
            first_seen_at=self.first_seen_at,
            last_seen_at=self.last_seen_at,
            refreshed_at=self.refreshed_at,
            expires_at=self.expires_at,
            tech_stack=list(self.tech_stack or []),
            salary_range=salary,
            seniority=JobSeniority(self.seniority) if self.seniority else JobSeniority.UNSPECIFIED,
            source_ids=self.source_ids or {},
            source_urls=self.source_urls or {},
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, j: JobPosting) -> "JobPostingModel":
        return cls(
            id=j.id, canonical_job_id=j.canonical_job_id.value,
            company_id=j.company_id, title=j.title,
            normalized_title=j.normalized_title,
            location={"city": j.location.city, "state": j.location.state,
                       "country": j.location.country, "display_text": j.location.display_text},
            remote_policy=j.remote_policy.value,
            description_raw=j.description_raw,
            description_clean=j.description_clean,
            description_summary=j.description_summary,
            source_url=j.source_url, source_type=j.source_type.value,
            application_url=j.application_url, is_active=j.is_active,
            first_seen_at=j.first_seen_at, last_seen_at=j.last_seen_at,
            refreshed_at=j.refreshed_at, expires_at=j.expires_at,
            tech_stack=j.tech_stack,
            salary_min=j.salary_range.min_amount if j.salary_range else None,
            salary_max=j.salary_range.max_amount if j.salary_range else None,
            salary_currency=j.salary_range.currency if j.salary_range else "USD",
            seniority=j.seniority.value,
            source_ids=j.source_ids, source_urls=j.source_urls,
            created_at=j.created_at, updated_at=j.updated_at,
        )
