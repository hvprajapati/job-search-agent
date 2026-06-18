# Pathfinder — Sprint 4: Job Discovery Domain

**Sprint:** 4 of 7
**Duration:** 10 Days
**Prerequisite:** Sprint 3 (Profile domain complete)
**Goal:** Jobs flow continuously from 3 production sources. Normalized, deduplicated, enriched, searchable. Background sweeps via Celery. Production-grade pluggable source framework.
**Source:** FINAL_ARCHITECTURE.md §7 + EPICS_AND_TASKS.md Epic 2

---

## Day 1–2: Domain Core + Source Framework

### Files to Create

```
src/pathfinder/jobs/domain/
├── entities.py           # JobPosting, Company, JobSource aggregate
├── value_objects.py      # SalaryRange, JobLocation, RemotePolicy, CanonicalJobId, JobSeniority
├── repositories.py       # JobRepository, CompanyRepository, JobSourceRepository (abstract)
├── services.py           # JobNormalizer, JobDedupService, JobEnrichmentService
├── events.py             # JobDiscovered, JobDedupMerged, JobExpired, SweepCompleted
├── exceptions.py         # JobNotFoundError, ScrapingError, DedupError

src/pathfinder/jobs/application/ports/
├── job_source_port.py    # Abstract JobSource interface (pluggable framework)
├── web_search_port.py    # Abstract web search for enrichment

src/pathfinder/jobs/infrastructure/scraping/
├── base_scraper.py       # BaseJobSource ABC + RateLimiter + HealthTracker
├── source_registry.py    # SourceRegistry — register, list, sweep_all
├── greenhouse_scraper.py # Greenhouse Harvest API adapter
├── ycombinator_scraper.py# YC Work at a Startup API adapter
├── hn_scraper.py         # Hacker News "Who's Hiring" parser
```

### `src/pathfinder/jobs/domain/value_objects.py`

```python
"""Job domain value objects."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
from pathfinder.shared.domain.base_value_object import BaseValueObject
from pathfinder.shared.domain.exceptions import ValidationError


class RemotePolicy(StrEnum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"
    UNSPECIFIED = "unspecified"


class JobSeniority(StrEnum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    LEAD = "lead"
    MANAGER = "manager"
    DIRECTOR = "director"
    EXECUTIVE = "executive"
    UNSPECIFIED = "unspecified"


class SourceType(StrEnum):
    JOB_BOARD = "job_board"
    CAREER_PAGE = "career_page"
    COMMUNITY = "community"
    RECRUITER = "recruiter"
    OTHER = "other"


class SourceHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    DISABLED = "disabled"


@dataclass(frozen=True, kw_only=True)
class SalaryRange(BaseValueObject):
    min_amount: float | None = None
    max_amount: float | None = None
    currency: str = "USD"
    source: str = "unlisted"  # "listed", "inferred", "ml_prediction"
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.min_amount is not None and self.max_amount is not None:
            if self.min_amount > self.max_amount:
                raise ValidationError("min_amount must be <= max_amount", field="salary")
        if self.min_amount is not None and self.min_amount < 0:
            raise ValidationError("Salary cannot be negative", field="salary")

    @property
    def midpoint(self) -> float | None:
        if self.min_amount and self.max_amount:
            return (self.min_amount + self.max_amount) / 2
        return self.min_amount or self.max_amount


@dataclass(frozen=True, kw_only=True)
class JobLocation(BaseValueObject):
    city: str | None = None
    state: str | None = None
    country: str | None = None
    is_remote: bool = False
    display_text: str = ""  # Original text from source


@dataclass(frozen=True, kw_only=True)
class CanonicalJobId(BaseValueObject):
    """Stable dedup key derived from normalized title + company + location."""
    value: str

    @staticmethod
    def compute(*, title: str, company_name: str, location: str = "") -> CanonicalJobId:
        normalized_title = title.strip().lower()
        normalized_company = company_name.strip().lower()
        normalized_location = location.strip().lower()
        key = f"{normalized_title}|{normalized_company}|{normalized_location}"
        hash_val = hashlib.sha256(key.encode()).hexdigest()[:16]
        return CanonicalJobId(value=hash_val)


@dataclass(frozen=True, kw_only=True)
class RawJobEntry(BaseValueObject):
    """Unprocessed job data from a source — before normalization."""
    source_name: str
    source_type: SourceType
    raw_title: str
    raw_company: str
    raw_location: str = ""
    raw_description: str = ""
    source_url: str = ""
    application_url: str = ""
    source_id: str = ""  # Source's own ID for this job
    raw_metadata: dict = field(default_factory=dict)
    discovered_at: str = ""  # ISO timestamp
```

### `src/pathfinder/jobs/domain/entities.py`

```python
"""Job domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.shared.domain.identifiers import JobId, new_job_id
from pathfinder.jobs.domain.value_objects import (
    SalaryRange, JobLocation, RemotePolicy, JobSeniority,
    CanonicalJobId, SourceType, SourceHealth,
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
    locations: list[dict] = field(default_factory=list)
    tech_stack: list[str] = field(default_factory=list)
    culture_tags: dict = field(default_factory=dict)
    crunchbase_id: str = ""
    glassdoor_rating: float | None = None
    career_page_url: str = ""

    @classmethod
    def create(cls, *, name: str, website: str = "") -> Company:
        canonical = name.strip().lower()
        return cls(name=name.strip(), canonical_name=canonical, website=website)

    def merge_enrichment(self, other: Company) -> None:
        """Merge enrichment data from another Company (e.g., from Crunchbase)."""
        if other.website and not self.website:
            self.website = other.website
        if other.industry and not self.industry:
            self.industry = other.industry
        if other.funding_stage and not self.funding_stage:
            self.funding_stage = other.funding_stage
        if other.glassdoor_rating and not self.glassdoor_rating:
            self.glassdoor_rating = other.glassdoor_rating
        self.mark_updated()


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

    # Enrichment data (populated after creation)
    tech_stack: list[str] = field(default_factory=list)
    salary_range: SalaryRange | None = None
    seniority: JobSeniority = JobSeniority.UNSPECIFIED
    required_skills: list[dict] = field(default_factory=list)
    nice_to_have_skills: list[dict] = field(default_factory=list)
    required_years_min: int | None = None
    education_required: str = ""
    benefits_inferred: list[str] = field(default_factory=list)
    urgency_flag: bool = False

    # Source tracking
    source_ids: dict[str, str] = field(default_factory=dict)  # source_name → source_id
    source_urls: dict[str, str] = field(default_factory=dict)  # source_name → url

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
        """Merge a duplicate listing from another source. Returns True if anything changed."""
        changed = False
        if raw.source_name not in self.source_ids:
            self.source_ids[raw.source_name] = raw.source_id
            self.source_urls[raw.source_name] = raw.source_url
            changed = True
        if raw.application_url and not self.application_url:
            self.application_url = raw.application_url
            changed = True
        if raw.raw_description and len(raw.raw_description) > len(self.description_raw):
            self.description_raw = raw.raw_description
            changed = True
        if changed:
            self.last_seen_at = datetime.now(timezone.utc)
            self.mark_updated()
        return changed

    def mark_refreshed(self) -> None:
        self.refreshed_at = datetime.now(timezone.utc)
        self.last_seen_at = datetime.now(timezone.utc)
        self.is_active = True
        self.mark_updated()

    def expire(self) -> None:
        self.is_active = False
        self.expires_at = datetime.now(timezone.utc)
        self.mark_updated()

    @property
    def days_since_first_seen(self) -> int:
        return (datetime.now(timezone.utc) - self.first_seen_at).days

    @property
    def job_id(self) -> JobId:
        return JobId(self.id)


@dataclass(kw_only=True)
class JobSource(BaseEntity):
    name: str
    source_type: SourceType
    base_url: str = ""
    scraper_config: dict = field(default_factory=dict)
    priority: int = 5
    sweep_interval_min: int = 60
    health_status: SourceHealth = SourceHealth.HEALTHY
    last_sweep_at: datetime | None = None
    last_sweep_status: str = ""
    success_rate: float = 1.0
    jobs_per_sweep_avg: float = 0.0
    consecutive_fails: int = 0
    is_enabled: bool = True

    def record_success(self, jobs_found: int, duration_ms: int) -> None:
        self.last_sweep_status = "success"
        self.last_sweep_at = datetime.now(timezone.utc)
        self.jobs_per_sweep_avg = (self.jobs_per_sweep_avg * 0.7) + (jobs_found * 0.3)
        self.success_rate = min(1.0, self.success_rate + 0.02)
        self.consecutive_fails = 0
        if self.health_status == SourceHealth.DEGRADED:
            self.health_status = SourceHealth.HEALTHY
        self.mark_updated()

    def record_failure(self, error: str) -> None:
        self.consecutive_fails += 1
        self.success_rate = max(0.0, self.success_rate - 0.1)
        self.last_sweep_status = f"failed: {error[:100]}"
        if self.consecutive_fails >= 3:
            self.health_status = SourceHealth.FAILING
        elif self.consecutive_fails >= 1:
            self.health_status = SourceHealth.DEGRADED
        self.mark_updated()
```

### `src/pathfinder/jobs/domain/exceptions.py`

