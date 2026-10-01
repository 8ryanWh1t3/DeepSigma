"""Narrow v0.4 compatibility shim.

This module exists only to help callers migrate. The v0.4 governance/trust/
authoritative-state system is intentionally NOT part of the v0.5 core engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .engine import VinculumEngine
from .ingest import ingest_text
from .models import ObjectType, ScoreMode, VinculumResult


@dataclass(frozen=True)
class Hypothesis:
    id: str
    statement: str
    probability: float = 0.5
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Constraint:
    id: str
    field: str
    op: str
    expected: Any
    hard: bool = True
    weight: float = 1.0


class LegacyV04Adapter:
    """Translate a v0.4-style hypothesis into a v0.5 language score.

    Constraints are reported as migration metadata only. They are not treated as
    governance or approval gates. Users should model deterministic constraints in
    the content or a dedicated scorer/profile when migrating.
    """

    def __init__(self, engine: VinculumEngine | None = None) -> None:
        self.engine = engine or VinculumEngine()

    def score_hypothesis(self, hypothesis: Hypothesis, constraints: tuple[Constraint, ...] = ()) -> VinculumResult:
        text = hypothesis.statement
        if constraints:
            rendered = "; ".join(f"{c.field} {c.op} {c.expected}" for c in constraints)
            text = f"{text}\nDeterministic constraints: {rendered}"
        obj = ingest_text(text, object_id=hypothesis.id, object_type=ObjectType.CLAIM, mode=ScoreMode.LANGUAGE, decompose=False)
        result = self.engine.score(obj)
        meta = dict(result.metadata)
        meta.update({"legacy_probability": hypothesis.probability, "legacy_constraint_count": len(constraints), "compatibility": "v0.4-shim"})
        return VinculumResult(**{**result.__dict__, "metadata": meta})
