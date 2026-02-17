"""
adapters/langchain_exhaust.py – LangChain callback handler for Exhaust Inbox
=============================================================================
Extends DeepSigmaCallbackHandler to emit EpisodeEvent payloads into the
Exhaust Inbox ingestion endpoint in real-time.

Usage:
    from adapters.langchain_exhaust import ExhaustCallbackHandler

    handler = ExhaustCallbackHandler(
        endpoint="http://localhost:8000/api/exhaust/events",
        project="my-project",
        team="ml-team",
    )
    chain.invoke(input, config={"callbacks": [handler]})
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Minimal base – avoid hard dependency on langchain at import time
# ---------------------------------------------------------------------------
try:
    from langchain_core.callbacks import BaseCallbackHandler  # type: ignore
except ImportError:  # pragma: no cover
    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Stub so the module can be imported without langchain installed."""
        pass

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_user(user_id: Optional[str]) -> str:
    """One-way hash for PII-safe user identification."""
    if not user_id:
        return "anon"
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]


def _make_event_id(*parts: str) -> str:
    """Deterministic event ID from composite key parts."""
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_str(obj: Any, max_len: int = 4000) -> str:
    """Convert payload to a string, truncating if necessary."""
    if isinstance(obj, str):
        s = obj
    else:
        try:
            s = json.dumps(obj, default=str)
        except Exception:
            s = str(obj)
    return s[:max_len] if len(s) > max_len else s


# ---------------------------------------------------------------------------
# Callback handler
# ---------------------------------------------------------------------------

class ExhaustCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback that emits EpisodeEvent payloads to the Exhaust API.

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
    """

    name = "exhaust_callback"

    def __init__(
        self,
        endpoint: str = "http://localhost:8000/api/exhaust/events",
        project: str = "default",
        team: str = "",
        source: str = "langchain",
        flush_interval: float = 0,
    ) -> None:
        super().__init__()
        self._endpoint = endpoint
        self._project = project
        self._team = team
        self._source = source
        self._flush_interval = flush_interval
        self._buffer: List[Dict[str, Any]] = []
        self._last_flush = time.monotonic()

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
            "episode_id": "",  # assigned during assembly
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

    # -- LangChain callbacks -----------------------------------------------

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
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
        # Final flush when the top-level chain finishes
        self._flush()
