"""Local LLM Exhaust Adapter — wraps chat calls into EpisodeEvents.

Usage::

    adapter = LocalLLMExhaustAdapter(connector)
    result = adapter.chat_with_exhaust(
        [{"role": "user", "content": "Summarize the decision"}]
    )
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from adapters._exhaust_helpers import _make_event_id, _safe_str, _utcnow

logger = logging.getLogger(__name__)


class LocalLLMExhaustAdapter:
    """Wraps LlamaCppConnector.chat() to emit EpisodeEvents."""

    def __init__(
        self,
        connector: Any,
        endpoint: str = "http://localhost:8000/api/exhaust/events",
        project: str = "default",
    ) -> None:
        self._connector = connector
        self._endpoint = endpoint
        self._project = project

    def chat_with_exhaust(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Chat via local LLM and emit prompt + response + metric events."""
        start = time.monotonic()

        # Emit prompt event
        prompt_event = {
            "event_id": _make_event_id("local_llm", "prompt", _utcnow()),
            "event_type": "prompt",
            "timestamp": _utcnow(),
            "project": self._project,
            "source": "local",
            "data": _safe_str({"messages": messages, "max_tokens": max_tokens}),
        }

        # Execute chat
        result = self._connector.chat(
            messages, max_tokens=max_tokens, temperature=temperature,
        )

        latency_ms = int((time.monotonic() - start) * 1000)

        # Emit response event
        response_event = {
            "event_id": _make_event_id("local_llm", "response", _utcnow()),
            "event_type": "response",
            "timestamp": _utcnow(),
            "project": self._project,
            "source": "local",
            "data": _safe_str(result),
        }

        # Emit metric event
        metric_event = {
            "event_id": _make_event_id("local_llm", "metric", _utcnow()),
            "event_type": "metric",
            "timestamp": _utcnow(),
            "project": self._project,
            "source": "local",
            "data": json.dumps({
                "latency_ms": latency_ms,
                "model": result.get("model", ""),
                "backend": result.get("backend", "llama.cpp"),
                "usage": result.get("usage", {}),
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
                    logger.warning("Local LLM exhaust flush returned %s", resp.status)
        except Exception as exc:
            logger.warning("Local LLM exhaust flush failed: %s", exc)
