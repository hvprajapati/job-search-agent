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


@dataclass(frozen=True, kw_only=True)
class Skill(BaseValueObject):
    name: str
    proficiency: SkillProficiency = SkillProficiency.INTERMEDIATE
    years: float = 0.0
    category: SkillCategory = SkillCategory.OTHER
    last_used: str | None = None
    sub_skills: tuple[str, ...] = field(default_factory=tuple)
    verified: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("Skill name cannot be empty", field="skill.name")


@dataclass(frozen=True, kw_only=True)
class WorkExperience(BaseValueObject):
    experience_id: str
    company: str
    title: str
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str = ""
    achievements: tuple[str, ...] = field(default_factory=tuple)
    tech_stack: tuple[str, ...] = field(default_factory=tuple)
    verified: bool = False

    def __post_init__(self) -> None:
        if not self.company.strip():
            raise ValidationError("Company name required", field="work_experience.company")


@dataclass(frozen=True, kw_only=True)
class Education(BaseValueObject):
    education_id: str
    institution: str
    degree: str = ""
    field: str = ""
    graduation_year: int | None = None
    verified: bool = False


@dataclass(frozen=True, kw_only=True)
class Project(BaseValueObject):
    project_id: str
    name: str
    description: str = ""
    url: str | None = None
    technologies: tuple[str, ...] = field(default_factory=tuple)
