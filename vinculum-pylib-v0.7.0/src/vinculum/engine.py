from __future__ import annotations

from dataclasses import replace
import json
from typing import Any

from .config import ScoringConfig
from .formulas import clamp01, derive_vector
from .models import ObjectType, ScoreMode, Signal, VinculumObject, VinculumResult
from .scorers import detect_mode, score_language, score_math, score_structured, score_ttl_graph, score_ttl_triple
from .semantics import MeaningRegistry, ReconciliationStatus, reconcile_object


class VinculumEngine:
    """VINCULUM pyLib v0.5.2 — P↔D Tension Engine.

    The engine does not decide truth, authority, approval, or permission. It measures
    the relationship between probabilistic pressure (P) and deterministic strength (D),
    then derives the third state ΣV = {P, D, V, tau, Coverage}.
    """

    def __init__(self, config: ScoringConfig | None = None, meaning_registry: MeaningRegistry | None = None) -> None:
        self.config = config or ScoringConfig()
        self.meaning_registry = meaning_registry or MeaningRegistry.default()

    def score(self, obj: VinculumObject) -> VinculumResult:
        child_results = tuple(self.score(child) for child in obj.children)
        mode = self._resolve_mode(obj)
        own = self._score_own(obj, mode)
        P, D, coverage, drivers_p, drivers_d, unresolved, metadata = own

        overlay_weight = self._overlay_weight(obj, child_results)
        if child_results:
            agg = self._aggregate_children(obj, child_results)
            if overlay_weight > 0:
                total_w = agg[3] + overlay_weight
                P = (agg[0] * agg[3] + P * overlay_weight) / total_w
                D = (agg[1] * agg[3] + D * overlay_weight) / total_w
                coverage = (agg[2] * agg[3] + coverage * overlay_weight) / total_w
            else:
                P, D, coverage = agg[0], agg[1], agg[2]
            # Parent-level drivers are descriptive only; child drivers remain in children.
            unresolved = tuple(dict.fromkeys(unresolved + tuple(u for c in child_results for u in c.unresolved_elements)))
            metadata = {**metadata, "aggregate_children": len(child_results), "aggregate_weight": agg[3], "parent_overlay_weight": overlay_weight}

        # v0.5.2 semantic determinization + second-order record-defense reconciliation.
        # This is deliberately bounded: explicit lexical rules resolve language into
        # comparable facts, then explicit record values defend deterministic state.
        # No LLM, authority, or policy semantics are introduced here.
        reconciliation = reconcile_object(obj, self.meaning_registry)
        if reconciliation.semantic_facts:
            semantic_strength = max((f.confidence for f in reconciliation.semantic_facts), default=0.0)
            D = max(D, min(1.0, 0.80 * semantic_strength))
            drivers_d = tuple(drivers_d) + (
                Signal(
                    "D_SEMANTIC_RESOLUTION",
                    "D",
                    "Canonical phrase resolved to machine-comparable meaning",
                    0.80,
                    len(reconciliation.semantic_facts),
                    tuple(f.phrase for f in reconciliation.semantic_facts[:3]),
                    "Language P is pushed toward D through an explicit semantic registry.",
                ),
            )
        record_raw_d: float | None = None
        record_effective_d: float | None = None
        if reconciliation.record_facts:
            defenses = [f.confidence for f in reconciliation.record_facts]
            record_strength = sum(defenses) / len(defenses) if defenses else 0.0
            contamination = 1.0 - record_strength
            # First order: the explicit number/record supplies deterministic structure.
            # Second order: R_D controls how strongly that number can defend D.
            record_raw_d = max(D, 0.95)
            record_effective_d = clamp01(record_raw_d * record_strength)
            D = record_effective_d
            drivers_d = tuple(drivers_d) + (
                Signal(
                    "D_RECORD_CONSTRAINT",
                    "D",
                    "Explicit recorded numeric value",
                    0.95 * record_strength,
                    len(reconciliation.record_facts),
                    tuple(f"{f.phrase} -> {f.value:g} (R_D={f.confidence:.2f})" for f in reconciliation.record_facts[:3]),
                    "The numeric record supplies first-order D; its defense is reduced by second-order uncertainty.",
                ),
            )
            if contamination > 0:
                drivers_p = tuple(drivers_p) + (
                    Signal(
                        "P_RECORD_UNCERTAINTY",
                        "P",
                        "Probabilistic contamination of numeric record",
                        contamination,
                        1,
                        (),
                        "U_D = 1 - R_D; probabilistic uncertainty weakens the math side's defense of determinism.",
                    ),
                )
        if reconciliation.has_comparison:
            coverage = max(coverage, reconciliation.comparison_coverage)
            if reconciliation.status in {ReconciliationStatus.CONFLICT, ReconciliationStatus.MIXED}:
                unresolved = tuple(dict.fromkeys(unresolved + ("semantic meaning conflicts with deterministic record",)))
            metadata = {
                **metadata,
                "semantic_reconciliation_status": reconciliation.status.value,
                "semantic_record_tension": reconciliation.semantic_record_tension,
                "comparison_coverage": reconciliation.comparison_coverage,
            }

        semantic_strength = reconciliation.semantic_determinization_strength
        record_defense = reconciliation.deterministic_defense_strength
        contamination = reconciliation.probabilistic_contamination
        raw_deterministic_strength = record_raw_d
        defended_deterministic_strength = record_effective_d
        if mode is ScoreMode.MATH:
            record_defense = metadata.get("deterministic_defense_strength", record_defense)
            contamination = metadata.get("probabilistic_contamination", contamination)
            raw_deterministic_strength = metadata.get("raw_deterministic_strength", raw_deterministic_strength)
            defended_deterministic_strength = D
        elif raw_deterministic_strength is None:
            raw_deterministic_strength = D
            defended_deterministic_strength = D

        vector = derive_vector(P, D, coverage)
        direction = self._direction(mode, obj.object_type)
        return VinculumResult.from_vector(
            obj=obj,
            mode=mode,
            direction=direction,
            P=clamp01(P),
            D=clamp01(D),
            coverage=clamp01(coverage),
            vector=vector,
            unresolved=unresolved,
            drivers_p=drivers_p,
            drivers_d=drivers_d,
            children=child_results,
            metadata=metadata,
            reconciliation_status=reconciliation.status.value,
            semantic_record_tension=reconciliation.semantic_record_tension,
            comparison_coverage=reconciliation.comparison_coverage,
            reconciliation=reconciliation.to_dict(),
            semantic_determinization_strength=semantic_strength,
            deterministic_defense_strength=record_defense,
            probabilistic_contamination=contamination,
            raw_deterministic_strength=raw_deterministic_strength,
            defended_deterministic_strength=defended_deterministic_strength,
            boundary_low=self.config.boundary_low,
            boundary_high=self.config.boundary_high,
            minimum_coverage=self.config.minimum_coverage,
        )

    def score_text(self, text: str, *, object_id: str = "claim", object_type: ObjectType = ObjectType.CLAIM, mode: ScoreMode = ScoreMode.AUTO) -> VinculumResult:
        from .ingest import ingest_text
        return self.score(ingest_text(text, object_id=object_id, object_type=object_type, mode=mode))

    def _resolve_mode(self, obj: VinculumObject) -> ScoreMode:
        if obj.mode is not ScoreMode.AUTO:
            return obj.mode
        if obj.object_type in {ObjectType.TTL_GRAPH, ObjectType.RDF_TRIPLE}:
            return ScoreMode.TTL
        if obj.object_type is ObjectType.MATH:
            return ScoreMode.MATH
        if obj.object_type in {ObjectType.DATASET, ObjectType.DATA_ROW}:
            return ScoreMode.STRUCTURED
        if isinstance(obj.content, (dict, list, tuple)):
            return ScoreMode.STRUCTURED
        return detect_mode(str(obj.content))

    def _score_own(self, obj: VinculumObject, mode: ScoreMode):
        if obj.object_type is ObjectType.RDF_TRIPLE:
            return score_ttl_triple(obj, self.config)
        if obj.object_type is ObjectType.TTL_GRAPH:
            return score_ttl_graph(obj, self.config)
        if mode is ScoreMode.MATH:
            return score_math(str(obj.content), self.config)
        if mode is ScoreMode.STRUCTURED:
            return score_structured(obj.content, self.config)
        if mode is ScoreMode.TTL:
            # Non-graph TTL fragments are treated as formal language fragments.
            return score_language(str(obj.content), self.config)
        return score_language(str(obj.content), self.config)

    def _aggregate_children(self, obj: VinculumObject, children: tuple[VinculumResult, ...]) -> tuple[float, float, float, float]:
        child_weights = {c.object_id: o.weight for c, o in zip(children, obj.children)}
        total = sum(child_weights.values())
        if total <= 0:
            return 0.0, 0.0, 0.0, 0.0
        P = sum(c.probabilistic_pressure * child_weights[c.object_id] for c in children) / total
        D = sum(c.deterministic_strength * child_weights[c.object_id] for c in children) / total
        coverage = sum(c.coverage * child_weights[c.object_id] for c in children) / total
        return P, D, coverage, total

    def _overlay_weight(self, obj: VinculumObject, children: tuple[VinculumResult, ...]) -> float:
        if not children:
            return 1.0
        if obj.object_type is ObjectType.TTL_GRAPH:
            return self.config.ttl_graph_overlay_weight
        return self.config.aggregate_parent_overlay_weight

    @staticmethod
    def _direction(mode: ScoreMode, object_type: ObjectType) -> str:
        if mode is ScoreMode.LANGUAGE:
            return "P→D"
        if mode is ScoreMode.MATH:
            return "D←P"
        if mode is ScoreMode.TTL or object_type in {ObjectType.TTL_GRAPH, ObjectType.RDF_TRIPLE}:
            return "FORMAL D↔P"
        if mode is ScoreMode.STRUCTURED:
            return "STRUCTURE D↔P"
        return "P↔D"
