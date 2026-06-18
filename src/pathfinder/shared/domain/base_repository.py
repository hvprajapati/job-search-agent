"""Generic abstract repository."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID
from pathfinder.shared.domain.base_entity import BaseEntity

T = TypeVar("T", bound=BaseEntity)


class BaseRepository(ABC, Generic[T]):
    """Abstract repository. Domain defines what; infrastructure implements how."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> T | None: ...

    @abstractmethod
    async def save(self, entity: T) -> None: ...

    @abstractmethod
    async def delete(self, entity: T) -> None: ...
