"""REST middleware for the coherence pipeline.

Public API
----------
configure          -- set default agent_id and storage_dir
log_decision       -- decorator that logs function calls as decisions
DeepSigmaMiddleware -- ASGI middleware for request-level logging
FlaskDeepSigma     -- Flask extension for request-level logging
"""
from __future__ import annotations

from .decorator import configure, log_decision, get_session
from .fastapi_mw import DeepSigmaMiddleware
from .flask_mw import FlaskDeepSigma

__all__ = [
    "configure",
    "log_decision",
    "get_session",
    "DeepSigmaMiddleware",
    "FlaskDeepSigma",
]
