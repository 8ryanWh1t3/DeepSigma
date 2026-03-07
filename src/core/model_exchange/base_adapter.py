"""Abstract base class for all Model Exchange adapters.

Every adapter must return a ReasoningResult.
Adapters must never perform commit / patch / canon write operations.
Adapters are drafting-only by default.
"""

from __future__ import annotations

import abc
from typing import Any, Dict

from .models import ReasoningResult


class BaseModelAdapter(abc.ABC):
    """Base contract for model adapters in the Model Exchange Engine.

    Models produce exhaust. Deep Sigma produces judgment.
    """

    adapter_name: str = "base"

    @abc.abstractmethod
    def reason(self, packet: Dict[str, Any]) -> ReasoningResult:
        """Process a reasoning packet and return structured output.

        The packet is a dict containing at minimum a ``request_id`` and
        ``question`` field.  Adapters may inspect additional keys such as
        ``evidence``, ``claims``, ``topic``, ``ttl``, and ``context``.
        """
        ...

    def health(self) -> Dict[str, Any]:
        """Return a health-check dict for this adapter."""
        return {"ok": True, "adapter_name": self.adapter_name}

    def normalize_packet(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise an incoming packet before reasoning.  Default pass-through."""
        return packet
