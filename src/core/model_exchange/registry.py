"""Adapter registry — register, retrieve, and list model adapters."""

from __future__ import annotations

from typing import Dict, List

from .base_adapter import BaseModelAdapter


class AdapterRegistry:
    """Thread-safe-ish registry for model adapters."""

    def __init__(self) -> None:
        self._adapters: Dict[str, BaseModelAdapter] = {}

    def register(self, name: str, adapter: BaseModelAdapter) -> None:
        """Register an adapter under *name*."""
        if not isinstance(adapter, BaseModelAdapter):
            raise TypeError(
                f"Expected BaseModelAdapter, got {type(adapter).__name__}"
            )
        self._adapters[name] = adapter

    def get(self, name: str) -> BaseModelAdapter:
        """Return the adapter registered as *name*."""
        try:
            return self._adapters[name]
        except KeyError:
            raise KeyError(
                f"Adapter '{name}' not registered.  "
                f"Available: {', '.join(sorted(self._adapters)) or '(none)'}"
            )

    def list_adapters(self) -> List[str]:
        """Return sorted list of registered adapter names."""
        return sorted(self._adapters.keys())
