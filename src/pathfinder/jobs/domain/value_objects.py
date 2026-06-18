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
    UNSPECIFIED = "unspecified"


class SourceType(StrEnum):
    JOB_BOARD = "job_board"
    CAREER_PAGE = "career_page"
    COMMUNITY = "community"
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
    source: str = "unlisted"
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.min_amount is not None and self.max_amount is not None:
            if self.min_amount > self.max_amount:
                raise ValidationError("min must be <= max", field="salary")

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
    display_text: str = ""


@dataclass(frozen=True, kw_only=True)
class CanonicalJobId(BaseValueObject):
    value: str

    @staticmethod
    def compute(*, title: str, company_name: str, location: str = "") -> CanonicalJobId:
        key = f"{title.strip().lower()}|{company_name.strip().lower()}|{location.strip().lower()}"
        return CanonicalJobId(value=hashlib.sha256(key.encode()).hexdigest()[:16])


@dataclass(frozen=True, kw_only=True)
class RawJobEntry(BaseValueObject):
    source_name: str
    source_type: SourceType
    raw_title: str
    raw_company: str
    raw_location: str = ""
    raw_description: str = ""
    source_url: str = ""
    application_url: str = ""
    source_id: str = ""
    raw_metadata: dict = field(default_factory=dict)
    discovered_at: str = ""
