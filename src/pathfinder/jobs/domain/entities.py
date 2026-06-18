"""Job domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.jobs.domain.value_objects import (
    SalaryRange, JobLocation, RemotePolicy, JobSeniority,
    CanonicalJobId, SourceType, SourceHealth, RawJobEntry,
)


@dataclass(kw_only=True)
class Company(BaseEntity):
    name: str
    canonical_name: str = ""
    website: str = ""
    industry: str = ""
    industry_tags: list[str] = field(default_factory=list)
    size_range: str = ""
    employee_count: int | None = None
    funding_stage: str = ""
    total_funding: int | None = None
    founded_year: int | None = None
    headquarters: dict = field(default_factory=dict)
    tech_stack: list[str] = field(default_factory=list)
    culture_tags: dict = field(default_factory=dict)
    glassdoor_rating: float | None = None
    career_page_url: str = ""

    @classmethod
    def create(cls, *, name: str, website: str = "") -> Company:
        return cls(name=name.strip(), canonical_name=name.strip().lower(), website=website)


@dataclass(kw_only=True)
class JobPosting(BaseEntity):
    canonical_job_id: CanonicalJobId
    company_id: UUID | None = None
    company_name: str = ""
    title: str = ""
    normalized_title: str = ""
    location: JobLocation = field(default_factory=JobLocation)
    remote_policy: RemotePolicy = RemotePolicy.UNSPECIFIED
    description_raw: str = ""
    description_clean: str = ""
    description_summary: str = ""
    source_url: str = ""
    source_type: SourceType = SourceType.OTHER
    application_url: str = ""
    is_active: bool = True
    is_verified: bool = False
    first_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    refreshed_at: datetime | None = None
    expires_at: datetime | None = None
    tech_stack: list[str] = field(default_factory=list)
    salary_range: SalaryRange | None = None
    seniority: JobSeniority = JobSeniority.UNSPECIFIED
    required_skills: list[dict] = field(default_factory=list)
    nice_to_have_skills: list[dict] = field(default_factory=list)
    required_years_min: int | None = None
    urgency_flag: bool = False
    source_ids: dict[str, str] = field(default_factory=dict)
    source_urls: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: RawJobEntry, canonical_id: CanonicalJobId) -> JobPosting:
        return cls(
            canonical_job_id=canonical_id,
            title=raw.raw_title.strip(),
            company_name=raw.raw_company.strip(),
            location=JobLocation(display_text=raw.raw_location.strip()),
            description_raw=raw.raw_description,
            source_url=raw.source_url,
            source_type=raw.source_type,
            application_url=raw.application_url or raw.source_url,
            source_ids={raw.source_name: raw.source_id},
            source_urls={raw.source_name: raw.source_url},
        )

    def merge_from_source(self, raw: RawJobEntry) -> bool:
        changed = False
        if raw.source_name not in self.source_ids:
            self.source_ids[raw.source_name] = raw.source_id
            self.source_urls[raw.source_name] = raw.source_url
            changed = True
        if raw.application_url and not self.application_url:
            self.application_url = raw.application_url
            changed = True
        if changed:
            self.last_seen_at = datetime.now(timezone.utc)
            self.mark_updated()
        return changed

    def expire(self) -> None:
        self.is_active = False
        self.expires_at = datetime.now(timezone.utc)
        self.mark_updated()
