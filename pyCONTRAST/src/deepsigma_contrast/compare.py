from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import (
    Assumption,
    ContrastResult,
    Delta,
    DiscriminatingFactor,
    Episode,
)
from .scorer import (
    contrast_confidence,
    lexical_episode_similarity,
    metric_distance,
    normalize_text,
    structural_episode_similarity,
    weighted_similarity,
)


def _materiality_for_confidence_change(prior: float, current: float) -> float:
    return min(1.0, abs(prior - current))


def _assumption_index(episode: Episode) -> dict[str, Assumption]:
    return {a.id: a for a in episode.assumptions}


def _delta(kind: str, key: str, prior: Any, current: Any, materiality: float, rationale: str) -> Delta:
    return Delta(
        kind=kind,
        key=key,
        prior=prior,
        current=current,
        materiality=round(max(0.0, min(1.0, materiality)), 6),
        rationale=rationale,
    )


@dataclass
class ContrastEngine:
    materiality_threshold: float = 0.20

    def compare(self, *, current_episode: Episode, prior_episode: Episode) -> ContrastResult:
        lexical = lexical_episode_similarity(current_episode, prior_episode)
        structural = structural_episode_similarity(current_episode, prior_episode)
        similarity = weighted_similarity(lexical, structural)

        assumption_deltas = self._compare_assumptions(prior_episode, current_episode)
        outcome_deltas = self._compare_outcomes(prior_episode, current_episode)
        evidence_deltas = self._compare_evidence(prior_episode, current_episode)
        metadata_deltas = self._compare_metadata(prior_episode, current_episode)

        all_deltas = assumption_deltas + outcome_deltas + evidence_deltas + metadata_deltas
        material = tuple(
            f"{d.kind}:{d.key} — {d.rationale}"
            for d in all_deltas
            if d.materiality >= self.materiality_threshold
        )
        factors = self._discriminating_factors(all_deltas, current_episode, prior_episode)
        confidence = contrast_confidence(current_episode, prior_episode, similarity)

        return ContrastResult(
            current_episode_id=current_episode.id,
            prior_episode_id=prior_episode.id,
            similarity=similarity,
            structural_similarity=round(structural, 6),
            lexical_similarity=round(lexical, 6),
            assumption_deltas=tuple(assumption_deltas),
            outcome_deltas=tuple(outcome_deltas),
            evidence_deltas=tuple(evidence_deltas),
            metadata_deltas=tuple(metadata_deltas),
            material_differences=material,
            discriminating_factors=tuple(factors),
            confidence=confidence,
            advisory_only=True,
        )

    def _compare_assumptions(self, prior: Episode, current: Episode) -> list[Delta]:
        before = _assumption_index(prior)
        after = _assumption_index(current)
        deltas: list[Delta] = []
        for key in sorted(before.keys() | after.keys()):
            p, c = before.get(key), after.get(key)
            if p is None:
                deltas.append(_delta(
                    "ASSUMPTION_ADDED", key, None, c.statement, 0.70,
                    "A new assumption entered the current episode."
                ))
                continue
            if c is None:
                deltas.append(_delta(
                    "ASSUMPTION_REMOVED", key, p.statement, None, 0.80,
                    "A prior load-bearing assumption is absent from the current episode."
                ))
                continue

            text_changed = normalize_text(p.statement) != normalize_text(c.statement)
            status_changed = p.status != c.status
            confidence_change = _materiality_for_confidence_change(p.confidence, c.confidence)
            expiry_changed = p.expires_at != c.expires_at

            if text_changed:
                deltas.append(_delta(
                    "ASSUMPTION_TEXT_CHANGED", key, p.statement, c.statement, 0.85,
                    "The meaning of a shared assumption changed."
                ))
            if status_changed:
                deltas.append(_delta(
                    "ASSUMPTION_STATUS_CHANGED", key, p.status, c.status, 0.90,
                    "The lifecycle state of a shared assumption changed."
                ))
            if confidence_change > 0:
                deltas.append(_delta(
                    "ASSUMPTION_CONFIDENCE_CHANGED", key, p.confidence, c.confidence,
                    confidence_change,
                    "Confidence in the assumption changed."
                ))
            if expiry_changed:
                deltas.append(_delta(
                    "ASSUMPTION_EXPIRY_CHANGED", key, p.expires_at, c.expires_at, 0.55,
                    "The assumption validity horizon changed."
                ))
        return deltas

    def _compare_outcomes(self, prior: Episode, current: Episode) -> list[Delta]:
        if prior.outcome is None and current.outcome is None:
            return []
        if prior.outcome is None:
            return [_delta("OUTCOME_ADDED", "outcome", None, current.outcome.status, 0.70,
                           "The current episode contains an observed outcome.")]
        if current.outcome is None:
            return [_delta("OUTCOME_MISSING", "outcome", prior.outcome.status, None, 0.85,
                           "The prior episode has an outcome but the current episode does not.")]

        deltas: list[Delta] = []
        if prior.outcome.status != current.outcome.status:
            deltas.append(_delta(
                "OUTCOME_STATUS_CHANGED", "status",
                prior.outcome.status, current.outcome.status, 1.0,
                "The observed outcome class changed."
            ))
        distance = metric_distance(prior.outcome.metrics, current.outcome.metrics)
        if distance > 0:
            deltas.append(_delta(
                "OUTCOME_METRICS_CHANGED", "metrics",
                dict(prior.outcome.metrics), dict(current.outcome.metrics), distance,
                "Outcome measurements changed."
            ))
        if normalize_text(prior.outcome.summary) != normalize_text(current.outcome.summary):
            deltas.append(_delta(
                "OUTCOME_SUMMARY_CHANGED", "summary",
                prior.outcome.summary, current.outcome.summary, 0.40,
                "The outcome narrative changed."
            ))
        return deltas

    def _compare_evidence(self, prior: Episode, current: Episode) -> list[Delta]:
        p = {e.id: e for e in prior.evidence}
        c = {e.id: e for e in current.evidence}
        deltas: list[Delta] = []
        for key in sorted(p.keys() | c.keys()):
            before, after = p.get(key), c.get(key)
            if before is None:
                deltas.append(_delta(
                    "EVIDENCE_ADDED", key, None, after.uri or after.id, 0.60,
                    "New evidence was introduced."
                ))
            elif after is None:
                deltas.append(_delta(
                    "EVIDENCE_REMOVED", key, before.uri or before.id, None, 0.65,
                    "Previously available evidence is absent."
                ))
            else:
                if before.supports != after.supports:
                    deltas.append(_delta(
                        "EVIDENCE_STANCE_CHANGED", key, before.supports, after.supports, 0.95,
                        "The same evidence changed from supporting to contradicting, or vice versa."
                    ))
                if before.weight != after.weight:
                    deltas.append(_delta(
                        "EVIDENCE_WEIGHT_CHANGED", key, before.weight, after.weight,
                        abs(before.weight - after.weight),
                        "The assessed strength of shared evidence changed."
                    ))
        return deltas

    def _compare_metadata(self, prior: Episode, current: Episode) -> list[Delta]:
        deltas: list[Delta] = []
        for key in sorted(set(prior.metadata) | set(current.metadata)):
            p = prior.metadata.get(key)
            c = current.metadata.get(key)
            if p != c:
                deltas.append(_delta(
                    "CONTEXT_CHANGED", key, p, c, 0.45,
                    "A contextual variable differs between the episodes."
                ))
        return deltas

    def _discriminating_factors(
        self,
        deltas: list[Delta],
        current: Episode,
        prior: Episode,
    ) -> list[DiscriminatingFactor]:
        ranked = sorted(
            (d for d in deltas if d.materiality >= self.materiality_threshold),
            key=lambda x: (-x.materiality, x.kind, x.key),
        )
        current_evidence = tuple(sorted(e.id for e in current.evidence))
        prior_evidence = tuple(sorted(e.id for e in prior.evidence))
        evidence_ids = tuple(sorted(set(current_evidence) | set(prior_evidence)))

        return [
            DiscriminatingFactor(
                key=f"{d.kind}:{d.key}",
                description=d.rationale,
                weight=d.materiality,
                evidence_ids=evidence_ids,
            )
            for d in ranked[:12]
        ]
