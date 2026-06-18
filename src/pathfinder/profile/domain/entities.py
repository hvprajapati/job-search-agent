"""Profile domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.shared.domain.identifiers import UserId, ResumeId
from pathfinder.profile.domain.value_objects import (
    Skill, WorkExperience, Education, Project,
)


@dataclass(kw_only=True)
class Profile(BaseEntity):
    user_id: UUID
    version: int = 1
    is_active: bool = True
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
    publications: list[dict] = field(default_factory=list)
    languages: list[dict] = field(default_factory=list)
    links: dict = field(default_factory=dict)
    parsing_confidence: dict = field(default_factory=dict)
    enrichment_data: dict = field(default_factory=dict)
    source: list[str] = field(default_factory=list)

    @classmethod
    def create_empty(cls, *, user_id: UUID) -> Profile:
        return cls(user_id=user_id)

    def add_skill(self, skill: Skill) -> None:
        existing_names = {s.name.lower() for s in self.skills}
        if skill.name.lower() not in existing_names:
            self.skills.append(skill)
            self._bump()

    def remove_skill(self, skill_name: str) -> None:
        self.skills = [s for s in self.skills if s.name.lower() != skill_name.lower()]
        self._bump()

    def add_work_experience(self, exp: WorkExperience) -> None:
        self.work_experiences.append(exp)
        self._bump()

    def add_education(self, edu: Education) -> None:
        self.education.append(edu)
        self._bump()

    def _bump(self) -> None:
        self.version += 1
        self.mark_updated()


@dataclass(kw_only=True)
class Resume(BaseEntity):
    user_id: UUID
    name: str
    description: str = ""
    template_id: str = "modern_professional"
    content: dict = field(default_factory=dict)
    file_url: str | None = None
    file_format: str = "pdf"
    is_base: bool = False
    tailored_for_job_id: UUID | None = None
    tailored_for_role: str | None = None
    performance_metrics: dict = field(default_factory=dict)
    ats_parse_score: int | None = None
    versions: list[dict] = field(default_factory=list)

    @classmethod
    def create_base(cls, *, user_id: UUID, name: str, template_id: str,
                    content: dict) -> Resume:
        return cls(user_id=user_id, name=name, template_id=template_id,
                   content=content, is_base=True)

    def update_content(self, new_content: dict) -> None:
        self.versions.append({
            "type": "edit", "content": self.content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.content = new_content
        self.mark_updated()

    @property
    def resume_id(self) -> ResumeId:
        return ResumeId(self.id)
