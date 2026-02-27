"""Decorator and context-var session management for the coherence pipeline.

Usage::

    from deepsigma_middleware import configure, log_decision

    configure(agent_id="my-api", storage_dir="/tmp/decisions")

    @log_decision(actor_type="api", decision_type="endpoint")
    def handle_request(request):
        ...
"""
from __future__ import annotations

import contextvars
import functools
import logging
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_agent_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "deepsigma_agent_id", default="default-api",
)
_storage_dir_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "deepsigma_storage_dir", default=None,
)
_session_var: contextvars.ContextVar[Any] = contextvars.ContextVar(
    "deepsigma_session",
)


def configure(
    agent_id: str = "default-api",
    storage_dir: Optional[str | Path] = None,
) -> None:
    """Set default agent_id and storage_dir for this context."""
    _agent_id_var.set(agent_id)
    if storage_dir is not None:
        _storage_dir_var.set(str(storage_dir))


def get_session() -> Any:
    """Return the current context's AgentSession, creating one if needed."""
    try:
        session = _session_var.get()
        if session is not None:
            return session
    except LookupError:
        pass

    from core.agent import AgentSession

    agent_id = _agent_id_var.get()
    storage_dir = _storage_dir_var.get()
    session = AgentSession(agent_id, storage_dir=storage_dir)
    _session_var.set(session)
    return session


def reset_session() -> None:
    """Clear the current session (useful for testing)."""
    _session_var.set(None)


def log_decision(
    actor_type: str = "api",
    decision_type: str = "request",
) -> Callable:
    """Decorator that logs the decorated function call as a decision.

    Parameters
    ----------
    actor_type : str
        Actor type tag for the decision (e.g. "api", "worker").
    decision_type : str
        Decision type tag (e.g. "endpoint", "task").
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            session = get_session()
            result = func(*args, **kwargs)
            session.log_decision({
                "action": func.__name__,
                "reason": f"Function call: {func.__name__}",
                "decision_type": decision_type,
                "actor": {"type": actor_type, "id": _agent_id_var.get()},
            })
            return result

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            session = get_session()
            result = await func(*args, **kwargs)
            session.log_decision({
                "action": func.__name__,
                "reason": f"Function call: {func.__name__}",
                "decision_type": decision_type,
                "actor": {"type": actor_type, "id": _agent_id_var.get()},
            })
            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator
