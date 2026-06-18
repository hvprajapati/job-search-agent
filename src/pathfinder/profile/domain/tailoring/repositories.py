"""Tailoring repository interfaces."""
from abc import abstractmethod
from uuid import UUID
from pathfinder.shared.domain.base_repository import BaseRepository
from pathfinder.profile.domain.tailoring.entities import TailoredResume


class TailoredResumeRepository(BaseRepository[TailoredResume]):
    @abstractmethod
    async def get_latest_for_job(self, user_id: UUID, job_id: UUID) -> TailoredResume | None: ...
    @abstractmethod
    async def list_by_user(self, user_id: UUID, *, job_id: UUID | None = None,
                           limit: int = 20) -> list[TailoredResume]: ...
    @abstractmethod
    async def list_versions(self, base_resume_id: UUID, job_id: UUID) -> list[TailoredResume]: ...
    @abstractmethod
    async def get_by_user_and_id(self, user_id: UUID, tailored_id: UUID) -> TailoredResume | None: ...
