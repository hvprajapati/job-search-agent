"""Domain exception hierarchy."""


class DomainError(Exception):
    """Base for all domain exceptions."""

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code or type(self).__name__
        super().__init__(message)


class NotFoundError(DomainError):
    """Entity not found -> 404."""
    pass


class ValidationError(DomainError):
    """Business rule violation -> 422."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class ConflictError(DomainError):
    """Duplicate or conflict -> 409."""
    pass


class UnauthorizedError(DomainError):
    """Authentication required -> 401."""
    pass


class ForbiddenError(DomainError):
    """Permission denied -> 403."""
    pass
