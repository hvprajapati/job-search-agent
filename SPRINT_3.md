# Pathfinder — Sprint 3: Profile & Resume Domain

**Sprint:** 3 of 7
**Duration:** 10 Days
**Prerequisite:** Sprint 2 (infrastructure, auth, health)
**Goal:** Users upload resumes, get structured profiles with extracted skills, manage multiple resume variants. All profile data versioned and searchable.
**Source:** FINAL_ARCHITECTURE.md §7 + EPICS_AND_TASKS.md Epic 1

---

## Day 1–2: Domain Core

### Files to Create

```
src/pathfinder/profile/domain/
├── entities.py           # Profile, Resume, WorkExperience, Education, Skill
├── value_objects.py      # SkillProficiency, EmploymentDate, ResumeSection
├── repositories.py       # ProfileRepository, ResumeRepository (abstract)
├── services.py           # SkillExtractor, ProfileEnricher
├── events.py             # ProfileCreated, ProfileUpdated, ResumeCreated, etc.
└── exceptions.py         # ProfileNotFound, ResumeParsingError, etc.

tests/unit/profile/
├── test_profile_entity.py
├── test_resume_entity.py
├── test_skill_vo.py
└── test_domain_services.py
```

### `src/pathfinder/profile/domain/value_objects.py`

```python
"""Profile domain value objects and enums."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from pathfinder.shared.domain.base_value_object import BaseValueObject
from pathfinder.shared.domain.exceptions import ValidationError


class SkillProficiency(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SkillCategory(StrEnum):
    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    CLOUD = "cloud"
    TOOL = "tool"
    METHODOLOGY = "methodology"
    SOFT_SKILL = "soft_skill"
    DOMAIN = "domain"
    OTHER = "other"


class ResumeTemplate(StrEnum):
    MODERN_PROFESSIONAL = "modern_professional"
    CLASSIC = "classic"
    MINIMAL = "minimal"
    TECH_FOCUSED = "tech_focused"


@dataclass(frozen=True, kw_only=True)
class Skill(BaseValueObject):
    name: str
    proficiency: SkillProficiency = SkillProficiency.INTERMEDIATE
    years: float = 0.0
    category: SkillCategory = SkillCategory.OTHER
    last_used: str | None = None  # "YYYY-MM"
    sub_skills: tuple[str, ...] = field(default_factory=tuple)
    verified: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("Skill name cannot be empty", field="skill.name")
        if self.years < 0:
            raise ValidationError("Years cannot be negative", field="skill.years")


@dataclass(frozen=True, kw_only=True)
class WorkExperience(BaseValueObject):
    experience_id: str  # stable identifier
    company: str
    title: str
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    description: str = ""
    achievements: tuple[str, ...] = field(default_factory=tuple)
    tech_stack: tuple[str, ...] = field(default_factory=tuple)
    verified: bool = False

    def __post_init__(self) -> None:
        if not self.company.strip():
            raise ValidationError("Company name required", field="work_experience.company")
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date must be before end date", field="work_experience.dates")


@dataclass(frozen=True, kw_only=True)
class Education(BaseValueObject):
    education_id: str
    institution: str
    degree: str = ""
    field: str = ""
    graduation_year: int | None = None
    gpa: float | None = None
    verified: bool = False

    def __post_init__(self) -> None:
        if not self.institution.strip():
            raise ValidationError("Institution name required", field="education.institution")
        if self.graduation_year and (self.graduation_year < 1950 or self.graduation_year > 2035):
            raise ValidationError("Invalid graduation year", field="education.graduation_year")


@dataclass(frozen=True, kw_only=True)
class Project(BaseValueObject):
    project_id: str
    name: str
    description: str = ""
    url: str | None = None
    technologies: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, kw_only=True)
class ResumeSection(BaseValueObject):
    """A section within a resume (summary, experience, etc.)."""
    section_type: str  # "summary", "experience", "education", "skills", "projects"
    title: str
    content: list[dict]  # List of structured entries
    order: int = 0
```

### `src/pathfinder/profile/domain/entities.py`

```python
"""Profile domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import UUID, uuid4
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.shared.domain.identifiers import UserId, ResumeId
from pathfinder.profile.domain.value_objects import (
    Skill, WorkExperience, Education, Project,
    SkillProficiency, ResumeTemplate, ResumeSection,
)


@dataclass(kw_only=True)
class Profile(BaseEntity):
    user_id: UserId
    version: int = 1
    is_active: bool = True
    full_name: str = ""
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: dict | None = None  # {city, state, country}
    summary: str = ""
    work_experiences: list[WorkExperience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    certifications: list[dict] = field(default_factory=list)
    publications: list[dict] = field(default_factory=list)
    languages: list[dict] = field(default_factory=list)
    links: dict = field(default_factory=dict)
    parsing_confidence: dict = field(default_factory=dict)
    enrichment_data: dict = field(default_factory=dict)
    source: list[str] = field(default_factory=list)

    # ── Factory ──
    @classmethod
    def create_empty(cls, *, user_id: UserId) -> Profile:
        return cls(user_id=user_id)

    # ── Skill Management ──
    def add_skill(self, skill: Skill) -> None:
        existing = [s for s in self.skills if s.name.lower() == skill.name.lower()]
        if not existing:
            self.skills.append(skill)
            self.mark_updated()
            self._bump_version()

    def update_skill_proficiency(self, skill_name: str, proficiency: SkillProficiency) -> None:
        for s in self.skills:
            if s.name.lower() == skill_name.lower():
                updated = Skill(
                    name=s.name, proficiency=proficiency, years=s.years,
                    category=s.category, last_used=s.last_used,
                    sub_skills=s.sub_skills, verified=s.verified,
                )
                self.skills = [updated if x.name.lower() == skill_name.lower() else x for x in self.skills]
                self.mark_updated()
                self._bump_version()
                return

    def remove_skill(self, skill_name: str) -> None:
        self.skills = [s for s in self.skills if s.name.lower() != skill_name.lower()]
        self.mark_updated()
        self._bump_version()

    # ── Work Experience ──
    def add_work_experience(self, exp: WorkExperience) -> None:
        if exp.is_current:
            for e in self.work_experiences:
                if e.is_current:
                    # Only one current role — mark previous as not current
                    pass  # Handled by VO immutability; caller should update
        self.work_experiences.append(exp)
        self.mark_updated()
        self._bump_version()

    def remove_work_experience(self, experience_id: str) -> None:
        self.work_experiences = [e for e in self.work_experiences if e.experience_id != experience_id]
        self.mark_updated()
        self._bump_version()

    # ── Education ──
    def add_education(self, edu: Education) -> None:
        self.education.append(edu)
        self.mark_updated()
        self._bump_version()

    def remove_education(self, education_id: str) -> None:
        self.education = [e for e in self.education if e.education_id != education_id]
        self.mark_updated()
        self._bump_version()

    # ── Aggregate Methods ──
    def merge_from_parsed(self, parsed: ParsedProfileData, strategy: str = "merge") -> None:
        """Merge newly parsed data into existing profile."""
        if strategy == "replace":
            self.work_experiences = parsed.work_experiences
            self.education = parsed.education
            self.skills = parsed.skills
        else:  # merge: add new, skip duplicates
            existing_companies = {e.company.lower() for e in self.work_experiences}
            for exp in parsed.work_experiences:
                if exp.company.lower() not in existing_companies:
                    self.work_experiences.append(exp)
            existing_skills = {s.name.lower() for s in self.skills}
            for skill in parsed.skills:
                if skill.name.lower() not in existing_skills:
                    self.skills.append(skill)
        self.parsing_confidence = parsed.confidence
        self.mark_updated()
        self._bump_version()

    def _bump_version(self) -> None:
        self.version += 1


# Sentinel for passing parsed data before it's confirmed
@dataclass
class ParsedProfileData:
    full_name: str = ""
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: dict | None = None
    summary: str = ""
    work_experiences: list[WorkExperience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    certifications: list[dict] = field(default_factory=list)
    languages: list[dict] = field(default_factory=list)
    links: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)
    conflicts: list[dict] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class Resume(BaseEntity):
    user_id: UserId
    name: str
    description: str = ""
    template_id: str = ResumeTemplate.MODERN_PROFESSIONAL.value
    content: dict = field(default_factory=dict)  # Structured resume content
    file_url: str | None = None
    file_format: str = "pdf"
    is_base: bool = False
    tailored_for_job_id: UUID | None = None
    tailored_for_role: str | None = None
    performance_metrics: dict = field(default_factory=dict)
    ats_parse_score: int | None = None
    versions: list[dict] = field(default_factory=list)  # Edit history

    @classmethod
    def create_base(cls, *, user_id: UserId, name: str, template_id: str,
                    content: dict) -> Resume:
        return cls(
            user_id=user_id, name=name, template_id=template_id,
            content=content, is_base=True,
        )

    @classmethod
    def create_tailored(cls, *, user_id: UserId, name: str, job_id: UUID,
                        base_content: dict, tailored_content: dict) -> Resume:
        resume = cls(
            user_id=user_id, name=name, content=tailored_content,
            tailored_for_job_id=job_id,
        )
        resume.versions.append({"type": "base", "content": base_content})
        resume.versions.append({"type": "tailored", "content": tailored_content})
        return resume

    def update_content(self, new_content: dict) -> None:
        self.versions.append({"type": "edit", "content": self.content, "timestamp": datetime.now(timezone.utc).isoformat()})
        self.content = new_content
        self.mark_updated()

    @property
    def resume_id(self) -> ResumeId:
        return ResumeId(self.id)
```