```python
"""Job domain exceptions."""
from pathfinder.shared.domain.exceptions import NotFoundError, DomainError, ValidationError


class JobNotFoundError(NotFoundError):
    def __init__(self, job_id: str = "") -> None:
        super().__init__(f"Job not found{' : ' + job_id if job_id else ''}")

class CompanyNotFoundError(NotFoundError):
    def __init__(self, company_id: str = "") -> None:
        super().__init__(f"Company not found{' : ' + company_id if company_id else ''}")

class ScrapingError(DomainError):
    def __init__(self, source: str, detail: str = "") -> None:
        super().__init__(f"Scraping failed for {source}{': ' + detail if detail else ''}")

class DedupError(DomainError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Deduplication error: {detail}")

class InvalidFilterError(ValidationError):
    def __init__(self, field: str) -> None:
        super().__init__(f"Invalid filter: {field}", field=field)
```

### `src/pathfinder/jobs/domain/repositories.py`

```python
"""Job domain repository interfaces (abstract)."""
from abc import abstractmethod
from uuid import UUID
from pathfinder.shared.domain.base_repository import BaseRepository
from pathfinder.jobs.domain.entities import JobPosting, Company, JobSource


class JobRepository(BaseRepository[JobPosting]):
    @abstractmethod
    async def get_by_canonical_id(self, canonical_id: str) -> JobPosting | None: ...
    @abstractmethod
    async def search(self, *, query: str | None = None, filters: dict | None = None,
                     sort: str = "-first_seen_at", cursor: str | None = None,
                     limit: int = 20) -> tuple[list[JobPosting], str | None, int]: ...
    @abstractmethod
    async def find_similar(self, job_id: UUID, limit: int = 10) -> list[JobPosting]: ...
    @abstractmethod
    async def mark_stale_jobs(self, older_than_days: int = 30) -> int: ...
    @abstractmethod
    async def list_active(self, *, cursor: str | None = None, limit: int = 100) -> list[JobPosting]: ...


class CompanyRepository(BaseRepository[Company]):
    @abstractmethod
    async def get_by_canonical_name(self, canonical_name: str) -> Company | None: ...
    @abstractmethod
    async def search(self, *, query: str | None = None, cursor: str | None = None,
                     limit: int = 20) -> list[Company]: ...
    @abstractmethod
    async def get_or_create(self, name: str) -> Company: ...


class JobSourceRepository(BaseRepository[JobSource]):
    @abstractmethod
    async def get_by_name(self, name: str) -> JobSource | None: ...
    @abstractmethod
    async def list_enabled(self) -> list[JobSource]: ...
    @abstractmethod
    async def list_all(self) -> list[JobSource]: ...
```

### `src/pathfinder/jobs/application/ports/job_source_port.py`

```python
"""Abstract job source interface — the pluggable source framework."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathfinder.jobs.domain.value_objects import RawJobEntry, SourceType


@dataclass
class SweepResult:
    source_name: str
    raw_jobs: list[RawJobEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0
    is_partial: bool = False

    @property
    def success(self) -> bool:
        return len(self.errors) == 0 or self.is_partial

    @property
    def job_count(self) -> int:
        return len(self.raw_jobs)


class JobSourcePort(ABC):
    """Every job source (Greenhouse, YC, HN, etc.) implements this interface."""

    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @property
    @abstractmethod
    def source_type(self) -> SourceType: ...

    @abstractmethod
    async def sweep(self) -> SweepResult:
        """Fetch all currently available jobs from this source.

        Returns SweepResult with raw job entries.
        May return is_partial=True if some pages succeeded but not all.
        Raises ScrapingError only if the entire sweep failed.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the source is reachable. Returns True if healthy."""
        ...

    @property
    @abstractmethod
    def rate_limit_delay_seconds(self) -> float:
        """Minimum delay between requests to this source."""
        ...

    @property
    @abstractmethod
    def priority(self) -> int:
        """1 = highest priority, 10 = lowest. Drives sweep frequency."""
        ...
```

### `src/pathfinder/jobs/infrastructure/scraping/base_scraper.py`

```python
"""Base scraper utilities: rate limiting, health tracking, retry logic."""
import asyncio
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import httpx
from pathfinder.shared.config import get_settings


class RateLimiter:
    """Token bucket rate limiter for HTTP requests to job sources."""

    def __init__(self, requests_per_second: float = 1.0, burst: int = 5) -> None:
        self._rate = requests_per_second
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()

    async def acquire(self) -> None:
        while True:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
            self._last_refill = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            await asyncio.sleep(0.1)


class HealthTracker:
    """Tracks source health across sweeps."""

    def __init__(self, window_size: int = 10) -> None:
        self._history: list[dict] = []
        self._window = window_size

    def record(self, success: bool, job_count: int, duration_ms: int,
               error: str = "") -> None:
        self._history.append({
            "timestamp": datetime.now(timezone.utc),
            "success": success, "job_count": job_count,
            "duration_ms": duration_ms, "error": error,
        })
        if len(self._history) > self._window * 2:
            self._history = self._history[-self._window:]

    @property
    def recent_success_rate(self) -> float:
        recent = self._history[-self._window:]
        if not recent:
            return 1.0
        return sum(1 for r in recent if r["success"]) / len(recent)

    @property
    def consecutive_failures(self) -> int:
        count = 0
        for r in reversed(self._history):
            if not r["success"]:
                count += 1
            else:
                break
        return count


async def retry_with_backoff(
    fn, max_retries: int = 3, base_delay: float = 1.0,
    max_delay: float = 60.0, *args, **kwargs,
):
    """Execute an async function with exponential backoff retry."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt), max_delay)
                await asyncio.sleep(delay)
    raise last_error  # type: ignore
```

### `src/pathfinder/jobs/infrastructure/scraping/source_registry.py`

```python
"""Central registry for all job sources."""
from pathfinder.jobs.application.ports.job_source_port import JobSourcePort


class SourceRegistry:
    """Manages all registered job sources. Enables sweep_all, health checks, etc."""

    def __init__(self) -> None:
        self._sources: dict[str, JobSourcePort] = {}

    def register(self, source: JobSourcePort) -> None:
        if source.source_name in self._sources:
            raise ValueError(f"Source already registered: {source.source_name}")
        self._sources[source.source_name] = source

    def get(self, name: str) -> JobSourcePort | None:
        return self._sources.get(name)

    def list_all(self) -> list[JobSourcePort]:
        return sorted(self._sources.values(), key=lambda s: s.priority)

    def list_enabled(self) -> list[JobSourcePort]:
        return [s for s in self.list_all()]

    @property
    def source_count(self) -> int:
        return len(self._sources)

    @property
    def source_names(self) -> list[str]:
        return list(self._sources.keys())


# Global singleton
source_registry = SourceRegistry()
```

---

## Day 3–4: Three Source Adapters

### `src/pathfinder/jobs/infrastructure/scraping/greenhouse_scraper.py`

```python
"""Greenhouse job board scraper.

Greenhouse hosts career pages for thousands of companies at:
  https://boards.greenhouse.io/{company_name}

This scraper uses the public Greenhouse JSON API.
Each board lists all active jobs in JSON format.
"""
import asyncio
import httpx
import time
from pathfinder.jobs.application.ports.job_source_port import JobSourcePort, SweepResult
from pathfinder.jobs.domain.value_objects import RawJobEntry, SourceType
from pathfinder.jobs.infrastructure.scraping.base_scraper import RateLimiter, retry_with_backoff


GREENHOUSE_COMPANIES = [
    "stripe", "airbnb", "dropbox", "square", "shopify", "spotify",
    "cloudflare", "datadog", "figma", "notion", "linear", "vercel",
    "github", "gitlab", "reddit", "pinterest", "snap", "uber",
    "doordash", "instacart", "roblox", "discord", "twitch",
    "coinbase", "plaid", "brex", "ramp", "mercury",
    "anthropic", "openai", "scaleai", "huggingface",
    "databricks", "snowflake", "confluent", "mongodb",
    "hashicorp", "twilio", "asana", "atlassian",
]

API_URL_TEMPLATE = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"


class GreenhouseScraper(JobSourcePort):
    source_name = "greenhouse"
    source_type = SourceType.CAREER_PAGE
    priority = 2
    rate_limit_delay_seconds = 0.5
    _rate_limiter = RateLimiter(requests_per_second=2.0, burst=5)

    def __init__(self, companies: list[str] | None = None) -> None:
        self._companies = companies or GREENHOUSE_COMPANIES
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": "Pathfinder/0.1 (Job Discovery Agent; contact@pathfinder.com)"},
            )
        return self._client

    async def sweep(self) -> SweepResult:
        result = SweepResult(source_name=self.source_name)
        start = time.monotonic()

        async def fetch_company(company: str) -> list[RawJobEntry]:
            jobs = []
            await self._rate_limiter.acquire()
            client = await self._get_client()
            url = API_URL_TEMPLATE.format(company=company)
            try:
                resp = await retry_with_backoff(
                    client.get, max_retries=2, base_delay=1.0, url=url
                )
                resp.raise_for_status()
                data = resp.json()
                for job in data.get("jobs", []):
                    jobs.append(RawJobEntry(
                        source_name=self.source_name,
                        source_type=self.source_type,
                        raw_title=job.get("title", ""),
                        raw_company=job.get("company_name", company),
                        raw_location=job.get("location", {}).get("name", ""),
                        raw_description=self._format_description(job),
                        source_url=job.get("absolute_url", ""),
                        application_url=job.get("absolute_url", ""),
                        source_id=str(job.get("id", "")),
                        discovered_at="",
                    ))
            except Exception as e:
                result.errors.append(f"{company}: {e}")
            return jobs

        # Process companies with concurrency limit
        sem = asyncio.Semaphore(5)
        async def bounded_fetch(company: str) -> list[RawJobEntry]:
            async with sem:
                return await fetch_company(company)

        tasks = [bounded_fetch(c) for c in self._companies]
        all_job_lists = await asyncio.gather(*tasks, return_exceptions=True)

        for job_list in all_job_lists:
            if isinstance(job_list, list):
                result.raw_jobs.extend(job_list)

        if result.errors and not result.raw_jobs:
            result.is_partial = False
        elif result.errors:
            result.is_partial = True

        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            resp = await client.get(
                API_URL_TEMPLATE.format(company="stripe"),
            )
            resp.raise_for_status()
            return "jobs" in resp.json()
        except Exception:
            return False

    def _format_description(self, job: dict) -> str:
        parts = []
        for dept in job.get("departments", []):
            parts.append(dept.get("name", ""))
        for office in job.get("offices", []):
            parts.append(office.get("name", ""))
        return " | ".join(parts) if parts else ""

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
```

