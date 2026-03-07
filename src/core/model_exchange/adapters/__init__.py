"""Model Exchange adapters — pluggable cognitive thrusters."""

from __future__ import annotations

from .apex_adapter import ApexAdapter
from .claude_adapter import ClaudeAdapter
from .gguf_adapter import GGUFAdapter
from .mock_adapter import MockAdapter
from .openai_adapter import OpenAIAdapter

__all__ = [
    "ApexAdapter",
    "ClaudeAdapter",
    "GGUFAdapter",
    "MockAdapter",
    "OpenAIAdapter",
]
