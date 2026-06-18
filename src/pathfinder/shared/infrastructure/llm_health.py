"""DeepSeek health checker with circuit breaker and graceful degradation."""
from __future__ import annotations
import time
import logging
from enum import StrEnum

logger = logging.getLogger(__name__)


class LLMStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class DeepSeekHealthChecker:
    """Tracks DeepSeek API health with circuit breaker pattern."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._consecutive_failures: int = 0
        self._total_failures: int = 0
        self._total_successes: int = 0
        self._last_failure_time: float = 0.0
        self._circuit_open: bool = False
        self._circuit_opened_at: float = 0.0

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._total_successes += 1
        if self._circuit_open and (time.monotonic() - self._circuit_opened_at) > self._recovery_timeout:
            self._circuit_open = False
            logger.info("Circuit breaker closed — LLM recovered")

    def record_failure(self, error: str = "") -> None:
        self._consecutive_failures += 1
        self._total_failures += 1
        self._last_failure_time = time.monotonic()
        if self._consecutive_failures >= self._failure_threshold and not self._circuit_open:
            self._circuit_open = True
            self._circuit_opened_at = time.monotonic()
            logger.warning(f"Circuit breaker OPEN after {self._consecutive_failures} consecutive LLM failures")

    @property
    def status(self) -> LLMStatus:
        if self._circuit_open:
            if (time.monotonic() - self._circuit_opened_at) > self._recovery_timeout:
                return LLMStatus.DEGRADED
            return LLMStatus.UNAVAILABLE
        if self._consecutive_failures > 0:
            return LLMStatus.DEGRADED
        return LLMStatus.HEALTHY

    @property
    def is_available(self) -> bool:
        return self.status != LLMStatus.UNAVAILABLE

    @property
    def metrics(self) -> dict:
        return {
            "status": self.status.value,
            "circuit_open": self._circuit_open,
            "consecutive_failures": self._consecutive_failures,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "failure_rate": (
                self._total_failures / max(self._total_failures + self._total_successes, 1)
            ),
        }


# Global singleton
llm_health = DeepSeekHealthChecker(failure_threshold=5, recovery_timeout=30.0)
