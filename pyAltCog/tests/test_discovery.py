from pyaltcog.discovery import (
    assumption_dependence,
    cross_domain_analogy,
    cross_source_contradiction,
    edge_case_accumulation,
    outcome_mismatch,
    repeated_exception,
    residual_evidence,
)
from pyaltcog.models import DiscoverySurface


def test_outcome_mismatch_only_when_different():
    assert outcome_mismatch(1, 1) is None
    d = outcome_mismatch(1, 2)
    assert d and d.surface == DiscoverySurface.OUTCOME_MISMATCH


def test_numeric_residual_respects_tolerance():
    assert residual_evidence(10, 9.9, tolerance=0.2) is None
    d = residual_evidence(10, 8, tolerance=0.2)
    assert d and d.metadata["residual"] == 2


def test_repeated_exception_threshold():
    assert repeated_exception(1, minimum_occurrences=2) is None
    assert repeated_exception(3, minimum_occurrences=2) is not None


def test_cross_source_contradiction():
    assert cross_source_contradiction("A", "x", "B", "x") is None
    d = cross_source_contradiction("A", "x", "B", "y")
    assert d and d.surface == DiscoverySurface.CROSS_SOURCE_CONTRADICTION


def test_assumption_dependence():
    assert assumption_dependence("a", "go", "go") is None
    assert assumption_dependence("a", "go", "stop") is not None


def test_edge_case_accumulation():
    assert edge_case_accumulation(["a", "b"], minimum_cases=3) is None
    assert edge_case_accumulation(["a", "b", "c"], minimum_cases=3) is not None


def test_cross_domain_analogy():
    d = cross_domain_analogy(
        "queue congestion causes latency", "network queue congestion creates latency",
        tags_a=["queue"], tags_b=["queue"], minimum_similarity=0.2,
    )
    assert d and d.surface == DiscoverySurface.CROSS_DOMAIN_ANALOGY
