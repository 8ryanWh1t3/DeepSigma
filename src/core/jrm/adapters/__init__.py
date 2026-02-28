"""JRM adapters — thin, lossless parsers for external log formats."""

from __future__ import annotations

from .base import AdapterBase
from .registry import get_adapter, list_adapters, register_adapter

__all__ = [
    "AdapterBase",
    "get_adapter",
    "list_adapters",
    "register_adapter",
]