### `src/pathfinder/profile/domain/exceptions.py`

```python
"""Profile domain exceptions."""
from pathfinder.shared.domain.exceptions import (
    DomainError, NotFoundError, ValidationError, ConflictError
)


class ProfileNotFoundError(NotFoundError):
    def __init__(self, user_id: str = "") -> None:
        super().__init__(f"Profile not found{' for user: ' + user_id if user_id else ''}")


class ResumeNotFoundError(NotFoundError):
    def __init__(self, resume_id: str = "") -> None:
        super().__init__(f"Resume not found{' : ' + resume_id if resume_id else ''}")


class ResumeParsingError(DomainError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Failed to parse resume: {detail}" if detail else "Failed to parse resume")


class ResumeInUseError(ConflictError):
    def __init__(self, count: int = 0) -> None:
        super().__init__(f"Cannot delete: resume linked to {count} active application(s). Withdraw or archive them first.")


class UnsupportedFileTypeError(ValidationError):
    def __init__(self, file_type: str = "") -> None:
        super().__init__(f"Unsupported file type{f': {file_type}' if file_type else ''}. Accepted: PDF, DOCX, TXT", field="file")


class FileTooLargeError(ValidationError):
    def __init__(self, max_mb: int = 10) -> None:
        super().__init__(f"File exceeds maximum size of {max_mb}MB", field="file")


class MaliciousFileError(ValidationError):
    def __init__(self) -> None:
        super().__init__("File failed security scan", field="file")


class ProfileMergeConflictError(DomainError):
    def __init__(self, conflicts: list[dict]) -> None:
        self.conflicts = conflicts
        super().__init__(f"Profile merge has {len(conflicts)} conflict(s) requiring resolution")
```

### `src/pathfinder/profile/domain/repositories.py`

```python
"""Profile domain repository interfaces (abstract)."""
from abc import abstractmethod
from uuid import UUID
from pathfinder.shared.domain.base_repository import BaseRepository
from pathfinder.profile.domain.entities import Profile, Resume


class ProfileRepository(BaseRepository[Profile]):
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Profile | None: ...
    @abstractmethod
    async def get_version(self, user_id: UUID, version: int) -> Profile | None: ...
    @abstractmethod
    async def list_versions(self, user_id: UUID) -> list[dict]: ...


class ResumeRepository(BaseRepository[Resume]):
    @abstractmethod
    async def list_by_user(self, user_id: UUID, *, is_base: bool | None = None,
                           tailored_for_job_id: UUID | None = None,
                           cursor: str | None = None, limit: int = 20) -> list[Resume]: ...
    @abstractmethod
    async def count_linked_applications(self, resume_id: UUID) -> int: ...
    @abstractmethod
    async def get_by_user_and_id(self, user_id: UUID, resume_id: UUID) -> Resume | None: ...
```

### `src/pathfinder/profile/domain/services.py`

```python
"""Profile domain services — pure business logic."""
from pathfinder.profile.domain.entities import Profile, ParsedProfileData
from pathfinder.profile.domain.value_objects import Skill, SkillProficiency


class SkillExtractor:
    """Extract and infer skills from parsed profile data."""

    KNOWN_SKILLS: dict[str, dict] = {
        "python": {"category": "programming_language", "typical_proficiency": "advanced"},
        "javascript": {"category": "programming_language", "typical_proficiency": "advanced"},
        "typescript": {"category": "programming_language", "typical_proficiency": "advanced"},
        "java": {"category": "programming_language", "typical_proficiency": "advanced"},
        "go": {"category": "programming_language", "typical_proficiency": "intermediate"},
        "rust": {"category": "programming_language", "typical_proficiency": "intermediate"},
        "sql": {"category": "database", "typical_proficiency": "advanced"},
        "postgresql": {"category": "database", "typical_proficiency": "advanced"},
        "react": {"category": "framework", "typical_proficiency": "advanced"},
        "fastapi": {"category": "framework", "typical_proficiency": "intermediate"},
        "docker": {"category": "tool", "typical_proficiency": "intermediate"},
        "kubernetes": {"category": "tool", "typical_proficiency": "intermediate"},
        "aws": {"category": "cloud", "typical_proficiency": "intermediate"},
        "gcp": {"category": "cloud", "typical_proficiency": "intermediate"},
    }

    @classmethod
    def infer_proficiency(cls, skill_name: str, years: float = 0.0) -> SkillProficiency:
        """Infer proficiency from years of experience."""
        if years >= 7:
            return SkillProficiency.EXPERT
        elif years >= 4:
            return SkillProficiency.ADVANCED
        elif years >= 1:
            return SkillProficiency.INTERMEDIATE
        return SkillProficiency.BEGINNER

    @classmethod
    def categorize(cls, skill_name: str) -> str:
        """Categorize a skill name."""
        key = skill_name.lower().strip()
        return cls.KNOWN_SKILLS.get(key, {}).get("category", "other")

    @classmethod
    def normalize(cls, skill_name: str) -> str:
        """Normalize skill name (e.g., 'Python3' → 'Python')."""
        mapping = {"python3": "Python", "js": "JavaScript", "ts": "TypeScript",
                   "golang": "Go", "pg": "PostgreSQL", "k8s": "Kubernetes"}
        return mapping.get(skill_name.lower().strip(), skill_name.strip().title())
```

### `src/pathfinder/profile/domain/events.py`

```python
"""Profile domain events."""
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID
from pathfinder.shared.domain.base_domain_event import BaseDomainEvent


@dataclass
class ProfileCreated(BaseDomainEvent):
    user_id: UUID
    profile_id: UUID

@dataclass
class ProfileUpdated(BaseDomainEvent):
    user_id: UUID
    profile_id: UUID
    version: int
    changed_fields: list[str]

@dataclass
class ResumeCreated(BaseDomainEvent):
    user_id: UUID
    resume_id: UUID
    is_base: bool

@dataclass
class ResumeTailored(BaseDomainEvent):
    user_id: UUID
    resume_id: UUID
    job_id: UUID
```

### Tests — Day 1–2

**`tests/unit/profile/test_skill_vo.py`:**
```python
import pytest
from pathfinder.profile.domain.value_objects import Skill, SkillProficiency, WorkExperience
from pathfinder.shared.domain.exceptions import ValidationError
from datetime import date

def test_skill_creation_with_defaults():
    s = Skill(name="Python")
    assert s.proficiency == SkillProficiency.INTERMEDIATE
    assert s.years == 0.0

def test_skill_empty_name_raises():
    with pytest.raises(ValidationError):
        Skill(name="")

def test_skill_negative_years_raises():
    with pytest.raises(ValidationError):
        Skill(name="Python", years=-1)

def test_work_experience_valid_dates():
    exp = WorkExperience(experience_id="1", company="Acme", title="Eng",
                         start_date=date(2020, 1, 1), end_date=date(2023, 1, 1))
    assert exp.company == "Acme"

def test_work_experience_invalid_dates_raises():
    with pytest.raises(ValidationError):
        WorkExperience(experience_id="1", company="Acme", title="Eng",
                       start_date=date(2023, 1, 1), end_date=date(2020, 1, 1))
```

**`tests/unit/profile/test_profile_entity.py`:**
```python
from pathfinder.profile.domain.entities import Profile
from pathfinder.profile.domain.value_objects import Skill, SkillProficiency
from pathfinder.shared.domain.identifiers import new_user_id

def test_create_empty_profile():
    uid = new_user_id()
    p = Profile.create_empty(user_id=uid)
    assert p.user_id == uid
    assert p.version == 1

def test_add_skill():
    p = Profile.create_empty(user_id=new_user_id())
    p.add_skill(Skill(name="Python", proficiency=SkillProficiency.EXPERT))
    assert len(p.skills) == 1
    assert p.skills[0].name == "Python"

def test_add_duplicate_skill_is_skipped():
    p = Profile.create_empty(user_id=new_user_id())
    p.add_skill(Skill(name="Python"))
    p.add_skill(Skill(name="python"))  # case-insensitive
    assert len(p.skills) == 1

def test_remove_skill():
    p = Profile.create_empty(user_id=new_user_id())
    p.add_skill(Skill(name="Python"))
    p.remove_skill("Python")
    assert len(p.skills) == 0

def test_version_bumps_on_change():
    p = Profile.create_empty(user_id=new_user_id())
    assert p.version == 1
    p.add_skill(Skill(name="Python"))
    assert p.version == 2
```

**`tests/unit/profile/test_resume_entity.py`:**
```python
from pathfinder.profile.domain.entities import Resume
from pathfinder.shared.domain.identifiers import new_user_id

def test_create_base_resume():
    r = Resume.create_base(user_id=new_user_id(), name="My Resume",
                           template_id="modern_professional", content={"summary": "..."})
    assert r.is_base is True
    assert r.name == "My Resume"

def test_resume_update_content_creates_version():
    r = Resume.create_base(user_id=new_user_id(), name="R", template_id="m", content={"v": 1})
    assert len(r.versions) == 0
    r.update_content({"v": 2})
    assert len(r.versions) == 1
    assert r.content == {"v": 2}
```

---

## Day 3–4: Infrastructure — Persistence

### Files to Create

```
src/pathfinder/profile/infrastructure/persistence/
├── models.py              # ProfileModel, ResumeModel, WorkExperienceModel, etc.
├── profile_repository.py  # SqlProfileRepository
└── resume_repository.py   # SqlResumeRepository

tests/integration/persistence/
├── test_profile_repository.py
└── test_resume_repository.py
```

### `src/pathfinder/profile/infrastructure/persistence/models.py`

```python
"""SQLAlchemy ORM models for profile domain."""
from __future__ import annotations
from datetime import date, datetime
from uuid import UUID
from sqlalchemy import String, Boolean, Integer, Float, Text, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin
from pathfinder.profile.domain.entities import Profile, Resume, ParsedProfileData
from pathfinder.profile.domain.value_objects import (
    Skill, SkillProficiency, SkillCategory, WorkExperience, Education,
    Project, ResumeTemplate,
)


class ProfileModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "profiles"

    tenant_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="CASCADE"),
                                           nullable=False, unique=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    structured_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(3072), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text)
    parsing_confidence: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    enrichment_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    source: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    # Pre-computed snapshot columns for fast queries
    full_name_snapshot: Mapped[str | None] = mapped_column(String(255))
    headline_snapshot: Mapped[str | None] = mapped_column(String(255))
    skill_names_snapshot: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    def to_domain(self) -> Profile:
        data = self.structured_data or {}
        return Profile(
            id=self.id,
            user_id=self.user_id,
            version=self.version,
            is_active=self.is_active,
            full_name=data.get("full_name", ""),
            headline=data.get("headline", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            location=data.get("location"),
            summary=data.get("summary", ""),
            work_experiences=[WorkExperience(**e) for e in data.get("work_experiences", [])],
            education=[Education(**e) for e in data.get("education", [])],
            skills=[Skill(**s) for s in data.get("skills", [])],
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
    def from_domain(cls, profile: Profile, tenant_id: UUID | None = None) -> ProfileModel:
        data = {
            "full_name": profile.full_name,
            "headline": profile.headline,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.location,
            "summary": profile.summary,
            "work_experiences": [
                {**e.__dict__} for e in profile.work_experiences
            ],
            "education": [{**e.__dict__} for e in profile.education],
            "skills": [{**s.__dict__} for s in profile.skills],
            "projects": [{**p.__dict__} for p in profile.projects],
            "certifications": profile.certifications,
            "publications": profile.publications,
            "languages": profile.languages,
            "links": profile.links,
        }
        return cls(
            id=profile.id,
            tenant_id=tenant_id or UUID("00000000-0000-0000-0000-000000000001"),
            user_id=profile.user_id,
            version=profile.version,
            is_active=profile.is_active,
            structured_data=data,
            embedding=None,  # Set separately after generation
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
    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    template_id: Mapped[str] = mapped_column(String(50), default="modern_professional")
    content: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    file_url: Mapped[str | None] = mapped_column(Text)
    file_format: Mapped[str] = mapped_column(String(10), default="pdf")
    is_base: Mapped[bool] = mapped_column(Boolean, default=False)
    tailored_for_job_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    tailored_for_role: Mapped[str | None] = mapped_column(String(255))
    performance_metrics: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    ats_parse_score: Mapped[int | None] = mapped_column(Integer)
    versions: Mapped[list[dict]] = mapped_column(JSONB, default=list, server_default="[]")

    def to_domain(self) -> Resume:
        return Resume(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            description=self.description or "",
            template_id=self.template_id,
            content=self.content or {},
            file_url=self.file_url,
            file_format=self.file_format,
            is_base=self.is_base,
            tailored_for_job_id=self.tailored_for_job_id,
            tailored_for_role=self.tailored_for_role,
            performance_metrics=self.performance_metrics or {},
            ats_parse_score=self.ats_parse_score,
            versions=self.versions or [],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, resume: Resume, tenant_id: UUID | None = None) -> ResumeModel:
        return cls(
            id=resume.id,
            tenant_id=tenant_id or UUID("00000000-0000-0000-0000-000000000001"),
            user_id=resume.user_id,
            name=resume.name,
            description=resume.description,
            template_id=resume.template_id,
            content=resume.content,
            file_url=resume.file_url,
            file_format=resume.file_format,
            is_base=resume.is_base,
            tailored_for_job_id=resume.tailored_for_job_id,
            tailored_for_role=resume.tailored_for_role,
            performance_metrics=resume.performance_metrics,
            ats_parse_score=resume.ats_parse_score,
            versions=resume.versions,
            created_at=resume.created_at,
            updated_at=resume.updated_at,
        )
```

