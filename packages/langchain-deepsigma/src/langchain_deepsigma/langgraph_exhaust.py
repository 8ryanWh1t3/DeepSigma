"""Async event tracker for graph execution streams.

Tracks graph node execution, edge traversal, and state checkpoints.
Optionally enforces DTE constraints during graph execution.

Usage::

    from langchain_deepsigma import LangGraphExhaustTracker

    tracker = LangGraphExhaustTracker(
        endpoint="http://localhost:8000/api/exhaust/events",
        project="my-project",
    )
    async for event in graph.astream_events(input, version="v2"):
        violations = await tracker.handle_event(event)
        if violations:
            break
    await tracker.flush()
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from ._helpers import _make_event_id, _safe_str, _utcnow

logger = logging.getLogger(__name__)


class LangGraphExhaustTracker:
    """Async event tracker for graph ``astream_events()`` output.

    Parameters
    ----------
    endpoint : str
        URL of the POST /api/exhaust/events endpoint.
    project : str
        Project tag attached to every event.
    dte_enforcer : optional
        A DTE enforcer instance for constraint checking.
    flush_interval : float
        Seconds between automatic flushes.
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:8000/api/exhaust/events",
        project: str = "default",
        dte_enforcer: Any = None,
        flush_interval: float = 1.0,
    ) -> None:
        self._endpoint = endpoint
        self._project = project
        self._dte = dte_enforcer
        self._flush_interval = flush_interval
        self._buffer: List[Dict[str, Any]] = []
        self._last_flush = time.monotonic()
        self._start_time: Optional[float] = None
        self._node_count = 0
        self._tool_call_count = 0
        self._violations: List[Dict[str, Any]] = []
        self._is_first_chain = True

    async def handle_event(self, event: dict) -> Optional[List[dict]]:
        """Process one graph event.

        Returns a list of DTE violation dicts when a constraint is breached,
        or ``None`` otherwise.
        """
        event_type = event.get("event", "")
        name = event.get("name", "")
        run_id = event.get("run_id", "")
        parent_ids = event.get("parent_ids", [])

        if self._start_time is None:
            self._start_time = time.monotonic()

        mapped_type: Optional[str] = None
        check_dte = False

        if event_type == "on_chain_start":
            if self._is_first_chain:
                mapped_type = "graph_start"
                self._is_first_chain = False
            else:
                mapped_type = "node_start"
        elif event_type == "on_chain_end":
            mapped_type = "node_end"
            self._node_count += 1
            check_dte = True
        elif event_type == "on_tool_start":
            mapped_type = "tool_start"
        elif event_type == "on_tool_end":
            mapped_type = "tool_end"
            self._tool_call_count += 1
            check_dte = True

        if mapped_type is None:
            return None

        record = {
            "event_id": _make_event_id(run_id, mapped_type, _utcnow()),
            "event_type": mapped_type,
            "timestamp": _utcnow(),
            "name": name,
            "run_id": run_id,
            "parent_ids": parent_ids,
            "project": self._project,
            "data": _safe_str(event.get("data", {})),
        }
        self._buffer.append(record)

        if time.monotonic() - self._last_flush >= self._flush_interval:
            await self.flush()

        if check_dte and self._dte is not None:
            elapsed_ms = (time.monotonic() - self._start_time) * 1000
            violations = self._dte.enforce(
                elapsed_ms=elapsed_ms,
                counts={
                    "hops": self._node_count,
                    "tool_calls": self._tool_call_count,
                },
            )
            if violations:
                violation_dicts = [
                    {
                        "gate": v.gate,
                        "field": v.field,
                        "limit": v.limit_value,
                        "actual": v.actual_value,
                        "severity": v.severity,
                        "message": v.message,
                    }
                    for v in violations
                ]
                self._violations.extend(violation_dicts)
                return violation_dicts

        return None

    async def flush(self) -> None:
        """Send buffered events to the exhaust endpoint."""
        if not self._buffer:
            return
        payload = list(self._buffer)
        self._buffer.clear()
        self._last_flush = time.monotonic()
        try:
            import urllib.request

            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                self._endpoint,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status >= 400:
                    logger.warning("Exhaust API returned %s", resp.status)
        except Exception as exc:
            logger.warning("Exhaust flush failed: %s", exc)

    def summary(self) -> dict:
        """Return summary of tracked events and violations."""
        elapsed = 0.0
        if self._start_time is not None:
            elapsed = (time.monotonic() - self._start_time) * 1000
        return {
            "elapsed_ms": round(elapsed, 1),
            "node_count": self._node_count,
            "tool_call_count": self._tool_call_count,
            "violations": list(self._violations),
        }
