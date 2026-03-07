"""ModelExchangeEngine — main façade for governed multi-model reasoning.

Deep Sigma is the reactor, boundary, and memory system.
Models are interchangeable cognitive thrusters.
Models produce exhaust. Deep Sigma produces judgment.

MEE output is draft-grade reasoning.  Any patch / apply / canon operation
must go through existing AuthorityOps / feeds / decision surface flow.
MEE can recommend escalation only.  MEE cannot approve itself.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .evaluator import evaluate_results
from .models import EvaluationResult, ReasoningResult
from .registry import AdapterRegistry
from .router import AdapterRouter


class ModelExchangeEngine:
    """Primary entry-point for the Model Exchange Engine."""

    def __init__(self, registry: Optional[AdapterRegistry] = None) -> None:
        self._registry = registry or AdapterRegistry()
        self._router = AdapterRouter(self._registry)

    @property
    def registry(self) -> AdapterRegistry:
        return self._registry

    def run(
        self,
        packet: Dict[str, Any],
        adapter_names: List[str],
    ) -> EvaluationResult:
        """Route *packet* through adapters, evaluate, and return summary."""
        results = self._router.route(packet, adapter_names)
        return evaluate_results(results)

    def run_single(
        self,
        packet: Dict[str, Any],
        adapter_name: str,
    ) -> ReasoningResult:
        """Run *packet* through a single adapter."""
        adapter = self._registry.get(adapter_name)
        normalised = adapter.normalize_packet(packet)
        return adapter.reason(normalised)

    def health(self) -> Dict[str, Any]:
        """Aggregate health status from all registered adapters."""
        adapters = self._registry.list_adapters()
        statuses: Dict[str, Any] = {}
        for name in adapters:
            adapter = self._registry.get(name)
            statuses[name] = adapter.health()
        return {
            "ok": all(s.get("ok", False) for s in statuses.values()),
            "adapters": statuses,
            "adapter_count": len(adapters),
        }
