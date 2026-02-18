"""AskSage Exhaust Adapter — wraps queries into EpisodeEvents.

Usage::

    adapter = AskSageExhaustAdapter(connector)
    result = adapter.query_with_exhaust("What is NIST CSF?")
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from adapters._exhaust_helpers import _make_event_id, _safe_str, _utcnow

logger = logging.getLogger(__name__)


class AskSageExhaustAdapter:
    """Wraps AskSageConnector.query() to emit EpisodeEvents."""

    def __init__(
        self,
        connector: Any,
        endpoint: str = "http://localhost:8000/api/exhaust/events",
        project: str = "default",
    ) -> None:
        self._connector = connector
        self._endpoint = endpoint
        self._project = project

    def query_with_exhaust(
        self,
        prompt: str,
        model: Optional[str] = None,
        dataset: Optional[str] = None,
        persona: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query AskSage and emit prompt + response events to Exhaust."""
        start = time.monotonic()

        # Emit prompt event
        prompt_event = {
            "event_id": _make_event_id("asksage", "prompt", _utcnow()),
            "event_type": "prompt",
            "timestamp": _utcnow(),
            "project": self._project,
            "source": "asksage",
            "data": _safe_str({"prompt": prompt, "model": model, "dataset": dataset, "persona": persona}),
        }

        # Execute query
        result = self._connector.query(prompt, model=model, dataset=dataset, persona=persona)

        latency_ms = int((time.monotonic() - start) * 1000)

        # Emit response event
        response_event = {
            "event_id": _make_event_id("asksage", "response", _utcnow()),
            "event_type": "response",
            "timestamp": _utcnow(),
            "project": self._project,
            "source": "asksage",
            "data": _safe_str(result),
        }

        # Emit metric event
        metric_event = {
            "event_id": _make_event_id("asksage", "metric", _utcnow()),
            "event_type": "metric",
            "timestamp": _utcnow(),
            "project": self._project,
            "source": "asksage",
            "data": json.dumps({
                "latency_ms": latency_ms,
                "model": model or result.get("model", ""),
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
                    logger.warning("AskSage exhaust flush returned %s", resp.status)
        except Exception as exc:
            logger.warning("AskSage exhaust flush failed: %s", exc)
