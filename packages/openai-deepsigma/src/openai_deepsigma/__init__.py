"""Agent wrapper for coherence pipeline integration.

Public API
----------
DeepSigmaAgentWrapper — wraps any agent with .run() for decision logging
AgentRunResult        — result of a wrapped agent run
"""
from __future__ import annotations

from .wrapper import DeepSigmaAgentWrapper, AgentRunResult

__all__ = [
    "DeepSigmaAgentWrapper",
    "AgentRunResult",
]