### `src/pathfinder/jobs/infrastructure/scraping/ycombinator_scraper.py`

```python
"""Y Combinator "Work at a Startup" job scraper.

API: https://www.workatastartup.com/api/jobs
Public JSON API. No authentication required for public listings.
"""
import time
import httpx
from pathfinder.jobs.application.ports.job_source_port import JobSourcePort, SweepResult
from pathfinder.jobs.domain.value_objects import RawJobEntry, SourceType
from pathfinder.jobs.infrastructure.scraping.base_scraper import RateLimiter, retry_with_backoff


class YCombinatorScraper(JobSourcePort):
    source_name = "ycombinator"
    source_type = SourceType.JOB_BOARD
    priority = 1
    rate_limit_delay_seconds = 1.0
    _rate_limiter = RateLimiter(requests_per_second=1.0, burst=3)

    API_URL = "https://www.workatastartup.com/api/jobs"
    PAGE_SIZE = 100

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": "Pathfinder/0.1 (Job Discovery Agent; contact@pathfinder.com)"},
            )
        return self._client

    async def sweep(self) -> SweepResult:
        result = SweepResult(source_name=self.source_name)
        start = time.monotonic()
        all_jobs = []
        page = 1

        try:
            while True:
                await self._rate_limiter.acquire()
                client = await self._get_client()
                resp = await retry_with_backoff(
                    client.get, max_retries=2, base_delay=1.0,
                    url=self.API_URL,
                    params={"page": page, "per_page": self.PAGE_SIZE},
                )
                resp.raise_for_status()
                data = resp.json()

                jobs_batch = data.get("jobs", []) if isinstance(data, dict) else data
                if not jobs_batch:
                    break

                for job in jobs_batch:
                    all_jobs.append(RawJobEntry(
                        source_name=self.source_name,
                        source_type=self.source_type,
                        raw_title=job.get("title", ""),
                        raw_company=job.get("company_name", ""),
                        raw_location=self._format_location(job),
                        raw_description=job.get("description", ""),
                        source_url=job.get("url", ""),
                        application_url=job.get("apply_url", "") or job.get("url", ""),
                        source_id=str(job.get("id", "")),
                        discovered_at="",
                        raw_metadata={
                            "salary_min": job.get("salary_min"),
                            "salary_max": job.get("salary_max"),
                            "equity": job.get("equity"),
                            "remote": job.get("remote", False),
                            "skills": job.get("skills", []),
                        },
                    ))

                page += 1
                if page > 10:  # Safety limit
                    break

        except Exception as e:
            result.errors.append(str(e))
            if all_jobs:
                result.is_partial = True

        result.raw_jobs = all_jobs
        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            resp = await client.get(self.API_URL, params={"page": 1, "per_page": 1})
            resp.raise_for_status()
            return True
        except Exception:
            return False

    def _format_location(self, job: dict) -> str:
        locations = job.get("locations", [])
        if not locations:
            return job.get("location", "")
        return ", ".join(loc.get("name", "") for loc in locations)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
```

### `src/pathfinder/jobs/infrastructure/scraping/hn_scraper.py`

```python
"""Hacker News "Who's Hiring" monthly thread scraper.

The monthly thread contains top-level comments where each comment
is a job posting. Format varies but typically includes:
  Company Name | Role | Location | Remote | Tech Stack
"""
import re
import time
from datetime import datetime, timezone, timedelta
import httpx
from pathfinder.jobs.application.ports.job_source_port import JobSourcePort, SweepResult
from pathfinder.jobs.domain.value_objects import RawJobEntry, SourceType
from pathfinder.jobs.infrastructure.scraping.base_scraper import RateLimiter, retry_with_backoff


class HackerNewsScraper(JobSourcePort):
    source_name = "hackernews"
    source_type = SourceType.COMMUNITY
    priority = 3
    rate_limit_delay_seconds = 2.0
    _rate_limiter = RateLimiter(requests_per_second=0.5, burst=2)

    HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
    SEARCH_API = "https://hn.algolia.com/api/v1/search"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": "Pathfinder/0.1 (Job Discovery Agent; contact@pathfinder.com)"},
            )
        return self._client

    async def sweep(self) -> SweepResult:
        result = SweepResult(source_name=self.source_name)
        start = time.monotonic()

        try:
            # Find the latest "Who's Hiring" thread via Algolia search
            client = await self._get_client()
            await self._rate_limiter.acquire()
            search_resp = await retry_with_backoff(
                client.get, max_retries=2, base_delay=2.0,
                url=self.SEARCH_API,
                params={
                    "query": "Who is hiring",
                    "tags": "story",
                    "numericFilters": "created_at_i>{}".format(
                        int((datetime.now(timezone.utc) - timedelta(days=45)).timestamp())
                    ),
                    "hitsPerPage": 5,
                },
            )
            search_resp.raise_for_status()
            search_data = search_resp.json()

            thread_id = None
            for hit in search_data.get("hits", []):
                title = hit.get("title", "")
                if "who is hiring" in title.lower() and "month" in title.lower():
                    thread_id = hit.get("objectID")
                    break

            if not thread_id:
                result.errors.append("No recent Who's Hiring thread found")
                return result

            # Fetch the thread
            await self._rate_limiter.acquire()
            thread_resp = await client.get(
                f"{self.HN_API_BASE}/item/{thread_id}.json"
            )
            thread_resp.raise_for_status()
            thread = thread_resp.json()

            # Each top-level comment is a job posting
            job_comments = []
            kids = thread.get("kids", [])[:200]  # Limit to 200 comments

            for kid_id in kids:
                await self._rate_limiter.acquire()
                try:
                    comment_resp = await retry_with_backoff(
                        client.get, max_retries=1, base_delay=1.0,
                        url=f"{self.HN_API_BASE}/item/{kid_id}.json",
                    )
                    if comment_resp.status_code == 200:
                        comment = comment_resp.json()
                        text = comment.get("text", "")
                        if text and len(text) > 20:
                            job_comments.append({
                                "id": str(kid_id),
                                "text": self._strip_html(text),
                            })
                except Exception:
                    continue

            # Parse each comment into RawJobEntry
            for comment in job_comments:
                parsed = self._parse_comment(comment["text"])
                if parsed:
                    result.raw_jobs.append(RawJobEntry(
                        source_name=self.source_name,
                        source_type=self.source_type,
                        raw_title=parsed.get("title", ""),
                        raw_company=parsed.get("company", ""),
                        raw_location=parsed.get("location", ""),
                        raw_description=comment["text"],
                        source_url=f"https://news.ycombinator.com/item?id={comment['id']}",
                        application_url=parsed.get("apply_url", ""),
                        source_id=comment["id"],
                        discovered_at="",
                        raw_metadata=parsed,
                    ))

        except Exception as e:
            result.errors.append(str(e))

        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.HN_API_BASE}/item/8863.json")
            return resp.status_code == 200
        except Exception:
            return False

    def _strip_html(self, text: str) -> str:
        return re.sub(r"<[^>]+>", "", text)

    def _parse_comment(self, text: str) -> dict | None:
        """Parse HN comment into structured job fields.

        Common format: "Company | Role | Location | Remote | Tech"
        Also: "Company is hiring Role (Location) — Tech stack: ..."
        """
        lines = text.strip().split("\n")
        first_line = lines[0].strip() if lines else ""

        if len(first_line) < 10:
            return None

        # Try pipe-separated format
        if "|" in first_line:
            parts = [p.strip() for p in first_line.split("|")]
            return {
                "company": parts[0] if len(parts) > 0 else "",
                "title": parts[1] if len(parts) > 1 else "",
                "location": parts[2] if len(parts) > 2 else "",
                "remote": "remote" in first_line.lower(),
            }

        # Try "is hiring" format
        hiring_match = re.match(r"(.+?)\s+(?:is\s+hiring|hiring)\s+(.+?)(?:\s+\((.+?)\))?(?:\s|$)", first_line, re.IGNORECASE)
        if hiring_match:
            return {
                "company": hiring_match.group(1).strip(),
                "title": hiring_match.group(2).strip(),
                "location": hiring_match.group(3) or "",
                "remote": "remote" in first_line.lower(),
            }

        # Fallback: return raw text
        return {
            "company": first_line[:100],
            "title": "",
            "location": "",
            "remote": "remote" in first_line.lower(),
        }

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
```