### `src/pathfinder/profile/infrastructure/persistence/profile_repository.py`

```python
"""SQLAlchemy ProfileRepository implementation."""
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.profile.domain.entities import Profile
from pathfinder.profile.domain.repositories import ProfileRepository
from pathfinder.profile.infrastructure.persistence.models import ProfileModel


class SqlProfileRepository(ProfileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Profile | None:
        model = await self._session.get(ProfileModel, id)
        return model.to_domain() if model and model.is_active else None

    async def get_by_user_id(self, user_id: UUID) -> Profile | None:
        stmt = select(ProfileModel).where(
            ProfileModel.user_id == user_id,
            ProfileModel.is_active == True,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def save(self, entity: Profile) -> None:
        model = ProfileModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity: Profile) -> None:
        await self._session.execute(
            update(ProfileModel)
            .where(ProfileModel.id == entity.id)
            .values(is_active=False)
        )

    async def get_version(self, user_id: UUID, version: int) -> Profile | None:
        # Version history stored in a separate versions table (simplified: stored in JSONB)
        # For MVP, versions are stored as part of the profile update history
        stmt = select(ProfileModel).where(
            ProfileModel.user_id == user_id,
            ProfileModel.version == version,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def list_versions(self, user_id: UUID) -> list[dict]:
        # Simplified: return version numbers and timestamps
        stmt = select(ProfileModel.version, ProfileModel.updated_at).where(
            ProfileModel.user_id == user_id,
        ).order_by(ProfileModel.version.desc())
        result = await self._session.execute(stmt)
        return [{"version": row[0], "updated_at": row[1].isoformat()} for row in result]
```

### `src/pathfinder/profile/infrastructure/persistence/resume_repository.py`

```python
"""SQLAlchemy ResumeRepository implementation."""
from uuid import UUID
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.profile.domain.entities import Resume
from pathfinder.profile.domain.repositories import ResumeRepository
from pathfinder.profile.infrastructure.persistence.models import ResumeModel


class SqlResumeRepository(ResumeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Resume | None:
        model = await self._session.get(ResumeModel, id)
        return model.to_domain() if model else None

    async def get_by_user_and_id(self, user_id: UUID, resume_id: UUID) -> Resume | None:
        stmt = select(ResumeModel).where(
            ResumeModel.user_id == user_id,
            ResumeModel.id == resume_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def list_by_user(self, user_id: UUID, *, is_base: bool | None = None,
                           tailored_for_job_id: UUID | None = None,
                           cursor: str | None = None, limit: int = 20) -> list[Resume]:
        stmt = select(ResumeModel).where(ResumeModel.user_id == user_id)
        if is_base is not None:
            stmt = stmt.where(ResumeModel.is_base == is_base)
        if tailored_for_job_id is not None:
            stmt = stmt.where(ResumeModel.tailored_for_job_id == tailored_for_job_id)
        stmt = stmt.order_by(ResumeModel.updated_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [m.to_domain() for m in result.scalars()]

    async def save(self, entity: Resume) -> None:
        model = ResumeModel.from_domain(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity: Resume) -> None:
        model = await self._session.get(ResumeModel, entity.id)
        if model:
            await self._session.delete(model)

    async def count_linked_applications(self, resume_id: UUID) -> int:
        stmt = select(func.count()).select_from(text("applications")).where(
            text("resume_id = :rid AND status NOT IN ('rejected', 'withdrawn', 'accepted')")
        ).params(rid=resume_id)
        result = await self._session.execute(stmt)
        return result.scalar() or 0
```

---

## Day 5–6: Resume Parsing & LLM Integration

### Files to Create

```
src/pathfinder/profile/infrastructure/
├── llm/
│   ├── deepseek_client.py       # LLM client (if not already done in Sprint 2)
│   └── prompts/
│       └── resume_parsing.py    # Prompt templates
├── parsing/
│   ├── pdf_extractor.py         # PDF text extraction
│   ├── docx_extractor.py        # DOCX text extraction
│   └── resume_parser.py         # Orchestrator: extract → prompt → LLM → parse
└── rendering/
    └── pdf_renderer.py          # HTML → PDF resume rendering

src/pathfinder/profile/application/
├── ports/
│   ├── llm_port.py              # LLMPort abstract
│   └── embedding_port.py        # EmbeddingPort abstract
├── commands.py                  # ImportResume, CreateProfile, UpdateProfile, etc.
├── queries.py                   # GetProfile, GetResume, etc.
└── handlers.py                  # ProfileCommandHandler
```

### `src/pathfinder/profile/application/ports/llm_port.py`

```python
"""Abstract LLM port for profile operations."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    tokens_used: int
    model: str
    latency_ms: int


class LLMPort(ABC):
    @abstractmethod
    async def chat_completion(
        self, *, system_prompt: str, user_prompt: str,
        response_schema: dict | None = None,
        temperature: float = 0.3,
    ) -> LLMResponse: ...

    @abstractmethod
    async def generate_embedding(self, text: str) -> list[float]: ...
```

### `src/pathfinder/profile/infrastructure/llm/deepseek_client.py`

```python
"""DeepSeek API adapter implementing LLMPort."""
import json
import time
import httpx
from pathfinder.shared.config import get_settings
from pathfinder.profile.application.ports.llm_port import LLMPort, LLMResponse


class DeepSeekClient(LLMPort):
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.deepseek_api_key
        self._base_url = settings.deepseek_base_url
        self._model = settings.deepseek_model
        self._timeout = settings.deepseek_timeout_seconds
        self._client = httpx.AsyncClient(timeout=self._timeout)

    async def chat_completion(self, *, system_prompt: str, user_prompt: str,
                              response_schema: dict | None = None,
                              temperature: float = 0.3) -> LLMResponse:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        body = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }
        if response_schema:
            body["response_format"] = {"type": "json_object", "schema": response_schema}

        start = time.monotonic()
        resp = await self._client.post(
            f"{self._base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        latency_ms = int((time.monotonic() - start) * 1000)

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            tokens_used=data["usage"]["total_tokens"],
            model=data["model"],
            latency_ms=latency_ms,
        )

    async def generate_embedding(self, text: str) -> list[float]:
        resp = await self._client.post(
            f"{self._base_url}/v1/embeddings",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": "deepseek-embed", "input": text},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]

    async def close(self) -> None:
        await self._client.aclose()
```

### `src/pathfinder/profile/infrastructure/llm/prompts/resume_parsing.py`

```python
"""Resume parsing prompt templates."""

SYSTEM_PROMPT = """You are a resume parsing engine. Your job is to extract structured information from raw resume text.

CRITICAL RULES:
1. Extract ONLY what is explicitly stated in the resume. NEVER fabricate or infer information.
2. If a field is not present in the resume, use null or empty value.
3. For skills, list each skill separately with a confidence score (0.0-1.0).
4. For dates, use YYYY-MM format. If only year is given, use YYYY-01.
5. Identify the proficiency level of each skill based on context clues (years used, projects, certifications).
6. Flag any sections where you have low confidence in extraction.

OUTPUT: Valid JSON matching the schema provided."""

USER_PROMPT_TEMPLATE = """Parse the following resume text into structured JSON.

<user_data>
{resume_text}
</user_data>

The text above is a resume. Extract all available information into the required schema format.
Do not include any text outside the JSON object."""

EXPECTED_SCHEMA = {
    "type": "object",
    "properties": {
        "full_name": {"type": "string"},
        "headline": {"type": "string"},
        "email": {"type": "string"},
        "phone": {"type": "string"},
        "location": {
            "type": "object",
            "properties": {"city": {"type": "string"}, "state": {"type": "string"}, "country": {"type": "string"}}
        },
        "summary": {"type": "string"},
        "work_experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "experience_id": {"type": "string"},
                    "company": {"type": "string"},
                    "title": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "is_current": {"type": "boolean"},
                    "description": {"type": "string"},
                    "achievements": {"type": "array", "items": {"type": "string"}},
                    "tech_stack": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["experience_id", "company", "title"]
            }
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "education_id": {"type": "string"},
                    "institution": {"type": "string"},
                    "degree": {"type": "string"},
                    "field": {"type": "string"},
                    "graduation_year": {"type": "integer"},
                }
            }
        },
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "years": {"type": "number"},
                    "confidence": {"type": "number"},
                }
            }
        },
        "projects": {"type": "array"},
        "certifications": {"type": "array"},
        "languages": {"type": "array"},
        "links": {"type": "object"},
    }
}
```

