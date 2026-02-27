"""ASGI middleware that logs each request as a sealed decision.

Usage::

    from deepsigma_middleware import DeepSigmaMiddleware, configure

    configure(agent_id="my-api")
    app = DeepSigmaMiddleware(app)
"""
from __future__ import annotations

import time
from typing import Any, Callable

from .decorator import get_session, _agent_id_var


class DeepSigmaMiddleware:
    """ASGI middleware wrapping each request in a coherence decision.

    Parameters
    ----------
    app
        The ASGI application to wrap.
    agent_id : str
        Override agent_id for this middleware instance.
    """

    def __init__(self, app: Any, agent_id: str = "") -> None:
        self.app = app
        self._agent_id = agent_id

    async def __call__(
        self,
        scope: dict,
        receive: Callable,
        send: Callable,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if self._agent_id:
            _agent_id_var.set(self._agent_id)

        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        start = time.monotonic()

        status_code = 200
        original_send = send

        async def capture_send(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await original_send(message)

        try:
            await self.app(scope, receive, capture_send)
        finally:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            session = get_session()
            session.log_decision({
                "action": f"{method} {path}",
                "reason": f"HTTP request: {method} {path}",
                "decision_type": "http_request",
                "actor": {"type": "api", "id": _agent_id_var.get()},
                "confidence": 1.0 if status_code < 400 else 0.5,
            })
