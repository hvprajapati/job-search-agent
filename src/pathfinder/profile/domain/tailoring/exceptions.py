"""Tailoring domain exceptions."""
from pathfinder.shared.domain.exceptions import NotFoundError, DomainError


class TailoringError(DomainError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Resume tailoring failed: {detail}")


class BaseResumeNotFoundError(NotFoundError):
    def __init__(self, resume_id: str = "") -> None:
        super().__init__(f"Base resume not found: {resume_id}")


class TailoredResumeNotFoundError(NotFoundError):
    def __init__(self, tailored_id: str = "") -> None:
        super().__init__(f"Tailored resume not found: {tailored_id}")
