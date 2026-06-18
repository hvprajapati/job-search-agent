"""Tests for LLM health checker and graceful degradation."""
import pytest
from pathfinder.shared.infrastructure.llm_health import DeepSeekHealthChecker, LLMStatus


class TestDeepSeekHealthChecker:
    def test_initial_status_is_healthy(self):
        hc = DeepSeekHealthChecker()
        assert hc.status == LLMStatus.HEALTHY
        assert hc.is_available is True

    def test_single_failure_sets_degraded(self):
        hc = DeepSeekHealthChecker(failure_threshold=3)
        hc.record_failure("timeout")
        assert hc.status == LLMStatus.DEGRADED
        assert hc.is_available is True

    def test_threshold_failures_opens_circuit(self):
        hc = DeepSeekHealthChecker(failure_threshold=3)
        for _ in range(3):
            hc.record_failure("error")
        assert hc.status == LLMStatus.UNAVAILABLE
        assert hc.is_available is False

    def test_success_resets_consecutive_failures(self):
        hc = DeepSeekHealthChecker(failure_threshold=5)
        hc.record_failure("e1")
        hc.record_failure("e2")
        hc.record_success()
        assert hc._consecutive_failures == 0
        assert hc.status == LLMStatus.HEALTHY

    def test_metrics_include_failure_rate(self):
        hc = DeepSeekHealthChecker()
        hc.record_success()
        hc.record_success()
        hc.record_failure("e")
        m = hc.metrics
        assert m["total_successes"] == 2
        assert m["total_failures"] == 1
        assert 0.3 < m["failure_rate"] < 0.35

    def test_circuit_opens_after_recovery_timeout(self):
        hc = DeepSeekHealthChecker(failure_threshold=2, recovery_timeout=0.01)
        for _ in range(2):
            hc.record_failure("e")
        assert hc.status == LLMStatus.UNAVAILABLE
        import time
        time.sleep(0.02)
        assert hc.status == LLMStatus.DEGRADED  # Recovery window passed, but still degraded until success

    def test_record_success_closes_circuit(self):
        hc = DeepSeekHealthChecker(failure_threshold=2, recovery_timeout=0.01)
        for _ in range(2):
            hc.record_failure("e")
        assert hc.status == LLMStatus.UNAVAILABLE
        import time
        time.sleep(0.02)
        hc.record_success()
        assert hc.status == LLMStatus.HEALTHY
