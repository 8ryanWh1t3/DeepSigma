"""DTE-enforcing callback handler for chain runtimes.

Enforces Decision Timing Envelope constraints during chain execution.
Complements ``ExhaustCallbackHandler`` (logging) with active governance.

Usage::

    from langchain_deepsigma import GovernanceCallbackHandler

    handler = GovernanceCallbackHandler(
        dte_enforcer=enforcer,
        on_violation="raise",
    )
    chain.invoke(input, config={"callbacks": [handler]})
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

logger = logging.getLogger(__name__)

# Avoid hard dependency on langchain at import time
try:
    from langchain_core.callbacks import BaseCallbackHandler  # type: ignore
except ImportError:  # pragma: no cover
    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Stub so the module can be imported without langchain installed."""
        pass


class DTEViolationError(Exception):
    """Raised when a DTE constraint is violated and on_violation='raise'."""

    def __init__(self, violations: List[Dict[str, Any]]) -> None:
        self.violations = violations
        messages = [v.get("message", str(v)) for v in violations]
        super().__init__(f"DTE violation(s): {'; '.join(messages)}")


class GovernanceCallbackHandler(BaseCallbackHandler):
    """Callback that enforces DTE constraints mid-chain.

    Parameters
    ----------
    dte_enforcer
        Enforcer instance with an ``enforce(elapsed_ms, counts)`` method.
    project : str
        Project tag for exhaust events.
    on_violation : str
        ``"raise"`` -- raise ``DTEViolationError`` (halts chain).
        ``"log"`` -- log warning + emit drift event, continue.
        ``"degrade"`` -- set ``should_degrade`` flag, continue.
    exhaust_endpoint : str
        Optional endpoint for emitting drift events on violation.
    session : optional
        An ``AgentSession`` instance for coherence pipeline integration.
    """

    name = "governance_callback"

    def __init__(
        self,
        dte_enforcer: Any,
        project: str = "default",
        on_violation: str = "raise",
        exhaust_endpoint: str = "",
        session: Any = None,
    ) -> None:
        super().__init__()
        self._dte = dte_enforcer
        self._project = project
        self._on_violation = on_violation
        self._exhaust_endpoint = exhaust_endpoint
        self._session = session

        self._start_time: Optional[float] = None
        self._tool_call_count = 0
        self._chain_depth = 0
        self._violations: List[Dict[str, Any]] = []
        self.should_degrade = False

    @property
    def violations(self) -> List[Dict[str, Any]]:
        return list(self._violations)

    def summary(self) -> Dict[str, Any]:
        elapsed = 0.0
        if self._start_time is not None:
            elapsed = (time.monotonic() - self._start_time) * 1000
        return {
            "elapsed_ms": round(elapsed, 1),
            "tool_calls": self._tool_call_count,
            "chain_depth": self._chain_depth,
            "violations": list(self._violations),
        }

    # -- Callbacks ---------------------------------------------------------

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        if self._start_time is None:
            self._start_time = time.monotonic()
        self._chain_depth += 1

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        pass

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._check_dte()

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._tool_call_count += 1

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._check_dte()

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._chain_depth = max(0, self._chain_depth - 1)
        self._check_dte()

    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        pass

    # -- Internal ----------------------------------------------------------

    def _check_dte(self) -> None:
        if self._dte is None or self._start_time is None:
            return

        elapsed_ms = (time.monotonic() - self._start_time) * 1000
        violations = self._dte.enforce(
            elapsed_ms=elapsed_ms,
            counts={
                "tool_calls": self._tool_call_count,
                "chain_depth": self._chain_depth,
            },
        )
        if not violations:
            return

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

        if self._on_violation == "raise":
            raise DTEViolationError(violation_dicts)
        elif self._on_violation == "log":
            for v in violation_dicts:
                logger.warning("DTE violation: %s", v["message"])
            self._emit_drift(violation_dicts)
        elif self._on_violation == "degrade":
            self.should_degrade = True

    def _emit_drift(self, violations: List[Dict[str, Any]]) -> None:
        if not self._exhaust_endpoint:
            return
        try:
            import urllib.request
            from ._helpers import _make_event_id, _utcnow

            events = [
                {
                    "event_id": _make_event_id("governance", v["gate"], _utcnow()),
                    "event_type": "drift",
                    "timestamp": _utcnow(),
                    "project": self._project,
                    "data": v,
                }
                for v in violations
            ]
            data = json.dumps(events).encode()
            req = urllib.request.Request(
                self._exhaust_endpoint,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status >= 400:
                    logger.warning("Drift emit returned %s", resp.status)
        except Exception as exc:
            logger.warning("Drift emit failed: %s", exc)