### `src/pathfinder/profile/infrastructure/parsing/pdf_extractor.py`

```python
"""PDF text extraction."""
from io import BytesIO
import PyPDF2


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract raw text from a PDF file. Returns empty string on failure."""
    try:
        reader = PyPDF2.PdfReader(BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except Exception:
        return ""
```

### `src/pathfinder/profile/infrastructure/parsing/docx_extractor.py`

```python
"""DOCX text extraction."""
from io import BytesIO
from docx import Document


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract raw text from a DOCX file."""
    try:
        doc = Document(BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""
```

### `src/pathfinder/profile/infrastructure/parsing/resume_parser.py`

```python
"""Resume parsing orchestrator."""
import json
import uuid
from io import BytesIO
from pathfinder.shared.domain.result import Result
from pathfinder.profile.domain.entities import ParsedProfileData
from pathfinder.profile.domain.value_objects import (
    Skill, SkillProficiency, WorkExperience, Education, Project,
)
from pathfinder.profile.domain.services import SkillExtractor
from pathfinder.profile.domain.exceptions import ResumeParsingError
from pathfinder.profile.application.ports.llm_port import LLMPort
from pathfinder.profile.infrastructure.parsing.pdf_extractor import extract_text_from_pdf
from pathfinder.profile.infrastructure.parsing.docx_extractor import extract_text_from_docx
from pathfinder.profile.infrastructure.llm.prompts.resume_parsing import (
    SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, EXPECTED_SCHEMA
)


class ResumeParser:
    """Parses resume files (PDF/DOCX/TXT) into structured profile data using LLM."""

    SUPPORTED_TYPES = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "txt",
    }

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def parse(self, file_bytes: bytes, content_type: str) -> Result[ParsedProfileData]:
        # 1. Extract text
        ext = self.SUPPORTED_TYPES.get(content_type)
        if ext is None:
            return Result.failure(ResumeParsingError(f"Unsupported type: {content_type}"))

        raw_text = self._extract_text(file_bytes, ext)
        if not raw_text or len(raw_text.strip()) < 50:
            return Result.failure(ResumeParsingError("Could not extract meaningful text from file"))

        # 2. LLM parsing
        try:
            response = await self._llm.chat_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT_TEMPLATE.format(resume_text=raw_text),
                response_schema=EXPECTED_SCHEMA,
                temperature=0.1,
            )
            raw_json = json.loads(response.content)
        except json.JSONDecodeError as e:
            return Result.failure(ResumeParsingError(f"LLM returned invalid JSON: {e}"))
        except Exception as e:
            return Result.failure(ResumeParsingError(str(e)))

        # 3. Map to domain objects
        parsed = self._map_to_domain(raw_json)
        return Result.success(parsed)

    def _extract_text(self, file_bytes: bytes, ext: str) -> str:
        if ext == "pdf":
            return extract_text_from_pdf(file_bytes)
        elif ext == "docx":
            return extract_text_from_docx(file_bytes)
        else:
            return file_bytes.decode("utf-8", errors="ignore")

    def _map_to_domain(self, raw: dict) -> ParsedProfileData:
        return ParsedProfileData(
            full_name=raw.get("full_name", ""),
            headline=raw.get("headline", ""),
            email=raw.get("email", ""),
            phone=raw.get("phone", ""),
            location=raw.get("location"),
            summary=raw.get("summary", ""),
            work_experiences=[
                WorkExperience(
                    experience_id=e.get("experience_id", str(uuid.uuid4())),
                    company=e.get("company", ""),
                    title=e.get("title", ""),
                    start_date=self._parse_date(e.get("start_date")),
                    end_date=self._parse_date(e.get("end_date")) if e.get("end_date") else None,
                    is_current=e.get("is_current", False),
                    description=e.get("description", ""),
                    achievements=tuple(e.get("achievements", [])),
                    tech_stack=tuple(e.get("tech_stack", [])),
                ) for e in raw.get("work_experiences", [])
            ],
            education=[
                Education(
                    education_id=e.get("education_id", str(uuid.uuid4())),
                    institution=e.get("institution", ""),
                    degree=e.get("degree", ""),
                    field=e.get("field", ""),
                    graduation_year=e.get("graduation_year"),
                ) for e in raw.get("education", [])
            ],
            skills=[
                Skill(
                    name=SkillExtractor.normalize(s.get("name", "")),
                    proficiency=SkillExtractor.infer_proficiency(
                        s.get("name", ""), s.get("years", 0.0)
                    ),
                    years=s.get("years", 0.0),
                    category=SkillExtractor.categorize(s.get("name", "")),
                ) for s in raw.get("skills", [])
            ],
            projects=[
                Project(
                    project_id=p.get("project_id", str(uuid.uuid4())),
                    name=p.get("name", ""),
                    description=p.get("description", ""),
                    url=p.get("url"),
                    technologies=tuple(p.get("technologies", [])),
                ) for p in raw.get("projects", [])
            ],
            certifications=raw.get("certifications", []),
            languages=raw.get("languages", []),
            links=raw.get("links", {}),
            confidence=self._compute_confidence(raw),
        )

    def _parse_date(self, date_str: str | None) -> date:
        if not date_str:
            from datetime import date
            return date(1900, 1, 1)
        try:
            from datetime import date
            if "-" in date_str:
                parts = date_str.split("-")
                return date(int(parts[0]), int(parts[1]) if len(parts) > 1 else 1, 1)
            return date(int(date_str), 1, 1)
        except Exception:
            from datetime import date
            return date(1900, 1, 1)

    def _compute_confidence(self, raw: dict) -> dict:
        conf = {}
        conf["full_name"] = 0.95 if raw.get("full_name") else 0.0
        conf["email"] = 0.90 if raw.get("email") and "@" in raw.get("email", "") else 0.0
        conf["work_experiences"] = 0.85 if raw.get("work_experiences") else 0.0
        conf["education"] = 0.85 if raw.get("education") else 0.0
        conf["skills"] = 0.80 if raw.get("skills") else 0.0
        return conf
```

---

## Day 7–8: Application Layer + API

### Files to Create

```
src/pathfinder/profile/application/
├── commands.py     # Command DTOs
├── queries.py      # Query DTOs
└── handlers.py     # ProfileCommandHandler, ResumeCommandHandler

src/pathfinder/profile/presentation/
├── schemas.py
├── dependencies.py
└── router.py

tests/integration/api/
├── test_profile_api.py
└── test_resume_api.py
```

### `src/pathfinder/profile/application/commands.py`

