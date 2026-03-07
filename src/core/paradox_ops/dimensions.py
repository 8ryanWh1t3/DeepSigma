"""Dimension registry for Paradox Tension Sets.

Defines the 6 canonical common dimensions and 10 uncommon extensions.
Provides a registry for looking up, creating, and validating dimensions.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .models import DimensionKind, TensionDimension

COMMON_DIMENSIONS: List[Dict[str, Any]] = [
    {"name": "time", "is_governance_relevant": False, "threshold": 0.5},
    {"name": "authority", "is_governance_relevant": True, "threshold": 0.4},
    {"name": "risk", "is_governance_relevant": True, "threshold": 0.4},
    {"name": "layer", "is_governance_relevant": False, "threshold": 0.5},
    {"name": "objective", "is_governance_relevant": False, "threshold": 0.5},
    {"name": "resource", "is_governance_relevant": False, "threshold": 0.5},
]

UNCOMMON_DIMENSIONS: List[Dict[str, Any]] = [
    {"name": "reversibility", "is_governance_relevant": False, "threshold": 0.5},
    {"name": "confidence", "is_governance_relevant": False, "threshold": 0.5},
    {"name": "visibility", "is_governance_relevant": False, "threshold": 0.5},
    {"name": "classification", "is_governance_relevant": True, "threshold": 0.4},
    {"name": "provenance_depth", "is_governance_relevant": False, "threshold": 0.5},
    {"name": "dependency_density", "is_governance_relevant": False, "threshold": 0.5},
    {"name": "human_fatigue", "is_governance_relevant": False, "threshold": 0.5},
    {"name": "legal_exposure", "is_governance_relevant": True, "threshold": 0.4},
    {"name": "mission_criticality", "is_governance_relevant": True, "threshold": 0.4},
    {"name": "narrative_volatility", "is_governance_relevant": False, "threshold": 0.5},
]

COMMON_DIMENSION_NAMES = frozenset(d["name"] for d in COMMON_DIMENSIONS)


class DimensionRegistry:
    """Registry of available dimension templates."""

    def __init__(self) -> None:
        self._registry: Dict[str, Dict[str, Any]] = {}
        for d in COMMON_DIMENSIONS:
            self._registry[d["name"]] = {**d, "kind": DimensionKind.COMMON.value}
        for d in UNCOMMON_DIMENSIONS:
            self._registry[d["name"]] = {**d, "kind": DimensionKind.UNCOMMON.value}

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Look up a dimension template by name."""
        return self._registry.get(name)

    def register(
        self,
        name: str,
        is_governance_relevant: bool = False,
        threshold: float = 0.5,
        kind: str = "uncommon",
    ) -> None:
        """Register a custom uncommon dimension."""
        self._registry[name] = {
            "name": name,
            "is_governance_relevant": is_governance_relevant,
            "threshold": threshold,
            "kind": kind,
        }

    def list_common(self) -> List[str]:
        """Return names of all common dimensions."""
        return [
            n for n, d in self._registry.items()
            if d.get("kind") == DimensionKind.COMMON.value
        ]

    def list_all(self) -> List[str]:
        """Return names of all registered dimensions."""
        return sorted(self._registry.keys())

    def create_dimension(self, name: str, dim_id: Optional[str] = None) -> TensionDimension:
        """Create a TensionDimension instance from a registry template."""
        template = self._registry.get(name)
        if template is None:
            raise ValueError(f"Unknown dimension: {name!r}")
        return TensionDimension(
            dimension_id=dim_id or f"DIM-{uuid.uuid4().hex[:8]}",
            name=name,
            kind=template.get("kind", DimensionKind.UNCOMMON.value),
            is_governance_relevant=template.get("is_governance_relevant", False),
            threshold=template.get("threshold", 0.5),
        )

    def create_default_dimensions(self, tension_id: str) -> List[TensionDimension]:
        """Create the 6 default common dimensions for a PTS."""
        dims: List[TensionDimension] = []
        for i, d in enumerate(COMMON_DIMENSIONS, start=1):
            dims.append(TensionDimension(
                dimension_id=f"DIM-{tension_id}-{i:02d}",
                name=d["name"],
                kind=DimensionKind.COMMON.value,
                is_governance_relevant=d["is_governance_relevant"],
                threshold=d["threshold"],
            ))
        return dims
