"""Flask extension that logs each request as a sealed decision.

Usage::

    from deepsigma_middleware import FlaskDeepSigma, configure

    configure(agent_id="my-api")
    FlaskDeepSigma(app)
"""
from __future__ import annotations

import time
from typing import Any, Optional

from .decorator import get_session, configure as _configure


class FlaskDeepSigma:
    """Flask extension for coherence pipeline integration.

    Parameters
    ----------
    app
        Flask application instance. If None, call ``init_app()`` later.
    agent_id : str
        Override the default agent_id.
    storage_dir : str
        Override the default storage_dir.
    """

    def __init__(
        self,
        app: Any = None,
        agent_id: str = "",
        storage_dir: Optional[str] = None,
    ) -> None:
        self._agent_id = agent_id
        self._storage_dir = storage_dir
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Any) -> None:
        """Register before/after request hooks on the Flask app."""
        if self._agent_id or self._storage_dir:
            _configure(
                agent_id=self._agent_id or "default-api",
                storage_dir=self._storage_dir,
            )

        app.before_request(self._before_request)
        app.after_request(self._after_request)

    @staticmethod
    def _before_request() -> None:
        from flask import g
        g._deepsigma_start = time.monotonic()

    @staticmethod
    def _after_request(response: Any) -> Any:
        from flask import g, request

        start = getattr(g, "_deepsigma_start", None)
        elapsed_ms = int((time.monotonic() - start) * 1000) if start else 0

        session = get_session()
        session.log_decision({
            "action": f"{request.method} {request.path}",
            "reason": f"HTTP request: {request.method} {request.path}",
            "decision_type": "http_request",
            "actor": {"type": "api", "id": session.agent_id},
            "confidence": 1.0 if response.status_code < 400 else 0.5,
        })
        return response