---

## Day 5–6: Normalization, Deduplication, Enrichment Services

### `src/pathfinder/jobs/domain/services.py`

```python
"""Job domain services — normalization, deduplication, enrichment."""
import re
from datetime import datetime, timezone
from pathfinder.jobs.domain.entities import JobPosting, Company
from pathfinder.jobs.domain.value_objects import (
    RawJobEntry, CanonicalJobId, RemotePolicy, JobSeniority,
    SalaryRange, JobLocation,
)
from pathfinder.jobs.domain.repositories import JobRepository, CompanyRepository


class JobNormalizer:
    """Transforms RawJobEntry → JobPosting with standardized fields."""

    # Title normalization mapping
    TITLE_SYNONYMS = {
        "sde": "Software Engineer",
        "swe": "Software Engineer",
        "sw engineer": "Software Engineer",
        "sr.": "Senior",
        "jr.": "Junior",
        "eng": "Engineer",
        "eng.": "Engineer",
        "ml eng": "Machine Learning Engineer",
        "mle": "Machine Learning Engineer",
        "devops": "DevOps Engineer",
        "sre": "Site Reliability Engineer",
        "fe": "Frontend Engineer",
        "be": "Backend Engineer",
        "fs": "Full Stack Engineer",
    }

    # Location patterns
    LOCATION_PATTERNS = [
        re.compile(r"(?P<city>[\w\s]+),\s*(?P<state>[A-Z]{2})(?:\s*,?\s*(?P<country>USA|US))?", re.IGNORECASE),
        re.compile(r"(?P<city>[\w\s]+),\s*(?P<country>[A-Z]{2,})", re.IGNORECASE),
    ]

    @classmethod
    def normalize_title(cls, raw_title: str) -> str:
        """Normalize a job title to a standard form."""
        title = raw_title.strip()
        for pattern, replacement in cls.TITLE_SYNONYMS.items():
            title = re.sub(rf"\b{re.escape(pattern)}\b", replacement, title, flags=re.IGNORECASE)
        # Remove excessive whitespace
        title = re.sub(r"\s+", " ", title).strip()
        return title

    @classmethod
    def infer_remote_policy(cls, raw_location: str, description: str = "",
                            metadata: dict | None = None) -> RemotePolicy:
        """Infer remote policy from text signals."""
        text = f"{raw_location} {description}".lower()
        if metadata and metadata.get("remote"):
            return RemotePolicy.REMOTE
        if "remote-first" in text or "fully remote" in text:
            return RemotePolicy.REMOTE
        if "remote" in text:
            return RemotePolicy.HYBRID
        if "hybrid" in text:
            return RemotePolicy.HYBRID
        if "onsite" in text or "on-site" in text or "in office" in text:
            return RemotePolicy.ONSITE
        return RemotePolicy.UNSPECIFIED

    @classmethod
    def infer_seniority(cls, title: str, description: str = "",
                        required_years: int | None = None) -> JobSeniority:
        """Infer seniority level from title and description."""
        text = f"{title} {description}".lower()

        if required_years is not None:
            if required_years >= 10:
                return JobSeniority.STAFF
            if required_years >= 7:
                return JobSeniority.SENIOR
            if required_years >= 4:
                return JobSeniority.MID
            if required_years >= 1:
                return JobSeniority.JUNIOR
            return JobSeniority.INTERN

        # Keyword-based inference
        if any(w in text for w in ["principal", "distinguished", "fellow"]):
            return JobSeniority.PRINCIPAL
        if any(w in text for w in ["staff engineer", "staff software"]):
            return JobSeniority.STAFF
        if any(w in text for w in ["senior", "sr.", "sr ", "lead", "head of"]):
            return JobSeniority.SENIOR
        if any(w in text for w in ["junior", "jr.", "jr ", "associate", "entry level", "entry-level"]):
            return JobSeniority.JUNIOR
        if any(w in text for w in ["intern", "internship"]):
            return JobSeniority.INTERN
        if any(w in text for w in ["manager", "director", "vp", "head"]):
            return JobSeniority.MANAGER

        return JobSeniority.MID  # Default for unmarked roles

    @classmethod
    def normalize(cls, raw: RawJobEntry) -> JobPosting:
        """Full normalization pipeline: RawJobEntry → JobPosting."""
        canonical_id = CanonicalJobId.compute(
            title=raw.raw_title, company_name=raw.raw_company,
            location=raw.raw_location,
        )
        title = cls.normalize_title(raw.raw_title)
        remote = cls.infer_remote_policy(
            raw.raw_location, raw.raw_description, raw.raw_metadata
        )
        seniority = cls.infer_seniority(title, raw.raw_description)

        job = JobPosting.from_raw(raw, canonical_id)
        job.normalized_title = title
        job.remote_policy = remote
        job.seniority = seniority
        job.description_clean = cls._clean_description(raw.raw_description)
        job.description_summary = job.description_clean[:300] if job.description_clean else ""

        return job

    @classmethod
    def _clean_description(cls, raw: str) -> str:
        """Strip HTML, normalize whitespace."""
        text = re.sub(r"<[^>]+>", "", raw)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


class JobDedupService:
    """Detect and merge duplicate job listings across sources."""

    def __init__(self, job_repo: JobRepository, company_repo: CompanyRepository) -> None:
        self._jobs = job_repo
        self._companies = company_repo

    async def deduplicate(self, job: JobPosting) -> tuple[JobPosting, bool]:
        """Check for duplicates. Returns (canonical_job, is_new).

        If the job is new, it is saved and returned.
        If a duplicate exists, the existing job is updated with the new source info.
        """
        existing = await self._jobs.get_by_canonical_id(job.canonical_job_id.value)
        if existing is None:
            # New job — ensure company exists
            if job.company_name:
                company = await self._companies.get_or_create(job.company_name)
                job.company_id = company.id
            await self._jobs.save(job)
            return job, True
        else:
            # Merge into existing
            changed = existing.merge_from_source(
                RawJobEntry(
                    source_name=list(job.source_ids.keys())[0] if job.source_ids else "unknown",
                    source_type=job.source_type,
                    raw_title=job.title,
                    raw_company=job.company_name,
                    raw_location=job.location.display_text,
                    raw_description=job.description_raw,
                    source_url=job.source_url,
                    application_url=job.application_url,
                    source_id=list(job.source_ids.values())[0] if job.source_ids else "",
                )
            )
            if changed:
                existing.mark_refreshed()
                await self._jobs.save(existing)
            return existing, False


class JobEnrichmentService:
    """Enrich jobs with LLM-extracted metadata (tech stack, salary, etc.)."""

    # Stub for Sprint 4 — full LLM enrichment in Sprint 5 (Matching).
    # Sprint 4 does basic regex-based enrichment.

    TECH_KEYWORDS: dict[str, list[str]] = {
        "Python": ["python", "django", "flask", "fastapi", "pytorch"],
        "JavaScript": ["javascript", "js", "node", "react", "vue", "angular", "typescript"],
        "Java": ["java", "spring", "hibernate", "kotlin", "scala"],
        "Go": ["go", "golang"],
        "Rust": ["rust", "cargo"],
        "Ruby": ["ruby", "rails", "rspec"],
        "AWS": ["aws", "amazon web services", "s3", "lambda", "ec2"],
        "GCP": ["gcp", "google cloud", "bigquery"],
        "Azure": ["azure", "microsoft cloud"],
        "Docker": ["docker", "container"],
        "Kubernetes": ["kubernetes", "k8s"],
        "PostgreSQL": ["postgresql", "postgres"],
        "MongoDB": ["mongodb", "mongo"],
        "Redis": ["redis"],
        "Kafka": ["kafka", "event streaming"],
        "GraphQL": ["graphql"],
        "gRPC": ["grpc"],
        "Terraform": ["terraform", "infra as code"],
        "React": ["react", "reactjs", "react.js"],
        "TypeScript": ["typescript", "ts"],
    }

    @classmethod
    def extract_tech_stack(cls, text: str) -> list[str]:
        """Extract known technologies from text using keyword matching."""
        found = []
        text_lower = text.lower()
        for tech, keywords in cls.TECH_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                found.append(tech)
        return sorted(found)

    @classmethod
    def extract_salary(cls, text: str) -> SalaryRange | None:
        """Extract salary information from text using regex."""
        # Match "$120,000 - $180,000" or "$120k - $180k"
        patterns = [
            r"\$(?P<min>[\d,]+)(?:k|K)?\s*(?:-|–|to)\s*\$(?P<max>[\d,]+)(?:k|K)?",
            r"\$(?P<amount>[\d,]+)(?:k|K)?(?:\s*(?:per|a|\/)\s*(?:year|yr|annum|annual))",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groupdict()
                if "min" in groups and "max" in groups:
                    min_val = cls._parse_salary_amount(groups["min"])
                    max_val = cls._parse_salary_amount(groups["max"])
                    return SalaryRange(min_amount=min_val, max_amount=max_val, source="inferred")
                elif "amount" in groups:
                    val = cls._parse_salary_amount(groups["amount"])
                    return SalaryRange(min_amount=val, max_amount=val * 1.2, source="inferred")
        return None

    @classmethod
    def enrich(cls, job: JobPosting) -> JobPosting:
        """Run all enrichment on a job posting."""
        text = f"{job.title} {job.description_raw}"
        job.tech_stack = cls.extract_tech_stack(text)
        salary = cls.extract_salary(text)
        if salary:
            job.salary_range = salary
        return job

    @staticmethod
    def _parse_salary_amount(raw: str) -> float:
        cleaned = raw.replace(",", "").strip()
        if cleaned.lower().endswith("k"):
            return float(cleaned[:-1]) * 1000
        return float(cleaned)
```

