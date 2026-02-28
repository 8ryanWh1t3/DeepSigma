"""DomainMode base class — shared handler interface for all domain modes."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FunctionResult:
    """Result of executing a domain function handler."""

    function_id: str
    success: bool
    events_emitted: List[Dict[str, Any]] = field(default_factory=list)
    drift_signals: List[Dict[str, Any]] = field(default_factory=list)
    mg_updates: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0
    replay_hash: str = ""
    error: Optional[str] = None

    def compute_replay_hash(self) -> str:
        """Compute SHA-256 of deterministic output fields."""
        content = {
            "function_id": self.function_id,
            "success": self.success,
            "events_emitted": self.events_emitted,
            "drift_signals": self.drift_signals,
            "mg_updates": sorted(self.mg_updates),
        }
        canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.replay_hash = f"sha256:{digest}"
        return self.replay_hash


# Type alias for a function handler.
Handler = Callable[[Dict[str, Any], Dict[str, Any]], FunctionResult]


class DomainMode:
    """Base class for IntelOps, FranOps, ReflectionOps.

    Subclasses register handlers in ``_register_handlers()`` and
    callers invoke them via ``handle(function_id, event, context)``.
    """

    domain: str = ""

    def __init__(self) -> None:
        self._handlers: Dict[str, Handler] = {}
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Override in subclass to populate ``self._handlers``."""
        raise NotImplementedError

    @property
    def function_ids(self) -> List[str]:
        """All registered function IDs."""
        return sorted(self._handlers.keys())

    def has_handler(self, function_id: str) -> bool:
        """Check if a handler is registered for a function ID."""
        return function_id in self._handlers

    def handle(
        self,
        function_id: str,
        event: Dict[str, Any],
        context: Dict[str, Any],
    ) -> FunctionResult:
        """Execute a function handler by ID.

        Args:
            function_id: e.g. "INTEL-F01"
            event: FEEDS envelope or payload dict.
            context: Shared state (memory_graph, canon_store, drift_collector, etc.)

        Returns:
            FunctionResult with events emitted, drift signals, MG updates, and replay hash.
        """
        handler = self._handlers.get(function_id)
        if handler is None:
            return FunctionResult(
                function_id=function_id,
                success=False,
                error=f"No handler for {function_id} in {self.domain}",
            )

        t0 = time.monotonic()
        try:
            result = handler(event, context)
            result.elapsed_ms = (time.monotonic() - t0) * 1000
            result.compute_replay_hash()
            return result
        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000
            logger.exception("Handler %s failed: %s", function_id, exc)
            return FunctionResult(
                function_id=function_id,
                success=False,
                elapsed_ms=elapsed,
                error=str(exc),
            )

    def replay(
        self,
        function_id: str,
        event: Dict[str, Any],
        context: Dict[str, Any],
        expected_hash: str,
    ) -> bool:
        """Execute a handler and verify the output hash matches.

        Returns True if the replay hash matches the expected hash.
        """
        result = self.handle(function_id, event, context)
        return result.replay_hash == expected_hash