```python
from dataclasses import dataclass
from uuid import UUID

@dataclass
class ImportResumeCommand:
    user_id: UUID
    file_bytes: bytes
    content_type: str
    merge_strategy: str = "merge"

@dataclass
class ConfirmParsedProfileCommand:
    user_id: UUID
    parsed_data: dict
    resolved_conflicts: dict = None  # noqa: RUF009

@dataclass
class UpdateProfileCommand:
    user_id: UUID
    full_name: str | None = None
    headline: str | None = None
    email: str | None = None
    phone: str | None = None
    location: dict | None = None
    summary: str | None = None

@dataclass
class CreateResumeCommand:
    user_id: UUID
    name: str
    template_id: str
    content: dict
    is_base: bool = True

@dataclass
class UpdateResumeCommand:
    resume_id: UUID
    user_id: UUID
    name: str | None = None
    content: dict | None = None
```

### `src/pathfinder/profile/application/handlers.py`

```python
"""Profile and Resume command handlers."""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.domain.result import Result
from pathfinder.profile.domain.entities import Profile, Resume, ParsedProfileData
from pathfinder.profile.domain.repositories import ProfileRepository, ResumeRepository
from pathfinder.profile.domain.exceptions import (
    ProfileNotFoundError, ResumeNotFoundError, ResumeParsingError,
    ResumeInUseError, ProfileMergeConflictError,
)
from pathfinder.profile.application.ports.llm_port import LLMPort
from pathfinder.profile.application.commands import (
    ImportResumeCommand, ConfirmParsedProfileCommand,
    UpdateProfileCommand, CreateResumeCommand, UpdateResumeCommand,
)
from pathfinder.profile.infrastructure.parsing.resume_parser import ResumeParser


class ProfileCommandHandler:
    def __init__(self, profile_repo: ProfileRepository,
                 resume_repo: ResumeRepository,
                 llm: LLMPort, session: AsyncSession) -> None:
        self._profiles = profile_repo
        self._resumes = resume_repo
        self._llm = llm
        self._session = session
        self._parser = ResumeParser(llm)

    async def import_resume(self, cmd: ImportResumeCommand) -> Result[dict]:
        """Parse resume file, return extracted data for user review."""
        result = await self._parser.parse(cmd.file_bytes, cmd.content_type)
        if result.is_failure:
            return result  # type: ignore

        parsed: ParsedProfileData = result.value

        # Check for conflicts with existing profile
        existing = await self._profiles.get_by_user_id(cmd.user_id)
        conflicts = []
        if existing and cmd.merge_strategy == "merge":
            conflicts = self._detect_conflicts(existing, parsed)

        return Result.success({
            "parsed": self._parsed_to_dict(parsed),
            "confidence": parsed.confidence,
            "conflicts": conflicts,
            "missing_fields": parsed.missing_fields,
        })

    async def confirm_parsed(self, cmd: ConfirmParsedProfileCommand) -> Result[Profile]:
        """Apply confirmed parsed data to user's profile."""
        existing = await self._profiles.get_by_user_id(cmd.user_id)
        if existing:
            parsed = self._dict_to_parsed(cmd.parsed_data)
            existing.merge_from_parsed(parsed, strategy="merge")
            await self._profiles.save(existing)
            return Result.success(existing)
        else:
            parsed = self._dict_to_parsed(cmd.parsed_data)
            profile = Profile.create_empty(user_id=cmd.user_id)
            profile.merge_from_parsed(parsed, strategy="replace")
            await self._profiles.save(profile)
            return Result.success(profile)

    async def update_profile(self, cmd: UpdateProfileCommand) -> Result[Profile]:
        profile = await self._profiles.get_by_user_id(cmd.user_id)
        if not profile:
            return Result.failure(ProfileNotFoundError(str(cmd.user_id)))
        if cmd.full_name is not None:
            profile.full_name = cmd.full_name
        if cmd.headline is not None:
            profile.headline = cmd.headline
        if cmd.email is not None:
            profile.email = cmd.email
        if cmd.phone is not None:
            profile.phone = cmd.phone
        if cmd.location is not None:
            profile.location = cmd.location
        if cmd.summary is not None:
            profile.summary = cmd.summary
        profile.mark_updated()
        profile._bump_version()
        await self._profiles.save(profile)
        return Result.success(profile)

    # ── Resume Operations ──

    async def create_resume(self, cmd: CreateResumeCommand) -> Result[Resume]:
        resume = Resume.create_base(
            user_id=cmd.user_id, name=cmd.name,
            template_id=cmd.template_id, content=cmd.content,
        )
        await self._resumes.save(resume)
        return Result.success(resume)

    async def update_resume(self, cmd: UpdateResumeCommand) -> Result[Resume]:
        resume = await self._resumes.get_by_user_and_id(cmd.user_id, cmd.resume_id)
        if not resume:
            return Result.failure(ResumeNotFoundError(str(cmd.resume_id)))
        if cmd.name is not None:
            resume.name = cmd.name
        if cmd.content is not None:
            resume.update_content(cmd.content)
        await self._resumes.save(resume)
        return Result.success(resume)

    async def delete_resume(self, resume_id: UUID, user_id: UUID) -> Result[None]:
        resume = await self._resumes.get_by_user_and_id(user_id, resume_id)
        if not resume:
            return Result.failure(ResumeNotFoundError(str(resume_id)))
        linked = await self._resumes.count_linked_applications(resume_id)
        if linked > 0:
            return Result.failure(ResumeInUseError(linked))
        await self._resumes.delete(resume)
        return Result.success(None)

    # ── Helpers ──

    def _detect_conflicts(self, existing: Profile, parsed: ParsedProfileData) -> list[dict]:
        conflicts = []
        existing_companies = {(e.company.lower(), e.title.lower()) for e in existing.work_experiences}
        for exp in parsed.work_experiences:
            key = (exp.company.lower(), exp.title.lower())
            if key in existing_companies:
                conflicts.append({
                    "field": "work_experiences",
                    "entity": f"{exp.title} at {exp.company}",
                    "existing": "present in profile",
                    "parsed": "present in resume",
                    "suggestion": "merge" if exp.description else "skip",
                })
        return conflicts

    @staticmethod
    def _parsed_to_dict(p: ParsedProfileData) -> dict:
        return {
            "full_name": p.full_name, "headline": p.headline, "email": p.email,
            "phone": p.phone, "location": p.location, "summary": p.summary,
            "work_experiences": [{**e.__dict__} for e in p.work_experiences],
            "education": [{**e.__dict__} for e in p.education],
            "skills": [{**s.__dict__} for s in p.skills],
            "projects": [{**pr.__dict__} for pr in p.projects],
            "certifications": p.certifications,
            "languages": p.languages, "links": p.links,
        }

    @staticmethod
    def _dict_to_parsed(d: dict) -> ParsedProfileData:
        from pathfinder.profile.domain.value_objects import (
            Skill, WorkExperience, Education, Project,
        )
        return ParsedProfileData(
            full_name=d.get("full_name", ""),
            headline=d.get("headline", ""),
            email=d.get("email", ""),
            phone=d.get("phone", ""),
            location=d.get("location"),
            summary=d.get("summary", ""),
            work_experiences=[WorkExperience(**e) for e in d.get("work_experiences", [])],
            education=[Education(**e) for e in d.get("education", [])],
            skills=[Skill(**s) for s in d.get("skills", [])],
            projects=[Project(**p) for p in d.get("projects", [])],
            certifications=d.get("certifications", []),
            languages=d.get("languages", []),
            links=d.get("links", {}),
        )
```

### `src/pathfinder/profile/presentation/schemas.py`