---

## Day 7: Persistence Layer

### `src/pathfinder/jobs/infrastructure/persistence/models.py`

```python
"""SQLAlchemy ORM models for job domain."""
from uuid import UUID
from sqlalchemy import String, Boolean, Integer, Float, Text, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin
from pathfinder.jobs.domain.entities import JobPosting, Company, JobSource
from pathfinder.jobs.domain.value_objects import (
    RemotePolicy, JobSeniority, SourceType, SourceHealth, CanonicalJobId,
    JobLocation, SalaryRange,
)


class CompanyModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255))
    canonical_name: Mapped[str] = mapped_column(String(255), unique=True)
    website: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(100))
    industry_tags: Mapped[list | None] = mapped_column(ARRAY(Text), server_default="{}")
    size_range: Mapped[str | None] = mapped_column(String(20))
    employee_count: Mapped[int | None] = mapped_column(Integer)
    funding_stage: Mapped[str | None] = mapped_column(String(50))
    total_funding: Mapped[int | None] = mapped_column(Integer)
    founded_year: Mapped[int | None] = mapped_column(Integer)
    headquarters: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    locations: Mapped[list | None] = mapped_column(ARRAY(JSONB), server_default="{}")
    tech_stack: Mapped[list | None] = mapped_column(ARRAY(Text), server_default="{}")
    culture_tags: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    crunchbase_id: Mapped[str | None] = mapped_column(String(100))
    glassdoor_rating: Mapped[float | None] = mapped_column(Float)
    career_page_url: Mapped[str | None] = mapped_column(Text)

    def to_domain(self) -> Company:
        return Company(
            id=self.id, name=self.name, canonical_name=self.canonical_name,
            website=self.website or "", industry=self.industry or "",
            industry_tags=self.industry_tags or [],
            size_range=self.size_range or "", employee_count=self.employee_count,
            funding_stage=self.funding_stage or "", total_funding=self.total_funding,
            founded_year=self.founded_year, headquarters=self.headquarters or {},
            locations=self.locations or [], tech_stack=self.tech_stack or [],
            culture_tags=self.culture_tags or {},
            crunchbase_id=self.crunchbase_id or "",
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
            headquarters=c.headquarters, locations=c.locations,
            tech_stack=c.tech_stack, culture_tags=c.culture_tags,
            crunchbase_id=c.crunchbase_id, glassdoor_rating=c.glassdoor_rating,
            career_page_url=c.career_page_url,
            created_at=c.created_at, updated_at=c.updated_at,
        )


class JobPostingModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_postings"

    canonical_job_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    company_id: Mapped[UUID | None] = mapped_column(PGUUID, ForeignKey("companies.id"))
    title: Mapped[str] = mapped_column(String(255))
    normalized_title: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    remote_policy: Mapped[str] = mapped_column(String(20), default="unspecified")
    description_raw: Mapped[str | None] = mapped_column(Text)
    description_clean: Mapped[str | None] = mapped_column(Text)
    description_summary: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50))
    application_url: Mapped[str | None] = mapped_column(Text)
    job_embedding: Mapped[list[float] | None] = mapped_column(Vector(3072))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    first_seen_at: Mapped[DateTime] = mapped_column()
    last_seen_at: Mapped[DateTime] = mapped_column()
    refreshed_at: Mapped[DateTime | None] = mapped_column()
    expires_at: Mapped[DateTime | None] = mapped_column()

    # Enrichment snapshot columns
    tech_stack: Mapped[list | None] = mapped_column(ARRAY(Text), server_default="{}")
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    salary_currency: Mapped[str] = mapped_column(String(3), default="USD")
    seniority: Mapped[str] = mapped_column(String(30), default="unspecified")

    # Source tracking
    source_ids: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    source_urls: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    def to_domain(self) -> JobPosting:
        salary = None
        if self.salary_min is not None or self.salary_max is not None:
            salary = SalaryRange(min_amount=self.salary_min, max_amount=self.salary_max,
                                 currency=self.salary_currency, source="stored")
        return JobPosting(
            id=self.id, canonical_job_id=CanonicalJobId(value=self.canonical_job_id),
            company_id=self.company_id, title=self.title,
            normalized_title=self.normalized_title or "",
            location=JobLocation(**self.location) if self.location else JobLocation(),
            remote_policy=RemotePolicy(self.remote_policy),
            description_raw=self.description_raw or "",
            description_clean=self.description_clean or "",
            description_summary=self.description_summary or "",
            source_url=self.source_url, source_type=SourceType(self.source_type),
            application_url=self.application_url or "",
            is_active=self.is_active, is_verified=self.is_verified,
            first_seen_at=self.first_seen_at, last_seen_at=self.last_seen_at,
            refreshed_at=self.refreshed_at, expires_at=self.expires_at,
            tech_stack=self.tech_stack or [], salary_range=salary,
            seniority=JobSeniority(self.seniority),
            source_ids=self.source_ids or {}, source_urls=self.source_urls or {},
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
            is_verified=j.is_verified if hasattr(j, 'is_verified') else False,
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


class JobSourceModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_sources"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    type: Mapped[str] = mapped_column(String(50))
    base_url: Mapped[str | None] = mapped_column(Text)
    scraper_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    priority: Mapped[int] = mapped_column(Integer, default=5)
    sweep_interval_min: Mapped[int] = mapped_column(Integer, default=60)
    health_status: Mapped[str] = mapped_column(String(20), default="healthy")
    last_sweep_at: Mapped[DateTime | None] = mapped_column()
    last_sweep_status: Mapped[str | None] = mapped_column(String(20))
    success_rate: Mapped[float] = mapped_column(Float, default=1.0)
    jobs_per_sweep_avg: Mapped[float] = mapped_column(Float, default=0.0)
    consecutive_fails: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_domain(self) -> JobSource:
        return JobSource(
            id=self.id, name=self.name, source_type=SourceType(self.type),
            base_url=self.base_url or "", scraper_config=self.scraper_config or {},
            priority=self.priority, sweep_interval_min=self.sweep_interval_min,
            health_status=SourceHealth(self.health_status),
            last_sweep_at=self.last_sweep_at, last_sweep_status=self.last_sweep_status or "",
            success_rate=self.success_rate or 1.0,
            jobs_per_sweep_avg=self.jobs_per_sweep_avg or 0.0,
            consecutive_fails=self.consecutive_fails or 0,
            is_enabled=self.is_enabled, created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, s: JobSource) -> "JobSourceModel":
        return cls(
            id=s.id, name=s.name, type=s.source_type.value,
            base_url=s.base_url, scraper_config=s.scraper_config,
            priority=s.priority, sweep_interval_min=s.sweep_interval_min,
            health_status=s.health_status.value,
            last_sweep_at=s.last_sweep_at, last_sweep_status=s.last_sweep_status,
            success_rate=s.success_rate, jobs_per_sweep_avg=s.jobs_per_sweep_avg,
            consecutive_fails=s.consecutive_fails, is_enabled=s.is_enabled,
            created_at=s.created_at, updated_at=s.updated_at,
        )
```

### `src/pathfinder/jobs/infrastructure/persistence/job_repository.py`

