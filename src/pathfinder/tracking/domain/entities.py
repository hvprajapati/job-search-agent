"""Tracking domain entities — Application, Interview, Offer."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.shared.domain.identifiers import ApplicationId


class ApplicationStatus:
    SAVED = "saved"
    APPLIED = "applied"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL_INTERVIEW = "technical_interview"
    ONSITE = "onsite"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

    VALID_TRANSITIONS = {
        SAVED: [APPLIED, WITHDRAWN],
        APPLIED: [PHONE_SCREEN, TECHNICAL_INTERVIEW, ONSITE, REJECTED, WITHDRAWN],
        PHONE_SCREEN: [TECHNICAL_INTERVIEW, ONSITE, REJECTED, WITHDRAWN],
        TECHNICAL_INTERVIEW: [ONSITE, OFFER, REJECTED, WITHDRAWN],
        ONSITE: [OFFER, REJECTED, WITHDRAWN],
        OFFER: [ACCEPTED, REJECTED, WITHDRAWN],
        ACCEPTED: [],
        REJECTED: [],
        WITHDRAWN: [],
    }


@dataclass(kw_only=True)
class Application(BaseEntity):
    user_id: UUID
    job_id: UUID
    resume_id: UUID | None = None
    cover_letter_id: UUID | None = None
    status: str = ApplicationStatus.SAVED
    status_history: list[dict] = field(default_factory=list)
    source_channel: str = ""
    match_score: float | None = None
    notes: str = ""
    applied_at: datetime | None = None
    next_follow_up_at: datetime | None = None
    is_archived: bool = False

    def transition(self, new_status: str) -> None:
        valid = ApplicationStatus.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in valid:
            raise ValueError(f"Cannot transition from '{self.status}' to '{new_status}'")
        self.status_history.append({"from": self.status, "to": new_status, "at": datetime.now(timezone.utc).isoformat()})
        self.status = new_status
        if new_status == ApplicationStatus.APPLIED:
            self.applied_at = datetime.now(timezone.utc)
        self.mark_updated()

    @property
    def is_active(self) -> bool:
        return self.status not in (ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN)

    @property
    def application_id(self) -> ApplicationId:
        return ApplicationId(self.id)


@dataclass(kw_only=True)
class Interview(BaseEntity):
    application_id: UUID
    stage: str = ""
    scheduled_at: datetime | None = None
    duration_minutes: int = 60
    interviewer_name: str = ""
    interviewer_role: str = ""
    location: str = ""
    meeting_link: str = ""
    status: str = "scheduled"
    notes: str = ""
    feedback: dict = field(default_factory=dict)
    outcome: str = ""


@dataclass(kw_only=True)
class Offer(BaseEntity):
    application_id: UUID
    compensation: dict = field(default_factory=dict)
    status: str = "pending"
    expires_at: datetime | None = None
    negotiated: bool = False
