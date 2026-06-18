"""Identity domain exceptions."""
from pathfinder.shared.domain.exceptions import (
    ConflictError, UnauthorizedError, ValidationError,
)


class InvalidCredentialsError(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class EmailAlreadyExistsError(ConflictError):
    def __init__(self, email: str) -> None:
        super().__init__(f"Email already registered: {email}")


class WeakPasswordError(ValidationError):
    def __init__(self) -> None:
        super().__init__(
            "Password must be at least 8 characters with uppercase, lowercase, and a number",
            field="password",
        )