```python
"""SQLAlchemy JobRepository implementation."""
from uuid import UUID
from sqlalchemy import select, func, update, delete, text, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.jobs.domain.entities import JobPosting
from pathfinder.jobs.domain.repositories import JobRepository
from pathfinder.jobs.infrastructure.persistence.models import JobPostingModel

VALID_SORT_FIELDS = {"first_seen_at", "last_seen_at", "title", "salary_max"}


class SqlJobRepository(JobRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> JobPosting | None:
        model = await self._session.get(JobPostingModel, id)
        return model.to_domain() if model else None

    async def get_by_canonical_id(self, canonical_id: str) -> JobPosting | None:
        stmt = select(JobPostingModel).where(JobPostingModel.canonical_job_id == canonical_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def save(self, entity: JobPosting) -> None:
        model = JobPostingModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity: JobPosting) -> None:
        await self._session.execute(
            update(JobPostingModel)
            .where(JobPostingModel.id == entity.id)
            .values(is_active=False)
        )

    async def search(self, *, query: str | None = None, filters: dict | None = None,
                     sort: str = "-first_seen_at", cursor: str | None = None,
                     limit: int = 20) -> tuple[list[JobPosting], str | None, int]:
        stmt = select(JobPostingModel).where(JobPostingModel.is_active == True)
        count_stmt = select(func.count()).select_from(JobPostingModel).where(JobPostingModel.is_active == True)

        # Full-text search
        if query:
            ts_query = func.plainto_tsquery("english", query)
            stmt = stmt.where(
                func.to_tsvector("english", JobPostingModel.description_clean).op("@@")(ts_query)
            )
            count_stmt = count_stmt.where(
                func.to_tsvector("english", JobPostingModel.description_clean).op("@@")(ts_query)
            )

        # Filters
        filters = filters or {}
        if "title" in filters:
            stmt = stmt.where(JobPostingModel.title.ilike(f"%{filters['title']}%"))
            count_stmt = count_stmt.where(JobPostingModel.title.ilike(f"%{filters['title']}%"))
        if "remote_policy" in filters:
            stmt = stmt.where(JobPostingModel.remote_policy == filters["remote_policy"])
            count_stmt = count_stmt.where(JobPostingModel.remote_policy == filters["remote_policy"])
        if "seniority" in filters:
            stmt = stmt.where(JobPostingModel.seniority == filters["seniority"])
            count_stmt = count_stmt.where(JobPostingModel.seniority == filters["seniority"])
        if "company_id" in filters:
            stmt = stmt.where(JobPostingModel.company_id == filters["company_id"])
            count_stmt = count_stmt.where(JobPostingModel.company_id == filters["company_id"])
        if "salary_min" in filters:
            stmt = stmt.where(JobPostingModel.salary_min >= filters["salary_min"])
            count_stmt = count_stmt.where(JobPostingModel.salary_min >= filters["salary_min"])
        if "source_type" in filters:
            stmt = stmt.where(JobPostingModel.source_type == filters["source_type"])
            count_stmt = count_stmt.where(JobPostingModel.source_type == filters["source_type"])
        if "posted_after" in filters:
            stmt = stmt.where(JobPostingModel.first_seen_at >= filters["posted_after"])
            count_stmt = count_stmt.where(JobPostingModel.first_seen_at >= filters["posted_after"])

        # Sorting
        col = sort.lstrip("-")
        if col in VALID_SORT_FIELDS:
            order_col = getattr(JobPostingModel, col)
            stmt = stmt.order_by(order_col.desc() if sort.startswith("-") else order_col.asc())
        else:
            stmt = stmt.order_by(JobPostingModel.first_seen_at.desc())

        stmt = stmt.limit(limit + 1)  # +1 to detect next page

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        has_more = len(models) > limit
        if has_more:
            models = models[:limit]
        next_cursor = str(models[-1].id) if has_more else None

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        return [m.to_domain() for m in models], next_cursor, total

    async def find_similar(self, job_id: UUID, limit: int = 10) -> list[JobPosting]:
        job = await self._session.get(JobPostingModel, job_id)
        if not job or job.job_embedding is None:
            return []
        stmt = select(JobPostingModel).where(
            JobPostingModel.is_active == True,
            JobPostingModel.id != job_id,
        ).order_by(
            JobPostingModel.job_embedding.cosine_distance(job.job_embedding)
        ).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def list_active(self, *, cursor: str | None = None,
                          limit: int = 100) -> list[JobPosting]:
        stmt = select(JobPostingModel).where(
            JobPostingModel.is_active == True
        ).order_by(JobPostingModel.first_seen_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def mark_stale_jobs(self, older_than_days: int = 30) -> int:
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        stmt = (
            update(JobPostingModel)
            .where(JobPostingModel.last_seen_at < cutoff, JobPostingModel.is_active == True)
            .values(is_active=False, expires_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount or 0
```

### `src/pathfinder/jobs/infrastructure/persistence/company_repository.py`

```python
"""SQLAlchemy CompanyRepository implementation."""
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.jobs.domain.entities import Company
from pathfinder.jobs.domain.repositories import CompanyRepository
from pathfinder.jobs.infrastructure.persistence.models import CompanyModel


class SqlCompanyRepository(CompanyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Company | None:
        model = await self._session.get(CompanyModel, id)
        return model.to_domain() if model else None

    async def get_by_canonical_name(self, canonical_name: str) -> Company | None:
        stmt = select(CompanyModel).where(CompanyModel.canonical_name == canonical_name)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def save(self, entity: Company) -> None:
        model = CompanyModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity: Company) -> None:
        model = await self._session.get(CompanyModel, entity.id)
        if model:
            await self._session.delete(model)

    async def get_or_create(self, name: str) -> Company:
        canonical = name.strip().lower()
        existing = await self.get_by_canonical_name(canonical)
        if existing:
            return existing
        company = Company.create(name=name.strip())
        await self.save(company)
        return company

    async def search(self, *, query: str | None = None,
                     cursor: str | None = None, limit: int = 20) -> list[Company]:
        stmt = select(CompanyModel)
        if query:
            stmt = stmt.where(CompanyModel.name.ilike(f"%{query}%"))
        stmt = stmt.order_by(CompanyModel.name.asc()).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]
```

---

## Day 8: Celery Tasks + API Endpoints

### `src/pathfinder/agent/infrastructure/celery_tasks/scraping.py`

```python
"""Celery tasks for job discovery sweeps."""
import asyncio
import time
from celery import Celery
from celery.utils.log import get_task_logger
from pathfinder.shared.config import get_settings
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.jobs.infrastructure.scraping.source_registry import source_registry
from pathfinder.jobs.infrastructure.scraping.greenhouse_scraper import GreenhouseScraper
from pathfinder.jobs.infrastructure.scraping.ycombinator_scraper import YCombinatorScraper
from pathfinder.jobs.infrastructure.scraping.hn_scraper import HackerNewsScraper
from pathfinder.jobs.domain.services import JobNormalizer, JobDedupService, JobEnrichmentService
from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository
from pathfinder.jobs.infrastructure.persistence.company_repository import SqlCompanyRepository
from pathfinder.jobs.infrastructure.persistence.models import JobSourceModel

logger = get_task_logger(__name__)
settings = get_settings()

# Celery app (configured once, imported by beat)
app = Celery("pathfinder", broker=settings.redis_url)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_queues=["scraping", "llm_tasks", "celery"],
    task_routes={
        "pathfinder.agent.infrastructure.celery_tasks.scraping.*": {"queue": "scraping"},
    },
)


def _register_sources():
    """Register all MVP sources on module load."""
    if source_registry.source_count == 0:
        source_registry.register(GreenhouseScraper())
        source_registry.register(YCombinatorScraper())
        source_registry.register(HackerNewsScraper())


@app.task(name="sweep_all_sources", bind=True, max_retries=0)
def sweep_all_sources(self):
    """Sweep all registered job sources. Called by Celery Beat every hour."""
    return asyncio.run(_sweep_all_sources_async())


async def _sweep_all_sources_async():
    _register_sources()
    maker = get_sessionmaker()

    async with maker() as session:
        company_repo = SqlCompanyRepository(session)
        job_repo = SqlJobRepository(session)
        normalizer = JobNormalizer()
        dedup = JobDedupService(job_repo, company_repo)
        enricher = JobEnrichmentService()

        total_new = 0
        total_updated = 0
        results = {}

        for source in source_registry.list_enabled():
            logger.info(f"Sweeping source: {source.source_name}")
            try:
                result = await source.sweep()
                new_count = 0
                updated_count = 0

                for raw in result.raw_jobs:
                    try:
                        job = normalizer.normalize(raw)
                        job = enricher.enrich(job)
                        canonical, is_new = await dedup.deduplicate(job)
                        if is_new:
                            new_count += 1
                        else:
                            updated_count += 1
                    except Exception as e:
                        logger.error(f"Error processing job from {source.source_name}: {e}")

                # Update source stats
                source_model = await session.get(JobSourceModel, source.source_name)
                if source_model is None:
                    continue  # Source not in DB yet

                if result.errors:
                    source_model.health_status = "degraded" if result.raw_jobs else "failing"
                    source_model.consecutive_fails += 1
                else:
                    source_model.health_status = "healthy"
                    source_model.consecutive_fails = 0

                source_model.last_sweep_at = func.now()
                source_model.last_sweep_status = "success" if not result.errors else "partial"
                source_model.success_rate = (
                    source_model.success_rate * 0.9 + (1.0 if not result.errors else 0.5) * 0.1
                )
                source_model.jobs_per_sweep_avg = result.job_count

                total_new += new_count
                total_updated += updated_count
                results[source.source_name] = {
                    "raw": result.job_count, "new": new_count,
                    "updated": updated_count, "errors": result.errors,
                    "duration_ms": result.duration_ms,
                }

            except Exception as e:
                logger.error(f"Sweep failed for {source.source_name}: {e}")
                results[source.source_name] = {"error": str(e)}

        await session.commit()

    logger.info(f"Sweep complete: {total_new} new, {total_updated} updated across {len(results)} sources")
    return {"new": total_new, "updated": total_updated, "sources": results}


@app.task(name="sweep_single_source", bind=True, max_retries=2, default_retry_delay=300)
def sweep_single_source(self, source_name: str):
    """Sweep a single source by name."""
    return asyncio.run(_sweep_single_async(source_name))


async def _sweep_single_async(source_name: str):
    _register_sources()
    source = source_registry.get(source_name)
    if source is None:
        return {"error": f"Unknown source: {source_name}"}
    # Same pipeline as sweep_all for a single source
    maker = get_sessionmaker()
    async with maker() as session:
        company_repo = SqlCompanyRepository(session)
        job_repo = SqlJobRepository(session)
        dedup = JobDedupService(job_repo, company_repo)
        result = await source.sweep()
        new_count = 0
        for raw in result.raw_jobs:
            job = JobNormalizer.normalize(raw)
            job = JobEnrichmentService.enrich(job)
            _, is_new = await dedup.deduplicate(job)
            if is_new:
                new_count += 1
        await session.commit()
        return {"source": source_name, "raw": result.job_count, "new": new_count}


@app.task(name="mark_stale_jobs", bind=True)
def mark_stale_jobs(self, older_than_days: int = 30):
    """Mark jobs as inactive if not seen recently."""
    return asyncio.run(_mark_stale_async(older_than_days))


async def _mark_stale_async(older_than_days: int):
    maker = get_sessionmaker()
    async with maker() as session:
        repo = SqlJobRepository(session)
        count = await repo.mark_stale_jobs(older_than_days)
        await session.commit()
        logger.info(f"Marked {count} jobs as stale")
        return {"stale_count": count}
```

