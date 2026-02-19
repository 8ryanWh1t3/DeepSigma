"""Tests for MCP adapter resilience primitives — retry and circuit breaker."""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.mcp.resilience import (
    BreakerState,
    CircuitBreaker,
    CircuitOpen,
    TransientError,
    is_transient,
    retry,
)


# ── is_transient ─────────────────────────────────────────────────


class TestIsTransient:
    def test_transient_error_class(self):
        assert is_transient(TransientError("boom"))

    def test_429_in_message(self):
        assert is_transient(RuntimeError("HTTP 429 Too Many Requests"))

    def test_502_in_message(self):
        assert is_transient(RuntimeError("502 Bad Gateway"))

    def test_503_in_message(self):
        assert is_transient(RuntimeError("503 Service Unavailable"))

    def test_timeout_in_message(self):
        assert is_transient(RuntimeError("Connection timeout after 30s"))

    def test_connection_reset(self):
        assert is_transient(ConnectionError("Connection reset by peer"))

    def test_rate_limit(self):
        assert is_transient(RuntimeError("rate limit exceeded"))

    def test_non_transient(self):
        assert not is_transient(ValueError("invalid input"))

    def test_non_transient_key_error(self):
        assert not is_transient(KeyError("missing_key"))


# ── retry ────────────────────────────────────────────────────────


class TestRetry:
    def test_succeeds_first_try(self):
        fn = MagicMock(return_value=42)
        decorated = retry(max_attempts=3, base_delay=0.01)(fn)
        assert decorated() == 42
        assert fn.call_count == 1

    def test_retries_on_transient_then_succeeds(self):
        fn = MagicMock(side_effect=[TransientError("fail"), TransientError("fail"), 42])
        decorated = retry(max_attempts=3, base_delay=0.01)(fn)
        assert decorated() == 42
        assert fn.call_count == 3

    def test_raises_after_max_attempts(self):
        fn = MagicMock(side_effect=TransientError("persistent failure"))
        decorated = retry(max_attempts=3, base_delay=0.01)(fn)
        try:
            decorated()
            assert False, "Should have raised"
        except TransientError as exc:
            assert "persistent failure" in str(exc)
        assert fn.call_count == 3

    def test_non_transient_raises_immediately(self):
        fn = MagicMock(side_effect=ValueError("bad input"))
        decorated = retry(max_attempts=3, base_delay=0.01)(fn)
        try:
            decorated()
            assert False, "Should have raised"
        except ValueError:
            pass
        assert fn.call_count == 1

    def test_passes_args_through(self):
        fn = MagicMock(return_value="ok")
        decorated = retry(max_attempts=2, base_delay=0.01)(fn)
        result = decorated("a", b="c")
        assert result == "ok"
        fn.assert_called_once_with("a", b="c")

    def test_respects_custom_transient_check(self):
        fn = MagicMock(side_effect=[KeyError("miss"), "ok"])
        decorated = retry(
            max_attempts=3,
            base_delay=0.01,
            transient=lambda e: isinstance(e, KeyError),
        )(fn)
        assert decorated() == "ok"
        assert fn.call_count == 2


# ── CircuitBreaker ───────────────────────────────────────────────


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker(name="test", threshold=3, cooldown=1.0)
        assert cb.state == BreakerState.CLOSED
        assert cb.allow_request()

    def test_trips_after_threshold(self):
        cb = CircuitBreaker(name="test", threshold=3, cooldown=60.0)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == BreakerState.OPEN
        assert not cb.allow_request()

    def test_does_not_trip_below_threshold(self):
        cb = CircuitBreaker(name="test", threshold=3, cooldown=60.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == BreakerState.CLOSED
        assert cb.allow_request()

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(name="test", threshold=3, cooldown=60.0)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        # Two more failures should not trip (count was reset)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == BreakerState.CLOSED

    def test_transitions_to_half_open_after_cooldown(self):
        cb = CircuitBreaker(name="test", threshold=1, cooldown=0.05)
        cb.record_failure()
        assert cb.state == BreakerState.OPEN
        time.sleep(0.1)
        assert cb.state == BreakerState.HALF_OPEN
        assert cb.allow_request()

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(name="test", threshold=1, cooldown=0.05)
        cb.record_failure()
        time.sleep(0.1)
        assert cb.state == BreakerState.HALF_OPEN
        cb.record_success()
        assert cb.state == BreakerState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(name="test", threshold=1, cooldown=0.05)
        cb.record_failure()
        time.sleep(0.1)
        assert cb.state == BreakerState.HALF_OPEN
        cb.record_failure()
        assert cb.state == BreakerState.OPEN

    def test_context_manager_success(self):
        cb = CircuitBreaker(name="test", threshold=3, cooldown=60.0)
        with cb():
            pass
        assert cb.stats["success_count"] == 1

    def test_context_manager_failure(self):
        cb = CircuitBreaker(name="test", threshold=3, cooldown=60.0)
        try:
            with cb():
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert cb.stats["failure_count"] == 1

    def test_context_manager_raises_circuit_open(self):
        cb = CircuitBreaker(name="test", threshold=1, cooldown=60.0)
        cb.record_failure()
        assert cb.state == BreakerState.OPEN
        try:
            with cb():
                pass
            assert False, "Should have raised CircuitOpen"
        except CircuitOpen as exc:
            assert "test" in str(exc)
            assert exc.name == "test"

    def test_reset(self):
        cb = CircuitBreaker(name="test", threshold=1, cooldown=60.0)
        cb.record_failure()
        assert cb.state == BreakerState.OPEN
        cb.reset()
        assert cb.state == BreakerState.CLOSED
        assert cb.allow_request()

    def test_stats(self):
        cb = CircuitBreaker(name="test", threshold=2, cooldown=60.0)
        cb.record_success()
        cb.record_failure()
        cb.record_failure()
        stats = cb.stats
        assert stats["name"] == "test"
        assert stats["state"] == "open"
        assert stats["success_count"] == 1
        assert stats["failure_count"] == 2
        assert stats["total_trips"] == 1

    def test_total_trips_increments(self):
        cb = CircuitBreaker(name="test", threshold=1, cooldown=0.05)
        # Trip 1
        cb.record_failure()
        assert cb.stats["total_trips"] == 1
        # Wait for half-open, then succeed to close
        time.sleep(0.15)
        # Force state check so half-open transition occurs
        assert cb.state == BreakerState.HALF_OPEN
        cb.record_success()
        assert cb.state == BreakerState.CLOSED
        # Trip 2
        cb.record_failure()
        assert cb.stats["total_trips"] == 2