```python
"""Pydantic API schemas for profile domain."""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date

class ProfileResponse(BaseModel):
    profile_id: UUID
    user_id: UUID
    version: int
    full_name: str = ""
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: dict | None = None
    summary: str = ""
    work_experiences: list[dict] = []
    education: list[dict] = []
    skills: list[dict] = []
    projects: list[dict] = []
    certifications: list[dict] = []
    languages: list[dict] = []
    links: dict = {}
    parsing_confidence: dict = {}
    created_at: str = ""
    updated_at: str = ""

class ImportResumeResponse(BaseModel):
    parsed: dict
    confidence: dict
    conflicts: list[dict] = []
    missing_fields: list[str] = []

class ConfirmImportRequest(BaseModel):
    parsed_data: dict
    resolve_conflicts: dict = {}

class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    headline: str | None = None
    email: str | None = None
    phone: str | None = None
    location: dict | None = None
    summary: str | None = None

class CreateResumeRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    template_id: str = "modern_professional"
    content: dict

class UpdateResumeRequest(BaseModel):
    name: str | None = None
    content: dict | None = None

class ResumeResponse(BaseModel):
    resume_id: UUID
    user_id: UUID
    name: str
    description: str = ""
    template_id: str = ""
    is_base: bool = False
    tailored_for_job_id: UUID | None = None
    tailored_for_role: str | None = None
    file_format: str = "pdf"
    ats_parse_score: int | None = None
    created_at: str = ""
    updated_at: str = ""

class ResumeListResponse(BaseModel):
    data: list[ResumeResponse]
    meta: dict  # cursor, count, limit

class ResumeDetailResponse(BaseModel):
    data: dict  # Full resume with content

class TemplateResponse(BaseModel):
    template_id: str
    name: str
    description: str
    preview_url: str = ""
    ats_score: int = 90
    tier_required: str = "free"
```

### `src/pathfinder/profile/presentation/dependencies.py`

```python
"""FastAPI dependency wiring for profile domain."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.profile.domain.repositories import ProfileRepository, ResumeRepository
from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
from pathfinder.profile.infrastructure.persistence.resume_repository import SqlResumeRepository
from pathfinder.profile.application.handlers import ProfileCommandHandler
from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient


async def get_profile_repository(
    session: AsyncSession = Depends(get_session),
) -> ProfileRepository:
    return SqlProfileRepository(session)


async def get_resume_repository(
    session: AsyncSession = Depends(get_session),
) -> ResumeRepository:
    return SqlResumeRepository(session)


async def get_profile_handler(
    session: AsyncSession = Depends(get_session),
) -> ProfileCommandHandler:
    profile_repo = SqlProfileRepository(session)
    resume_repo = SqlResumeRepository(session)
    llm = DeepSeekClient()
    return ProfileCommandHandler(profile_repo, resume_repo, llm, session)
```

### `src/pathfinder/profile/presentation/router.py`

```python
"""Profile and Resume API routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Form, Request, Response
from fastapi.responses import StreamingResponse
import io
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User
from pathfinder.profile.application.commands import (
    ImportResumeCommand, ConfirmParsedProfileCommand,
    UpdateProfileCommand, CreateResumeCommand, UpdateResumeCommand,
)
from pathfinder.profile.application.handlers import ProfileCommandHandler
from pathfinder.profile.presentation.schemas import (
    ProfileResponse, ImportResumeResponse, ConfirmImportRequest,
    UpdateProfileRequest, CreateResumeRequest, UpdateResumeRequest,
    ResumeResponse, ResumeListResponse, ResumeDetailResponse, TemplateResponse,
)
from pathfinder.profile.presentation.dependencies import (
    get_profile_repository, get_resume_repository, get_profile_handler,
)
from pathfinder.profile.domain.entities import Profile, Resume
from pathfinder.profile.domain.repositories import ProfileRepository, ResumeRepository
from pathfinder.profile.domain.value_objects import ResumeTemplate
from pathfinder.profile.domain.exceptions import (
    UnsupportedFileTypeError, FileTooLargeError,
)

router = APIRouter(prefix="/v1", tags=["Profile & Resumes"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {
    "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


# ── Queries ──

@router.get("/profile", response_model=dict)
async def get_profile(
    current_user: User = Depends(get_current_user),
    repo: ProfileRepository = Depends(get_profile_repository),
):
    profile = await repo.get_by_user_id(current_user.id)
    if not profile:
        from pathfinder.profile.domain.exceptions import ProfileNotFoundError
        raise ProfileNotFoundError(str(current_user.id))
    return {"data": _profile_to_response(profile)}


@router.get("/profile/versions", response_model=dict)
async def get_profile_versions(
    current_user: User = Depends(get_current_user),
    repo: ProfileRepository = Depends(get_profile_repository),
):
    versions = await repo.list_versions(current_user.id)
    return {"data": versions}


# ── Profile Commands ──

@router.put("/profile", response_model=dict)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    handler: ProfileCommandHandler = Depends(get_profile_handler),
):
    cmd = UpdateProfileCommand(
        user_id=current_user.id,
        full_name=body.full_name, headline=body.headline,
        email=body.email, phone=body.phone,
        location=body.location, summary=body.summary,
    )
    result = await handler.update_profile(cmd)
    if result.is_failure:
        raise result.error
    return {"data": _profile_to_response(result.value)}


# ── Resume Import ──

@router.post("/profile/import/resume", response_model=dict)
async def import_resume(
    file: UploadFile = File(...),
    merge_strategy: str = Form("merge"),
    current_user: User = Depends(get_current_user),
    handler: ProfileCommandHandler = Depends(get_profile_handler),
):
    if file.content_type not in ALLOWED_TYPES:
        raise UnsupportedFileTypeError(file.content_type or "unknown")
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise FileTooLargeError()

    cmd = ImportResumeCommand(
        user_id=current_user.id, file_bytes=file_bytes,
        content_type=file.content_type, merge_strategy=merge_strategy,
    )
    result = await handler.import_resume(cmd)
    if result.is_failure:
        raise result.error
    return {"data": result.value}


@router.post("/profile/import/resume/confirm", response_model=dict)
async def confirm_import(
    body: ConfirmImportRequest,
    current_user: User = Depends(get_current_user),
    handler: ProfileCommandHandler = Depends(get_profile_handler),
):
    cmd = ConfirmParsedProfileCommand(
        user_id=current_user.id,
        parsed_data=body.parsed_data,
        resolved_conflicts=body.resolve_conflicts,
    )
    result = await handler.confirm_parsed(cmd)
    if result.is_failure:
        raise result.error
    return {"data": _profile_to_response(result.value)}


# ── Resumes ──

@router.get("/resumes", response_model=dict)
async def list_resumes(
    is_base: bool | None = None,
    current_user: User = Depends(get_current_user),
    repo: ResumeRepository = Depends(get_resume_repository),
):
    resumes = await repo.list_by_user(current_user.id, is_base=is_base, limit=50)
    return {
        "data": [_resume_to_response(r) for r in resumes],
        "meta": {"count": len(resumes), "limit": 50},
    }


@router.post("/resumes", status_code=201, response_model=dict)
async def create_resume(
    body: CreateResumeRequest,
    current_user: User = Depends(get_current_user),
    handler: ProfileCommandHandler = Depends(get_profile_handler),
):
    cmd = CreateResumeCommand(
        user_id=current_user.id, name=body.name,
        template_id=body.template_id, content=body.content, is_base=True,
    )
    result = await handler.create_resume(cmd)
    if result.is_failure:
        raise result.error
    return {"data": _resume_to_response(result.value)}


@router.get("/resumes/{resume_id}", response_model=dict)
async def get_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    repo: ResumeRepository = Depends(get_resume_repository),
):
    resume = await repo.get_by_user_and_id(current_user.id, resume_id)
    if not resume:
        from pathfinder.profile.domain.exceptions import ResumeNotFoundError
        raise ResumeNotFoundError(str(resume_id))
    return {"data": {"resume": _resume_to_response(resume), "content": resume.content}}


@router.put("/resumes/{resume_id}", response_model=dict)
async def update_resume(
    resume_id: UUID,
    body: UpdateResumeRequest,
    current_user: User = Depends(get_current_user),
    handler: ProfileCommandHandler = Depends(get_profile_handler),
):
    cmd = UpdateResumeCommand(
        resume_id=resume_id, user_id=current_user.id,
        name=body.name, content=body.content,
    )
    result = await handler.update_resume(cmd)
    if result.is_failure:
        raise result.error
    return {"data": _resume_to_response(result.value)}


@router.delete("/resumes/{resume_id}", status_code=204)
async def delete_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    handler: ProfileCommandHandler = Depends(get_profile_handler),
):
    result = await handler.delete_resume(resume_id, current_user.id)
    if result.is_failure:
        raise result.error
    return Response(status_code=204)


@router.get("/resumes/templates", response_model=dict)
async def list_templates():
    templates = [
        {"template_id": "modern_professional", "name": "Modern Professional",
         "description": "Clean, modern layout. Best for tech roles.", "ats_score": 94, "tier_required": "free"},
        {"template_id": "classic", "name": "Classic",
         "description": "Traditional format. Best for enterprise roles.", "ats_score": 96, "tier_required": "free"},
        {"template_id": "minimal", "name": "Minimal",
         "description": "Clean and simple. Highlights content.", "ats_score": 90, "tier_required": "free"},
        {"template_id": "tech_focused", "name": "Tech Focused",
         "description": "Skills-first layout. Best for IC roles.", "ats_score": 88, "tier_required": "pro"},
    ]
    return {"data": templates}


@router.get("/resumes/{resume_id}/download")
async def download_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    repo: ResumeRepository = Depends(get_resume_repository),
):
    resume = await repo.get_by_user_and_id(current_user.id, resume_id)
    if not resume:
        from pathfinder.profile.domain.exceptions import ResumeNotFoundError
        raise ResumeNotFoundError(str(resume_id))
    # Simplified PDF generation for Sprint 3
    content_str = str(resume.content)
    pdf_bytes = content_str.encode()  # Real implementation uses WeasyPrint
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{resume.name}.pdf"'},
    )


# ── Helpers ──

def _profile_to_response(p: Profile) -> dict:
    return {
        "profile_id": str(p.id), "user_id": str(p.user_id), "version": p.version,
        "full_name": p.full_name, "headline": p.headline, "email": p.email,
        "phone": p.phone, "location": p.location, "summary": p.summary,
        "work_experiences": [{**e.__dict__} for e in p.work_experiences],
        "education": [{**e.__dict__} for e in p.education],
        "skills": [{**s.__dict__} for s in p.skills],
        "projects": [{**pr.__dict__} for pr in p.projects],
        "certifications": p.certifications, "languages": p.languages,
        "links": p.links, "parsing_confidence": p.parsing_confidence,
        "created_at": p.created_at.isoformat(), "updated_at": p.updated_at.isoformat(),
    }


def _resume_to_response(r: Resume) -> dict:
    return {
        "resume_id": str(r.id), "user_id": str(r.user_id),
        "name": r.name, "description": r.description,
        "template_id": r.template_id, "is_base": r.is_base,
        "tailored_for_job_id": str(r.tailored_for_job_id) if r.tailored_for_job_id else None,
        "tailored_for_role": r.tailored_for_role,
        "file_format": r.file_format,
        "ats_parse_score": r.ats_parse_score,
        "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat(),
    }
```

