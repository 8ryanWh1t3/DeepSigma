"""Retry and circuit-breaker primitives for MCP tool calls.

Stdlib only — no external dependencies.

Usage::

    breaker = CircuitBreaker(name="sharepoint", threshold=3, cooldown=60)

    @retry(max_attempts=3, transient=is_transient)
    def call_sharepoint():
        with breaker:
            return connector.list_items(list_id)
"""

from __future__ import annotations

import random
import threading
import time
from contextlib import contextmanager
from enum import Enum
from functools import wraps
from typing import Any, Callable, Iterator, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


# ── Transient error detection ────────────────────────────────────

class TransientError(Exception):
    """Wraps an error identified as transient (retriable)."""

    def __init__(self, message: str, original: Exception | None = None):
        super().__init__(message)
        self.original = original


def is_transient(exc: Exception) -> bool:
    """Return True if *exc* looks like a transient failure worth retrying."""
    if isinstance(exc, TransientError):
        return True
    msg = str(exc).lower()
    # Common transient patterns from HTTP connectors
    for signal in ("429", "502", "503", "504", "timeout", "connection reset",
                   "temporary failure", "service unavailable", "rate limit"):
        if signal in msg:
            return True
    return False


# ── Retry decorator ──────────────────────────────────────────────

def retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    transient: Callable[[Exception], bool] = is_transient,
) -> Callable[[F], F]:
    """Exponential-backoff retry decorator with jitter.

    Only retries exceptions for which *transient(exc)* returns True.
    Non-transient exceptions propagate immediately.
    """

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if not transient(exc) or attempt == max_attempts:
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    jitter = random.uniform(0, delay * 0.5)  # noqa: S311
                    time.sleep(delay + jitter)
            raise last_exc  # pragma: no cover — unreachable but satisfies type checker

        return wrapper  # type: ignore[return-value]

    return decorator


# ── Circuit breaker ──────────────────────────────────────────────

class BreakerState(Enum):
    CLOSED = "closed"       # Normal — requests flow through
    OPEN = "open"           # Tripped — requests rejected immediately
    HALF_OPEN = "half_open" # Probing — one request allowed to test recovery


class CircuitOpen(Exception):
    """Raised when the circuit breaker is open."""

    def __init__(self, name: str, until: float):
        remaining = max(0, until - time.monotonic())
        super().__init__(
            f"Circuit '{name}' is open — retry in {remaining:.1f}s"
        )
        self.name = name
        self.until = until


class CircuitBreaker:
    """Thread-safe circuit breaker.

    Parameters
    ----------
    name : str
        Human-readable label (for logging / error messages).
    threshold : int
        Consecutive failures before the breaker trips.
    cooldown : float
        Seconds the breaker stays open before allowing a probe.
    """

    def __init__(self, name: str = "default", threshold: int = 5, cooldown: float = 60.0):
        self.name = name
        self.threshold = threshold
        self.cooldown = cooldown

        self._lock = threading.Lock()
        self._state = BreakerState.CLOSED
        self._failure_count = 0
        self._opened_at: float = 0.0
        self._success_count = 0
        self._total_trips = 0

    # ── Public API ───────────────────────────────────────────

    @property
    def state(self) -> BreakerState:
        with self._lock:
            self._maybe_transition()
            return self._state

    @property
    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "total_trips": self._total_trips,
            }

    def record_success(self) -> None:
        with self._lock:
            self._success_count += 1
            if self._state == BreakerState.HALF_OPEN:
                self._state = BreakerState.CLOSED
                self._failure_count = 0
            elif self._state == BreakerState.CLOSED:
                self._failure_count = 0

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if self._state == BreakerState.HALF_OPEN:
                self._trip()
            elif self._state == BreakerState.CLOSED and self._failure_count >= self.threshold:
                self._trip()

    def allow_request(self) -> bool:
        with self._lock:
            self._maybe_transition()
            if self._state == BreakerState.CLOSED:
                return True
            if self._state == BreakerState.HALF_OPEN:
                return True
            return False

    @contextmanager
    def __call__(self) -> Iterator[None]:
        """Context manager usage: ``with breaker(): do_work()``."""
        if not self.allow_request():
            raise CircuitOpen(self.name, self._opened_at + self.cooldown)
        try:
            yield
        except Exception:
            self.record_failure()
            raise
        else:
            self.record_success()

    def reset(self) -> None:
        """Force-reset to closed state (for testing)."""
        with self._lock:
            self._state = BreakerState.CLOSED
            self._failure_count = 0
            self._opened_at = 0.0

    # ── Internal ─────────────────────────────────────────────

    def _trip(self) -> None:
        """Transition to OPEN (must hold lock)."""
        self._state = BreakerState.OPEN
        self._opened_at = time.monotonic()
        self._total_trips += 1

    def _maybe_transition(self) -> None:
        """Auto-transition from OPEN → HALF_OPEN after cooldown (must hold lock)."""
        if self._state == BreakerState.OPEN:
            if time.monotonic() - self._opened_at >= self.cooldown:
                self._state = BreakerState.HALF_OPEN
