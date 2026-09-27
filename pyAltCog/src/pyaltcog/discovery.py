from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from .models import DiscoverySurface
from .text import feature_terms, jaccard


@dataclass(frozen=True)
class SignalDraft:
    """Structured, pre-ID discovery output suitable for AltCogEngine.capture_friction()."""

    surface: DiscoverySurface
    statement: str
    strength: float
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None


def outcome_mismatch(expected: Any, observed: Any, *, tags: Iterable[str] = ()) -> Optional[SignalDraft]:
    """Create an outcome-mismatch signal when structured expected and observed values differ."""
    if expected == observed:
        return None
    return SignalDraft(
        surface=DiscoverySurface.OUTCOME_MISMATCH,
        statement=f"Expected {expected!r}; observed {observed!r}.",
        strength=0.80,
        tags=tuple(sorted(set(tags) | {"expected-vs-observed"})),
        metadata={"expected": expected, "observed": observed},
    )


def residual_evidence(
    observed: float,
    explained: float,
    *,
    tolerance: float = 0.0,
    tags: Iterable[str] = (),
) -> Optional[SignalDraft]:
    """Create a residual signal when |observed - explained| exceeds tolerance."""
    residual = observed - explained
    if abs(residual) <= tolerance:
        return None
    denominator = max(abs(observed), abs(explained), 1.0)
    strength = min(1.0, max(0.55, abs(residual) / denominator))
    return SignalDraft(
        surface=DiscoverySurface.RESIDUAL_EVIDENCE,
        statement=f"Residual evidence detected: observed={observed}, explained={explained}, residual={residual}.",
        strength=strength,
        tags=tuple(sorted(set(tags) | {"residual"})),
        metadata={"observed": observed, "explained": explained, "residual": residual, "tolerance": tolerance},
    )


def repeated_exception(
    occurrences: int,
    *,
    minimum_occurrences: int = 2,
    description: str = "repeated exception",
    tags: Iterable[str] = (),
) -> Optional[SignalDraft]:
    if occurrences < minimum_occurrences:
        return None
    strength = min(1.0, 0.50 + 0.10 * occurrences)
    return SignalDraft(
        surface=DiscoverySurface.REPEATED_EXCEPTION,
        statement=f"{description}: {occurrences} occurrences (threshold {minimum_occurrences}).",
        strength=strength,
        tags=tuple(sorted(set(tags) | {"repeated-exception"})),
        metadata={"occurrences": occurrences, "minimum_occurrences": minimum_occurrences},
    )


def cross_source_contradiction(
    source_a: str,
    value_a: Any,
    source_b: str,
    value_b: Any,
    *,
    tags: Iterable[str] = (),
) -> Optional[SignalDraft]:
    if value_a == value_b:
        return None
    return SignalDraft(
        surface=DiscoverySurface.CROSS_SOURCE_CONTRADICTION,
        statement=f"{source_a} reports {value_a!r}; {source_b} reports {value_b!r}.",
        strength=0.85,
        tags=tuple(sorted(set(tags) | {"source-contradiction"})),
        metadata={"source_a": source_a, "value_a": value_a, "source_b": source_b, "value_b": value_b},
    )


def assumption_dependence(
    assumption: str,
    conclusion_with_assumption: Any,
    conclusion_without_assumption: Any,
    *,
    tags: Iterable[str] = (),
) -> Optional[SignalDraft]:
    """Detect a load-bearing assumption by structured counterfactual comparison."""
    if conclusion_with_assumption == conclusion_without_assumption:
        return None
    return SignalDraft(
        surface=DiscoverySurface.ASSUMPTION_DEPENDENCE,
        statement=f"Conclusion changes when assumption is removed or inverted: {assumption}",
        strength=0.82,
        tags=tuple(sorted(set(tags) | {"load-bearing-assumption"})),
        metadata={
            "assumption": assumption,
            "with_assumption": conclusion_with_assumption,
            "without_assumption": conclusion_without_assumption,
        },
    )


def edge_case_accumulation(
    cases: Iterable[str],
    *,
    minimum_cases: int = 3,
    tags: Iterable[str] = (),
) -> Optional[SignalDraft]:
    items = [c for c in cases if str(c).strip()]
    if len(items) < minimum_cases:
        return None
    return SignalDraft(
        surface=DiscoverySurface.EDGE_CASE_ACCUMULATION,
        statement=f"Edge-case accumulation reached {len(items)} cases; rare behavior may be becoming structurally relevant.",
        strength=min(1.0, 0.55 + 0.08 * len(items)),
        tags=tuple(sorted(set(tags) | {"edge-case"})),
        metadata={"cases": items, "minimum_cases": minimum_cases},
    )


def cross_domain_analogy(
    pattern_a: str,
    pattern_b: str,
    *,
    tags_a: Iterable[str] = (),
    tags_b: Iterable[str] = (),
    minimum_similarity: float = 0.25,
) -> Optional[SignalDraft]:
    similarity = jaccard(feature_terms(pattern_a, tags_a), feature_terms(pattern_b, tags_b))
    if similarity < minimum_similarity:
        return None
    return SignalDraft(
        surface=DiscoverySurface.CROSS_DOMAIN_ANALOGY,
        statement=f"Cross-domain structural analogy detected between '{pattern_a}' and '{pattern_b}'.",
        strength=min(1.0, 0.50 + similarity / 2),
        tags=tuple(sorted(set(tags_a) | set(tags_b) | {"cross-domain-analogy"})),
        metadata={"similarity": similarity, "pattern_a": pattern_a, "pattern_b": pattern_b},
    )