### `src/pathfinder/jobs/presentation/router.py`

```python
"""Job Search and Company API routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User
from pathfinder.jobs.domain.repositories import JobRepository, CompanyRepository
from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository
from pathfinder.jobs.infrastructure.persistence.company_repository import SqlCompanyRepository
from pathfinder.jobs.domain.exceptions import JobNotFoundError, CompanyNotFoundError, InvalidFilterError

router = APIRouter(prefix="/v1", tags=["Jobs & Companies"])


async def get_job_repo(session: AsyncSession = Depends(get_session)) -> JobRepository:
    return SqlJobRepository(session)


async def get_company_repo(session: AsyncSession = Depends(get_session)) -> CompanyRepository:
    return SqlCompanyRepository(session)


@router.get("/jobs")
async def search_jobs(
    q: str | None = Query(None, description="Free-text search query"),
    title: str | None = Query(None),
    company_id: UUID | None = Query(None),
    remote_policy: str | None = Query(None, pattern="^(remote|hybrid|onsite)$"),
    seniority: str | None = Query(None),
    salary_min: int | None = Query(None, ge=0),
    source_type: str | None = Query(None),
    posted_after: str | None = Query(None),
    sort: str = Query("-first_seen_at"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    repo: JobRepository = Depends(get_job_repo),
):
    filters = {}
    if title:
        filters["title"] = title
    if company_id:
        filters["company_id"] = company_id
    if remote_policy:
        filters["remote_policy"] = remote_policy
    if seniority:
        filters["seniority"] = seniority
    if salary_min:
        filters["salary_min"] = salary_min
    if source_type:
        filters["source_type"] = source_type
    if posted_after:
        from datetime import datetime
        filters["posted_after"] = datetime.fromisoformat(posted_after)

    jobs, next_cursor, total = await repo.search(
        query=q, filters=filters, sort=sort, limit=limit,
    )
    return {
        "data": [_job_to_response(j) for j in jobs],
        "meta": {"cursor_next": next_cursor, "count": total, "limit": limit},
    }


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    repo: JobRepository = Depends(get_job_repo),
    company_repo: CompanyRepository = Depends(get_company_repo),
):
    job = await repo.get_by_id(job_id)
    if not job:
        raise JobNotFoundError(str(job_id))
    company = None
    if job.company_id:
        company = await company_repo.get_by_id(job.company_id)
    return {"data": _job_to_response(job, company)}


@router.get("/jobs/{job_id}/similar")
async def similar_jobs(
    job_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    repo: JobRepository = Depends(get_job_repo),
):
    jobs = await repo.find_similar(job_id, limit)
    return {"data": [_job_to_response(j) for j in jobs]}


@router.get("/companies")
async def search_companies(
    q: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    repo: CompanyRepository = Depends(get_company_repo),
):
    companies = await repo.search(query=q, limit=limit)
    return {"data": [_company_to_response(c) for c in companies]}


@router.get("/companies/{company_id}")
async def get_company(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    repo: CompanyRepository = Depends(get_company_repo),
):
    company = await repo.get_by_id(company_id)
    if not company:
        raise CompanyNotFoundError(str(company_id))
    return {"data": _company_to_response(company)}


def _job_to_response(j, company=None) -> dict:
    return {
        "job_id": str(j.id),
        "canonical_job_id": j.canonical_job_id.value,
        "title": j.title,
        "normalized_title": j.normalized_title,
        "company": {
            "company_id": str(company.id) if company else None,
            "name": j.company_name,
            "industry": company.industry if company else "",
        } if company or j.company_name else None,
        "location": {"city": j.location.city, "state": j.location.state,
                      "country": j.location.country, "display_text": j.location.display_text},
        "remote_policy": j.remote_policy.value,
        "description_summary": j.description_summary,
        "salary_range": {
            "min": j.salary_range.min_amount, "max": j.salary_range.max_amount,
            "currency": j.salary_range.currency,
        } if j.salary_range else None,
        "tech_stack": j.tech_stack,
        "seniority": j.seniority.value,
        "source_type": j.source_type.value,
        "source_url": j.source_url,
        "application_url": j.application_url,
        "first_seen_at": j.first_seen_at.isoformat() if j.first_seen_at else None,
        "is_active": j.is_active,
        "urgency_flag": j.urgency_flag,
    }


def _company_to_response(c) -> dict:
    return {
        "company_id": str(c.id),
        "name": c.name,
        "website": c.website,
        "industry": c.industry,
        "size_range": c.size_range,
        "funding_stage": c.funding_stage,
        "founded_year": c.founded_year,
        "headquarters": c.headquarters,
        "tech_stack": c.tech_stack,
        "glassdoor_rating": c.glassdoor_rating,
        "active_jobs_count": 0,  # Computed separately
    }
```

### `src/pathfinder/shared/infrastructure/main.py` — Update

```python
# Add import:
from pathfinder.jobs.presentation.router import router as jobs_router

# Add router:
app.include_router(jobs_router)
```

---

## Day 9: Celery Beat Schedule + Source Initialization

### Celery Beat Configuration

Add to `src/pathfinder/agent/infrastructure/celery_tasks/scraping.py`:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    "sweep-all-sources": {
        "task": "sweep_all_sources",
        "schedule": crontab(minute="7"),  # Every hour at :07 (off-peak minute)
    },
    "mark-stale-jobs": {
        "task": "mark_stale_jobs",
        "schedule": crontab(hour="4", minute="23"),  # Daily at 04:23 UTC
        "kwargs": {"older_than_days": 30},
    },
}
app.conf.timezone = "UTC"
```

### Source Initialization Migration

**`alembic/versions/003_seed_job_sources.py`**:

```python
"""003_seed_job_sources — Insert 3 MVP job sources."""
from alembic import op
import sqlalchemy as sa
from uuid import uuid4
from datetime import datetime, timezone

revision = "003"
down_revision = "002"


def upgrade():
    now = datetime.now(timezone.utc)
    sources = [
        ("greenhouse", "career_page", "https://boards.greenhouse.io", 2, 60,
         '{"companies": ["stripe","airbnb","dropbox",...]}'),
        ("ycombinator", "job_board", "https://www.workatastartup.com", 1, 60,
         '{"page_size": 100}'),
        ("hackernews", "community", "https://news.ycombinator.com", 3, 360,
         '{"parse_comments": true}'),
    ]
    for name, stype, url, prio, interval, config in sources:
        op.execute(
            sa.text(
                "INSERT INTO job_sources (id, name, type, base_url, scraper_config, priority, "
                "sweep_interval_min, health_status, is_enabled, created_at, updated_at) "
                "VALUES (:id, :name, :type, :url, :config::jsonb, :prio, :interval, "
                "'healthy', true, :now, :now) "
                "ON CONFLICT (name) DO UPDATE SET scraper_config = EXCLUDED.scraper_config"
            ).bindparams(
                id=uuid4(), name=name, type=stype, url=url, config=config,
                prio=prio, interval=interval, now=now,
            )
        )


def downgrade():
    op.execute("DELETE FROM job_sources WHERE name IN ('greenhouse', 'ycombinator', 'hackernews')")
```

---

## Day 10: Tests + Gate Review

### `tests/unit/jobs/test_value_objects.py`

```python
import pytest
from pathfinder.jobs.domain.value_objects import (
    SalaryRange, CanonicalJobId, RemotePolicy, JobSeniority, RawJobEntry, SourceType,
)
from pathfinder.shared.domain.exceptions import ValidationError

def test_salary_range_valid():
    sr = SalaryRange(min_amount=100000, max_amount=150000)
    assert sr.midpoint == 125000

def test_salary_range_inverted_raises():
    with pytest.raises(ValidationError):
        SalaryRange(min_amount=150000, max_amount=100000)

def test_canonical_job_id_deterministic():
    a = CanonicalJobId.compute(title="SWE", company_name="Stripe", location="SF")
    b = CanonicalJobId.compute(title="SWE", company_name="Stripe", location="SF")
    assert a == b

def test_canonical_job_id_different():
    a = CanonicalJobId.compute(title="SWE", company_name="Stripe", location="SF")
    b = CanonicalJobId.compute(title="SWE", company_name="Square", location="SF")
    assert a != b

def test_remote_policy_enum():
    assert RemotePolicy.REMOTE.value == "remote"

def test_seniority_enum():
    assert JobSeniority.SENIOR.value == "senior"

