"""Immutable value object base."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class BaseValueObject:
    """Value objects are immutable and compared by value, not identity."""

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))
