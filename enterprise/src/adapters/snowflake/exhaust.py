"""Cortex Exhaust Adapter — wraps Cortex completions into EpisodeEvents.

Usage::

    adapter = CortexExhaustAdapter(connector)
    result = adapter.complete_with_exhaust("mistral-large", messages)
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from adapters._exhaust_helpers import _make_event_id, _safe_str, _utcnow

logger = logging.getLogger(__name__)


class CortexExhaustAdapter:
    """Wraps CortexConnector.complete_sync() to emit EpisodeEvents."""

    def __init__(
        self,
        connector: Any,
        endpoint: str = "http://localhost:8000/api/exhaust/events",
        project: str = "default",
    ) -> None:
        self._connector = connector
        self._endpoint = endpoint
        self._project = project

    def complete_with_exhaust(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Run Cortex completion and emit prompt + response + metric events."""
        start = time.monotonic()

        prompt_event = {
            "event_id": _make_event_id("cortex", "prompt", _utcnow()),
            "event_type": "prompt",
            "timestamp": _utcnow(),
            "project": self._project,
            "source": "snowflake_cortex",
            "data": _safe_str({"model": model, "messages": messages}),
        }

        result = self._connector.complete_sync(model, messages, max_tokens=max_tokens, temperature=temperature)

        latency_ms = int((time.monotonic() - start) * 1000)

        response_event = {
            "event_id": _make_event_id("cortex", "response", _utcnow()),
            "event_type": "response",
            "timestamp": _utcnow(),
            "project": self._project,
            "source": "snowflake_cortex",
            "data": _safe_str(result.get("response", "")),
        }

        metric_event = {
            "event_id": _make_event_id("cortex", "metric", _utcnow()),
            "event_type": "metric",
            "timestamp": _utcnow(),
            "project": self._project,
            "source": "snowflake_cortex",
            "data": json.dumps({
                "latency_ms": latency_ms,
                "model": model,
                "chunks": result.get("usage", {}).get("chunks", 0),
            }),
        }

        self._flush([prompt_event, response_event, metric_event])
        return result

    def _flush(self, events: List[Dict[str, Any]]) -> None:
        try:
            import urllib.request

            data = json.dumps(events).encode()
            req = urllib.request.Request(
                self._endpoint,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status >= 400:
                    logger.warning("Cortex exhaust flush returned %s", resp.status)
        except Exception as exc:
            logger.warning("Cortex exhaust flush failed: %s", exc)
