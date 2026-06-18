"""Profile domain exceptions."""
from pathfinder.shared.domain.exceptions import NotFoundError, DomainError, ConflictError


class ProfileNotFoundError(NotFoundError):
    def __init__(self, user_id: str = "") -> None:
        super().__init__(f"Profile not found{' for user: ' + user_id if user_id else ''}")


class ResumeNotFoundError(NotFoundError):
    def __init__(self, resume_id: str = "") -> None:
        super().__init__(f"Resume not found{' : ' + resume_id if resume_id else ''}")


class ResumeParsingError(DomainError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Failed to parse resume: {detail}" if detail else "Failed to parse resume")
