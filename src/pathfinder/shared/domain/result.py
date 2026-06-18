"""Result[T] monad for railway-oriented error handling."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, TypeVar, Callable

T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True)
class Result(Generic[T]):
    _value: T | None = None
    _error: Exception | None = None
    _is_success: bool = True

    @staticmethod
    def success(value: T) -> Result[T]:
        return Result(_value=value, _is_success=True)

    @staticmethod
    def failure(error: Exception) -> Result[T]:
        return Result(_error=error, _is_success=False)

    @property
    def is_success(self) -> bool:
        return self._is_success

    @property
    def is_failure(self) -> bool:
        return not self._is_success

    @property
    def value(self) -> T:
        if self.is_failure:
            raise ValueError(f"Cannot get value from failure: {self._error}")
        return self._value  # type: ignore[return-value]

    @property
    def error(self) -> Exception:
        if self.is_success:
            raise ValueError("Cannot get error from success")
        return self._error  # type: ignore[return-value]

    def map(self, fn: Callable[[T], U]) -> Result[U]:
        if self.is_failure:
            return Result.failure(self._error)  # type: ignore[return-value]
        return Result.success(fn(self._value))  # type: ignore[arg-type]

    def unwrap_or(self, default: T) -> T:
        return self._value if self.is_success else default  # type: ignore[return-value]
