"""Identity value objects and enums."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
import re
from pathfinder.shared.domain.base_value_object import BaseValueObject
from pathfinder.shared.domain.exceptions import ValidationError


class Tier(StrEnum):
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
    SUPPORT = "support"


@dataclass(frozen=True, kw_only=True)
class Email(BaseValueObject):
    value: str

    def __post_init__(self) -> None:
        if not self._is_valid(self.value):
            raise ValidationError(f"Invalid email: {self.value}", field="email")

    @staticmethod
    def _is_valid(email: str) -> bool:
        return bool(re.match(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email
        ))

    def __str__(self) -> str:
        return self.value
