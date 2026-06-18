"""Job domain repository interfaces."""
from abc import abstractmethod
from uuid import UUID
from pathfinder.shared.domain.base_repository import BaseRepository
from pathfinder.jobs.domain.entities import JobPosting, Company


class JobRepository(BaseRepository[JobPosting]):
    @abstractmethod
    async def get_by_canonical_id(self, canonical_id: str) -> JobPosting | None: ...
    @abstractmethod
    async def search(self, *, query: str | None = None, filters: dict | None = None,
                     sort: str = "-first_seen_at", limit: int = 20,
                     ) -> tuple[list[JobPosting], str | None, int]: ...
    @abstractmethod
    async def list_active(self, *, limit: int = 100) -> list[JobPosting]: ...
    @abstractmethod
    async def mark_stale_jobs(self, older_than_days: int = 30) -> int: ...


class CompanyRepository(BaseRepository[Company]):
    @abstractmethod
    async def get_by_canonical_name(self, canonical_name: str) -> Company | None: ...
    @abstractmethod
    async def search(self, *, query: str | None = None, limit: int = 20) -> list[Company]: ...
    @abstractmethod
    async def get_or_create(self, name: str) -> Company: ...
