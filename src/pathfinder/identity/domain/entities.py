"""Identity domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.shared.domain.identifiers import UserId
from pathfinder.identity.domain.value_objects import Email, Tier, UserStatus, UserRole


@dataclass(kw_only=True)
class User(BaseEntity):
    email: Email
    hashed_password: str | None = None
    full_name: str = ""
    tier: Tier = Tier.FREE
    status: UserStatus = UserStatus.ACTIVE
    role: UserRole = UserRole.USER
    email_verified: bool = False
    oauth_provider: str | None = None
    oauth_subject: str | None = None
    avatar_url: str | None = None
    locale: str = "en-US"
    timezone: str = "UTC"
    last_login_at: datetime | None = None
    deleted_at: datetime | None = None

    @classmethod
    def register(cls, *, email: str, full_name: str) -> User:
        email_vo = Email(value=email.strip().lower())
        return cls(email=email_vo, full_name=full_name.strip())

    def verify_email(self) -> None:
        self.email_verified = True
        self.mark_updated()

    def upgrade_tier(self, new_tier: Tier) -> None:
        if new_tier != self.tier:
            self.tier = new_tier
            self.mark_updated()

    def deactivate(self) -> None:
        self.status = UserStatus.INACTIVE
        self.mark_updated()

    def record_login(self) -> None:
        self.last_login_at = datetime.now(timezone.utc)
        self.mark_updated()

    def set_password_hash(self, hashed: str) -> None:
        self.hashed_password = hashed
        self.mark_updated()

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE and self.deleted_at is None

    @property
    def user_id(self) -> UserId:
        return UserId(self.id)
