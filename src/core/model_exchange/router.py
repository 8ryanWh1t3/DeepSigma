"""Router — dispatch a reasoning packet to one or many adapters."""

from __future__ import annotations

from typing import Any, Dict, List

from .models import ReasoningResult
from .registry import AdapterRegistry


class AdapterRouter:
    """Route reasoning packets through registered adapters."""

    def __init__(self, registry: AdapterRegistry) -> None:
        self._registry = registry

    def route(
        self,
        packet: Dict[str, Any],
        adapter_names: List[str],
    ) -> List[ReasoningResult]:
        """Run *packet* through every named adapter and collect results."""
        if not adapter_names:
            raise ValueError("adapter_names must not be empty")
        results: List[ReasoningResult] = []
        for name in adapter_names:
            adapter = self._registry.get(name)
            normalised = adapter.normalize_packet(packet)
            result = adapter.reason(normalised)
            results.append(result)
        return results
