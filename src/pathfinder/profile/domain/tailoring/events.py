"""Tailoring domain events."""
from dataclasses import dataclass
from uuid import UUID
from pathfinder.shared.domain.base_domain_event import BaseDomainEvent


@dataclass
class ResumeTailored(BaseDomainEvent):
    user_id: UUID
    tailored_resume_id: UUID
    job_id: UUID
    base_resume_id: UUID


@dataclass
class TailoringAccepted(BaseDomainEvent):
    user_id: UUID
    tailored_resume_id: UUID
