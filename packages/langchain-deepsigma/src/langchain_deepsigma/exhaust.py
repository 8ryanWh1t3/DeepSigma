"""Callback handler that emits episode events to the exhaust inbox.

Usage::

    from langchain_deepsigma import ExhaustCallbackHandler

    handler = ExhaustCallbackHandler(
        endpoint="http://localhost:8000/api/exhaust/events",
        project="my-project",
    )
    chain.invoke(input, config={"callbacks": [handler]})
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from ._helpers import _hash_user, _make_event_id, _utcnow, _safe_str

logger = logging.getLogger(__name__)

# Avoid hard dependency on langchain at import time
try:
    from langchain_core.callbacks import BaseCallbackHandler  # type: ignore
except ImportError:  # pragma: no cover
    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Stub so the module can be imported without langchain installed."""
        pass


class ExhaustCallbackHandler(BaseCallbackHandler):
    """Callback that emits episode event payloads to the exhaust API.

    Parameters
    ----------
    endpoint : str
        URL of the POST /api/exhaust/events endpoint.
    project : str
        Project tag attached to every event.
    team : str
        Team tag.
    source : str
        Source identifier (default: "langchain").
    flush_interval : float
        Seconds between automatic flushes (0 = send immediately).
    session : optional
        An ``AgentSession`` instance. When provided, events are also
        logged as decisions through the coherence pipeline.
    """

    name = "exhaust_callback"

    def __init__(
        self,
        endpoint: str = "http://localhost:8000/api/exhaust/events",
        project: str = "default",
        team: str = "",
        source: str = "langchain",
        flush_interval: float = 0,
        session: Any = None,
    ) -> None:
        super().__init__()
        self._endpoint = endpoint
        self._project = project
        self._team = team
        self._source = source
        self._flush_interval = flush_interval
        self._session = session
        self._buffer: List[Dict[str, Any]] = []
        self._last_flush = time.monotonic()
        self._run_start: Dict[str, float] = {}
        self._run_model: Dict[str, str] = {}

    # -- internal ----------------------------------------------------------

    def _emit(self, event: Dict[str, Any]) -> None:
        self._buffer.append(event)
        if self._flush_interval <= 0 or (
            time.monotonic() - self._last_flush >= self._flush_interval
        ):
            self._flush()

    def _flush(self) -> None:
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

    def _base(
        self,
        event_type: str,
        run_id: UUID,
        parent_run_id: Optional[UUID],
        payload: Any,
        **extra: Any,
    ) -> Dict[str, Any]:
        session_id = str(parent_run_id or run_id)
        return {
            "event_id": _make_event_id(str(run_id), event_type, _utcnow()),
            "episode_id": "",
            "session_id": session_id,
            "event_type": event_type,
            "timestamp": _utcnow(),
            "user_hash": _hash_user(extra.get("user_id")),
            "source": self._source,
            "project": self._project,
            "team": self._team,
            "payload": _safe_str(payload),
            "meta": {k: _safe_str(v) for k, v in extra.items()},
        }

    def _maybe_log_decision(self, event_type: str, payload: Any) -> None:
        """If a session is attached, log the event as a decision."""
        if self._session is None:
            return
        self._session.log_decision({
            "action": event_type,
            "reason": f"Callback event: {event_type}",
            "actor": {"type": "agent", "id": self._source},
        })

    # -- Callbacks ---------------------------------------------------------

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._run_start[str(run_id)] = time.monotonic()
        self._run_model[str(run_id)] = (
            serialized.get("kwargs", {}).get("model_name")
            or serialized.get("name", "")
        )
        self._emit(
            self._base("prompt", run_id, parent_run_id, prompts, **kwargs)
        )

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        text = ""
        try:
            text = response.generations[0][0].text  # type: ignore[union-attr]
        except Exception:
            text = str(response)
        self._emit(
            self._base("response", run_id, parent_run_id, text, **kwargs)
        )
        latency_ms = int(
            (time.monotonic() - self._run_start.pop(str(run_id), time.monotonic())) * 1000
        )
        model = self._run_model.pop(str(run_id), "")
        session_id = str(parent_run_id or run_id)
        self._emit({
            "event_id": _make_event_id(str(run_id), "metric", _utcnow()),
            "episode_id": "",
            "session_id": session_id,
            "event_type": "metric",
            "timestamp": _utcnow(),
            "user_hash": _hash_user(kwargs.get("user_id")),
            "source": self._source,
            "project": self._project,
            "team": self._team,
            "payload": {"latency_ms": latency_ms, "model": model},
            "meta": {},
        })
        self._maybe_log_decision("llm_response", text)

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._emit(
            self._base(
                "tool_call",
                run_id,
                parent_run_id,
                {"tool": serialized.get("name", "unknown"), "input": input_str},
                **kwargs,
            )
        )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._emit(
            self._base("tool_result", run_id, parent_run_id, output, **kwargs)
        )
        self._maybe_log_decision("tool_result", output)

    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._emit(
            self._base("error", run_id, parent_run_id, str(error), **kwargs)
        )

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._flush()