### `src/pathfinder/shared/infrastructure/main.py` — Update

Add the profile router to the FastAPI app:

```python
# Add this import
from pathfinder.profile.presentation.router import router as profile_router

# Add this line after auth_router in create_app()
app.include_router(profile_router)
```

---

## Day 9: Integration Tests

### `tests/integration/api/test_profile_api.py`

```python
import pytest
from httpx import ASGITransport, AsyncClient
from pathfinder.shared.infrastructure.main import create_app
from tests.conftest import create_test_user_and_token  # helper fixture

pytestmark = pytest.mark.integration

@pytest.fixture
async def client_and_token():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Register + login to get token
        resp = await c.post("/v1/auth/register", json={
            "email": "profile-test@example.com", "password": "Test1234!",
            "full_name": "Profile Tester", "accept_terms": True,
        })
        token = resp.json()["data"]["tokens"]["access_token"]
        yield c, token


async def test_get_empty_profile_returns_404(client_and_token):
    client, token = client_and_token
    resp = await client.get("/v1/profile", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


async def test_update_profile_creates_and_returns(client_and_token):
    client, token = client_and_token
    headers = {"Authorization": f"Bearer {token}"}
    # First update creates the profile implicitly (via confirm_import path)
    # For Sprint 3, PUT requires existing profile. Use import flow first.
    # This test verifies the API contract works.
    resp = await client.put("/v1/profile", headers=headers, json={
        "full_name": "Updated Name", "headline": "Senior Engineer",
    })
    # Profile doesn't exist yet → 404
    assert resp.status_code == 404


async def test_resume_crud_flow(client_and_token):
    client, token = client_and_token
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    resp = await client.post("/v1/resumes", headers=headers, json={
        "name": "My Base Resume", "template_id": "modern_professional",
        "content": {"summary": "Experienced engineer..."},
    })
    assert resp.status_code == 201
    resume_id = resp.json()["data"]["resume_id"]

    # List
    resp = await client.get("/v1/resumes", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1

    # Get detail
    resp = await client.get(f"/v1/resumes/{resume_id}", headers=headers)
    assert resp.status_code == 200
    assert "content" in resp.json()["data"]

    # Update
    resp = await client.put(f"/v1/resumes/{resume_id}", headers=headers, json={
        "name": "Updated Resume Name",
    })
    assert resp.status_code == 200

    # Delete
    resp = await client.delete(f"/v1/resumes/{resume_id}", headers=headers)
    assert resp.status_code == 204


async def test_template_list(client_and_token):
    client, token = client_and_token
    resp = await client.get("/v1/resumes/templates", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 3
```

---

## Day 10: Review, Polish, Gate

### Gate Checklist

```
☐ Profile entity: create, add skills, add work experience, version bump
☐ Resume entity: create base, update content, version history
☐ Skill value object: validation, proficiency inference
☐ ResumeParser: extracts text from PDF, returns ParsedProfileData
☐ DeepSeekClient: chat_completion with schema, embedding generation
☐ SqlProfileRepository: CRUD against real PostgreSQL
☐ SqlResumeRepository: CRUD against real PostgreSQL
☐ POST /v1/profile/import/resume → 200 with parsed data
☐ POST /v1/profile/import/resume/confirm → 200 with saved profile
☐ GET /v1/profile → 200 with structured profile
☐ PUT /v1/profile → 200 with updated profile
☐ GET /v1/resumes → 200 with resume list
☐ POST /v1/resumes → 201
☐ GET /v1/resumes/{id} → 200 with content
☐ PUT /v1/resumes/{id} → 200
☐ DELETE /v1/resumes/{id} → 204 (or 409 if linked)
☐ GET /v1/resumes/templates → 200
☐ GET /v1/resumes/{id}/download → 200
☐ Unsupported file type → 400
☐ File too large → 400
☐ All unit tests pass (15+)
☐ All integration tests pass (12+)
☐ ruff check → 0 errors
☐ mypy --strict → 0 errors
```

### Sprint 3 Completion Criteria
- [ ] Users can upload resume files (PDF/DOCX/TXT)
- [ ] Resume parsed into structured profile by LLM
- [ ] Profile stored with versioning, skills, work history, education
- [ ] Resume CRUD: create, list, view, update, delete
- [ ] Resume templates available
- [ ] PDF download works
- [ ] File validation: size limit, type check, virus scan placeholder
- [ ] 27+ tests pass
- [ ] Profile domain is the data foundation for all subsequent features

---

> *"Sprint 3: The profile is the product. Everything else — matching, tailoring, coaching — is just different ways to look at the profile data. Get this right."*

**End of Sprint 3**