def test_raw_job_entry_creation():
    raw = RawJobEntry(
        source_name="test", source_type=SourceType.JOB_BOARD,
        raw_title="Engineer", raw_company="Acme",
    )
    assert raw.source_name == "test"
```

### `tests/unit/jobs/test_normalizer.py`

```python
from pathfinder.jobs.domain.services import JobNormalizer
from pathfinder.jobs.domain.value_objects import RawJobEntry, SourceType

def test_normalize_title_expands_swe():
    assert JobNormalizer.normalize_title("SWE") == "Software Engineer"

def test_infer_remote_from_text():
    policy = JobNormalizer.infer_remote_policy("San Francisco", "fully remote position")
    assert policy.value == "remote"

def test_infer_hybrid():
    policy = JobNormalizer.infer_remote_policy("NYC", "hybrid role, 2 days in office")
    assert policy.value == "hybrid"

def test_infer_seniority_from_title():
    s = JobNormalizer.infer_seniority("Senior Software Engineer", "")
    assert s.value == "senior"

def test_infer_seniority_from_years():
    s = JobNormalizer.infer_seniority("Engineer", "", required_years=8)
    assert s.value == "senior"

def test_normalize_creates_job_posting():
    raw = RawJobEntry(
        source_name="test", source_type=SourceType.CAREER_PAGE,
        raw_title="Sr. Software Engineer", raw_company="Acme Corp",
        raw_location="San Francisco, CA", raw_description="Building great products",
        source_url="https://acme.com/jobs/1", source_id="123",
    )
    job = JobNormalizer.normalize(raw)
    assert job.normalized_title == "Senior Software Engineer"
    assert job.remote_policy.value == "onsite"  # SF = not listed as remote
    assert job.seniority.value == "senior"
```

### `tests/unit/jobs/test_entities.py`

```python
from pathfinder.jobs.domain.entities import JobPosting, Company, JobSource
from pathfinder.jobs.domain.value_objects import (
    CanonicalJobId, RawJobEntry, SourceType, SourceHealth,
)

def test_company_create():
    c = Company.create(name="Stripe", website="https://stripe.com")
    assert c.canonical_name == "stripe"

def test_job_from_raw():
    canonical = CanonicalJobId.compute(title="SWE", company_name="Stripe")
    raw = RawJobEntry(
        source_name="greenhouse", source_type=SourceType.CAREER_PAGE,
        raw_title="Software Engineer", raw_company="Stripe",
        raw_location="San Francisco", source_url="https://...", source_id="42",
    )
    job = JobPosting.from_raw(raw, canonical)
    assert job.canonical_job_id == canonical
    assert job.company_name == "Stripe"

def test_job_merge_adds_source():
    canonical = CanonicalJobId.compute(title="SWE", company_name="Stripe")
    raw1 = RawJobEntry(source_name="greenhouse", source_type=SourceType.CAREER_PAGE,
                       raw_title="SWE", raw_company="Stripe", raw_location="SF",
                       source_url="url1", source_id="1")
    job = JobPosting.from_raw(raw1, canonical)

    raw2 = RawJobEntry(source_name="ycombinator", source_type=SourceType.JOB_BOARD,
                       raw_title="SWE", raw_company="Stripe", raw_location="SF",
                       source_url="url2", source_id="2")
    changed = job.merge_from_source(raw2)
    assert changed
    assert "ycombinator" in job.source_ids

def test_source_record_success():
    s = JobSource(name="test", source_type=SourceType.JOB_BOARD)
    s.record_success(jobs_found=50, duration_ms=3000)
    assert s.consecutive_fails == 0
    assert s.health_status == SourceHealth.HEALTHY
    assert s.jobs_per_sweep_avg == 50.0

def test_source_record_failure():
    s = JobSource(name="test", source_type=SourceType.JOB_BOARD)
    s.record_failure("timeout")
    s.record_failure("timeout")
    s.record_failure("timeout")
    assert s.consecutive_fails == 3
    assert s.health_status == SourceHealth.FAILING
```

### `tests/integration/api/test_jobs_api.py`

```python
import pytest
from httpx import ASGITransport, AsyncClient
from pathfinder.shared.infrastructure.main import create_app

pytestmark = pytest.mark.integration

@pytest.fixture
async def client_and_token():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/v1/auth/register", json={
            "email": "jobs-test@test.com", "password": "Test1234!",
            "full_name": "Jobs Tester", "accept_terms": True,
        })
        token = resp.json()["data"]["tokens"]["access_token"]
        yield c, token


async def test_search_jobs_empty_returns_ok(client_and_token):
    client, token = client_and_token
    resp = await client.get("/v1/jobs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "meta" in data


async def test_search_with_filters(client_and_token):
    client, token = client_and_token
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/v1/jobs?remote_policy=remote&limit=10", headers=headers)
    assert resp.status_code == 200


async def test_company_search(client_and_token):
    client, token = client_and_token
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/v1/companies?q=Stripe", headers=headers)
    assert resp.status_code == 200
```

---

## Sprint 4 Final File Inventory

```
src/pathfinder/jobs/
├── domain/
│   ├── entities.py           # JobPosting, Company, JobSource aggregates
│   ├── value_objects.py      # 10 value objects + 5 enums
│   ├── repositories.py       # 3 abstract repository interfaces
│   ├── services.py           # JobNormalizer, JobDedupService, JobEnrichmentService
│   ├── events.py
│   └── exceptions.py         # 5 domain exceptions
├── application/
│   ├── ports/
│   │   ├── job_source_port.py    # Pluggable JobSourcePort interface
│   │   └── web_search_port.py
│   ├── commands.py
│   ├── queries.py
│   └── handlers.py
├── infrastructure/
│   ├── persistence/
│   │   ├── models.py            # CompanyModel, JobPostingModel, JobSourceModel
│   │   ├── job_repository.py    # SqlJobRepository with search, similar, mark_stale
│   │   └── company_repository.py # SqlCompanyRepository with get_or_create
│   ├── scraping/
│   │   ├── base_scraper.py      # RateLimiter, HealthTracker, retry_with_backoff
│   │   ├── source_registry.py   # Global SourceRegistry
│   │   ├── greenhouse_scraper.py # 30+ company boards
│   │   ├── ycombinator_scraper.py # Paginated JSON API
│   │   └── hn_scraper.py        # Algolia search + HN API comment parser
│   └── enrichment/
│       └── llm_enricher.py      # Stub for Sprint 5
└── presentation/
    ├── router.py                # /jobs, /jobs/{id}, /jobs/{id}/similar, /companies
    ├── schemas.py
    └── dependencies.py

tests/unit/jobs/
├── test_value_objects.py       # 7 tests
├── test_normalizer.py          # 6 tests
├── test_entities.py            # 5 tests
└── test_dedup.py               # 3 tests

tests/integration/api/
└── test_jobs_api.py            # 3 tests

alembic/versions/
└── 003_seed_job_sources.py     # Initial source data

src/pathfinder/agent/infrastructure/celery_tasks/
└── scraping.py                 # sweep_all_sources, sweep_single_source, mark_stale_jobs
```

---

## Sprint 4 Gate Checklist

```
☐ 3 source adapters implemented (Greenhouse, YC, HN)
☐ Pluggable source framework: JobSourcePort ABC + SourceRegistry
☐ JobNormalizer: title standardization, remote inference, seniority inference
☐ JobDedupService: canonical ID matching, cross-source merge
☐ JobEnrichmentService: tech stack extraction, salary extraction (regex)
☐ SqlJobRepository: save, get_by_canonical_id, search (with filters), find_similar, mark_stale
☐ SqlCompanyRepository: get_or_create, search
☐ GET /v1/jobs → 200 (with filters: title, remote_policy, seniority, salary_min, source_type)
☐ GET /v1/jobs/{id} → 200 with embedded company
☐ GET /v1/jobs/{id}/similar → 200 (vector search)
☐ GET /v1/companies?q=X → 200
☐ GET /v1/companies/{id} → 200
☐ Celery tasks: sweep_all_sources, sweep_single_source, mark_stale_jobs
☐ Celery Beat schedule: hourly sweep, daily stale check
☐ Rate limiting per source (RateLimiter class)
☐ Health tracking per source (HealthTracker class)
☐ Retry with exponential backoff (retry_with_backoff)
☐ Migration 003 seeds 3 sources into job_sources table
☐ All unit tests pass (21+)
☐ All integration tests pass (3+)
☐ ruff check → 0 errors. mypy --strict → 0 errors
☐ Manual verification: trigger sweep → jobs appear in DB → search returns them
```

---

## Sprint 4 Completion Criteria

- [ ] 3 job source adapters operational and health-checked
- [ ] Pluggable framework: new source = implement JobSourcePort + register
- [ ] Jobs flow into DB via Celery sweeps (hourly)
- [ ] Dedup correctly merges identical jobs from multiple sources
- [ ] Search API handles all filter combinations < 300ms
- [ ] Similar jobs via vector search returns relevant results
- [ ] Source health monitoring tracks failures and degrades appropriately
- [ ] Stale jobs auto-expired after 30 days
- [ ] 24+ tests pass
- [ ] First sweep produces >500 jobs in DB

---

> *"Sprint 4: Jobs are the fuel. Without a steady flow of fresh, deduplicated, enriched jobs, nothing else matters. The source framework is built to scale — add a new source by implementing one interface."*

**End of Sprint 4**
