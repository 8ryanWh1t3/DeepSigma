"""Tests for the RDF/SPARQL lattice query service.

Validates lattice-to-RDF serialization, SPARQL query
execution, Turtle export, and Trust Scorecard integration.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

rdflib = pytest.importorskip(
    "rdflib",
    reason=(
        "rdflib not installed — "
        "install with: pip install deepsigma[rdf]"
    ),
)

from credibility_engine.models import (  # noqa: E402
    Claim,
    CorrelationCluster,
    DriftEvent,
    make_default_claims,
    make_default_clusters,
)
from services.sparql_service import (  # noqa: E402
    DS,
    LatticeGraph,
    QueryResult,
    SPARQLService,
)


# ── Fixtures ───────────────────────────────────────────


@pytest.fixture
def sample_claims():
    return make_default_claims()


@pytest.fixture
def sample_clusters():
    return make_default_clusters()


@pytest.fixture
def sample_drift_events():
    return [
        DriftEvent(
            id="DRF-001",
            severity="red",
            fingerprint="fp-timing-east",
            category="timing_entropy",
            region="East",
            tier_impact=2,
        ),
        DriftEvent(
            id="DRF-002",
            severity="yellow",
            fingerprint="fp-freshness-central",
            category="freshness",
            region="Central",
            tier_impact=1,
        ),
        DriftEvent(
            id="DRF-003",
            severity="green",
            fingerprint="fp-bypass-west",
            category="bypass",
            region="West",
            tier_impact=0,
        ),
        DriftEvent(
            id="DRF-004",
            severity="red",
            fingerprint="fp-contention-east",
            category="contention",
            region="East",
            tier_impact=3,
        ),
    ]


@pytest.fixture
def populated_graph(
    sample_claims,
    sample_drift_events,
    sample_clusters,
):
    lg = LatticeGraph()
    lg.add_claims(sample_claims)
    lg.add_drift_events(sample_drift_events)
    lg.add_clusters(sample_clusters)
    # Link some drift to claims
    lg.link_drift_to_claim(
        "DRF-001", "CLM-T0-001",
    )
    lg.link_drift_to_claim(
        "DRF-004", "CLM-T0-002",
    )
    # Add evidence chains
    lg.link_evidence(
        "CLM-T0-001", "EV-001", "SRC-001",
    )
    lg.link_evidence(
        "CLM-T0-001", "EV-002", "SRC-002",
    )
    lg.link_evidence("CLM-T0-002", "EV-003")
    return lg


@pytest.fixture
def service(populated_graph):
    return SPARQLService(populated_graph)


# ── LatticeGraph tests ─────────────────────────────────


class TestLatticeGraph:
    def test_empty_graph(self):
        lg = LatticeGraph()
        assert lg.triple_count == 0

    def test_add_claims(self, sample_claims):
        lg = LatticeGraph()
        count = lg.add_claims(sample_claims)
        assert count == 5
        assert lg.triple_count > 0

    def test_add_drift_events(
        self, sample_drift_events,
    ):
        lg = LatticeGraph()
        count = lg.add_drift_events(
            sample_drift_events,
        )
        assert count == 4
        assert lg.triple_count > 0

    def test_add_clusters(self, sample_clusters):
        lg = LatticeGraph()
        count = lg.add_clusters(sample_clusters)
        assert count == 6
        assert lg.triple_count > 0

    def test_claim_triples(self, sample_claims):
        lg = LatticeGraph()
        lg.add_claims(sample_claims[:1])
        g = lg.graph
        # Should have rdf:type triple
        claim_uri = DS["claim/CLM-T0-001"]
        types = list(
            g.objects(claim_uri, rdflib.RDF.type),
        )
        assert DS.Claim in types

    def test_claim_confidence_typed(
        self, sample_claims,
    ):
        lg = LatticeGraph()
        lg.add_claims(sample_claims[:1])
        g = lg.graph
        claim_uri = DS["claim/CLM-T0-001"]
        confs = list(
            g.objects(claim_uri, DS.confidence),
        )
        assert len(confs) == 1
        assert float(confs[0]) == 0.94

    def test_drift_event_triples(
        self, sample_drift_events,
    ):
        lg = LatticeGraph()
        lg.add_drift_events(
            sample_drift_events[:1],
        )
        g = lg.graph
        uri = DS["drift/DRF-001"]
        types = list(
            g.objects(uri, rdflib.RDF.type),
        )
        assert DS.DriftEvent in types

    def test_cluster_sources_multi(
        self, sample_clusters,
    ):
        lg = LatticeGraph()
        lg.add_clusters(sample_clusters[:1])
        g = lg.graph
        uri = DS["cluster/CG-001"]
        sources = list(
            g.objects(uri, DS.hasSource),
        )
        assert len(sources) == 3

    def test_link_drift_to_claim(
        self, sample_claims, sample_drift_events,
    ):
        lg = LatticeGraph()
        lg.add_claims(sample_claims[:1])
        lg.add_drift_events(
            sample_drift_events[:1],
        )
        lg.link_drift_to_claim(
            "DRF-001", "CLM-T0-001",
        )
        g = lg.graph
        drift_uri = DS["drift/DRF-001"]
        affected = list(
            g.objects(drift_uri, DS.affectsClaim),
        )
        assert len(affected) == 1

    def test_link_evidence(self, sample_claims):
        lg = LatticeGraph()
        lg.add_claims(sample_claims[:1])
        lg.link_evidence(
            "CLM-T0-001", "EV-001", "SRC-001",
        )
        g = lg.graph
        claim_uri = DS["claim/CLM-T0-001"]
        evidences = list(
            g.objects(claim_uri, DS.hasEvidence),
        )
        assert len(evidences) == 1

    def test_link_evidence_no_source(
        self, sample_claims,
    ):
        lg = LatticeGraph()
        lg.add_claims(sample_claims[:1])
        lg.link_evidence("CLM-T0-001", "EV-X")
        g = lg.graph
        ev_uri = DS["evidence/EV-X"]
        sources = list(
            g.objects(ev_uri, DS.usesSource),
        )
        assert len(sources) == 0

    def test_graph_property(self):
        lg = LatticeGraph()
        assert lg.graph is not None


# ── SPARQLService tests ────────────────────────────────


class TestSPARQLService:
    def test_all_claims(self, service):
        result = service.all_claims()
        assert result.count == 5
        assert "claimId" in result.variables

    def test_all_drift(self, service):
        result = service.all_drift()
        assert result.count == 4

    def test_low_confidence_claims(self, service):
        # Default threshold 0.7 — all 5 claims
        # have confidence >= 0.88, so 0 returned
        result = service.low_confidence_claims(0.7)
        assert result.count == 0

    def test_low_confidence_with_high_threshold(
        self, service,
    ):
        # Threshold 0.92 catches claims with
        # confidence < 0.92
        result = service.low_confidence_claims(0.92)
        # CLM-T0-002 (0.88), CLM-T0-003 (0.90),
        # CLM-T0-005 (0.91) should match
        assert result.count == 3

    def test_evidence_chain(self, service):
        result = service.evidence_chain("CLM-T0-001")
        assert result.count == 2
        ids = {
            r["evidenceId"] for r in result.rows
        }
        assert "EV-001" in ids
        assert "EV-002" in ids

    def test_evidence_chain_with_source(
        self, service,
    ):
        result = service.evidence_chain("CLM-T0-001")
        sources = {
            r.get("sourceId") for r in result.rows
        }
        assert "SRC-001" in sources

    def test_drift_by_source(self, service):
        result = service.drift_by_source("East")
        assert result.count == 2
        ids = {r["driftId"] for r in result.rows}
        assert "DRF-001" in ids
        assert "DRF-004" in ids

    def test_drift_with_affected_claim(
        self, service,
    ):
        result = service.drift_by_source("East")
        claim_ids = {
            r.get("claimId")
            for r in result.rows
            if r.get("claimId")
        }
        assert "CLM-T0-001" in claim_ids

    def test_cluster_risk(self, service):
        result = service.cluster_risk()
        assert result.count == 6

    def test_graph_stats(self, service):
        result = service.graph_stats()
        assert result.count == 1
        row = result.rows[0]
        assert int(row["claimCount"]) == 5
        assert int(row["driftCount"]) == 4
        assert int(row["clusterCount"]) == 6

    def test_custom_query(self, service):
        sparql = """\
PREFIX ds: <https://deepsigma.ai/ns/coherence#>
SELECT (COUNT(?s) AS ?total)
WHERE { ?s a ds:Claim }
"""
        result = service.custom_query(
            "count_claims", sparql,
        )
        assert int(result.rows[0]["total"]) == 5

    def test_query_count_tracked(self, service):
        assert service.query_count == 0
        service.all_claims()
        service.all_drift()
        assert service.query_count == 2

    def test_avg_latency(self, service):
        service.all_claims()
        assert service.avg_latency_ms >= 0

    def test_query_result_structure(self, service):
        result = service.all_claims()
        assert isinstance(result, QueryResult)
        assert result.query_name == "all_claims"
        assert result.elapsed_ms >= 0
        assert len(result.variables) > 0
        assert result.count == len(result.rows)


# ── Export tests ───────────────────────────────────────


class TestExport:
    def test_turtle_export(self, service):
        ttl = service.export_turtle()
        assert "ds:Claim" in ttl or "coherence#Claim" in ttl
        assert len(ttl) > 100

    def test_ntriples_export(self, service):
        nt = service.export_ntriples()
        assert len(nt) > 100

    def test_turtle_roundtrip(self, service):
        """Export to Turtle, re-import, verify."""
        ttl = service.export_turtle()
        g2 = rdflib.Graph()
        g2.parse(data=ttl, format="turtle")
        # Should have same triple count
        original = service._lattice.triple_count
        assert len(g2) == original

    def test_turtle_contains_claims(
        self, service,
    ):
        ttl = service.export_turtle()
        assert "CLM-T0-001" in ttl
        assert "CLM-T0-005" in ttl

    def test_turtle_contains_drift(self, service):
        ttl = service.export_turtle()
        assert "DRF-001" in ttl


# ── Trust Scorecard integration ────────────────────────


class TestScorecardIntegration:
    def test_rdf_metrics_structure(self, service):
        metrics = service.rdf_metrics()
        assert "triple_count" in metrics
        assert "claim_count" in metrics
        assert "drift_count" in metrics
        assert "cluster_count" in metrics
        assert "queries_executed" in metrics
        assert "avg_query_latency_ms" in metrics

    def test_rdf_metrics_values(self, service):
        metrics = service.rdf_metrics()
        assert metrics["claim_count"] == 5
        assert metrics["drift_count"] == 4
        assert metrics["cluster_count"] == 6
        assert metrics["triple_count"] > 0

    def test_rdf_metrics_after_queries(
        self, service,
    ):
        service.all_claims()
        service.all_drift()
        metrics = service.rdf_metrics()
        # graph_stats() adds 1 more query
        assert metrics["queries_executed"] == 3
        assert metrics["avg_query_latency_ms"] >= 0


# ── Performance tests ──────────────────────────────────


@pytest.mark.benchmark
class TestPerformance:
    def test_10k_node_query_under_2s(self):
        """SPARQL queries < 2s for 10k-node lattice (CI-safe budget)."""
        lg = LatticeGraph()
        # Build 10k claims
        claims = [
            Claim(
                id=f"CLM-PERF-{i:05d}",
                title=f"Perf claim {i}",
                confidence=0.5 + (i % 50) / 100,
                region=["East", "Central", "West"][
                    i % 3
                ],
                domain=f"D{i % 10}",
            )
            for i in range(10_000)
        ]
        lg.add_claims(claims)
        svc = SPARQLService(lg)

        # Query: all claims
        start = time.monotonic()
        result = svc.all_claims()
        elapsed = time.monotonic() - start
        assert result.count == 10_000
        assert elapsed < 2.0, (
            f"all_claims took {elapsed:.2f}s "
            f"(SLO: <2s)"
        )

    def test_low_confidence_10k_under_2s(self):
        """Low confidence filter < 2s at scale (CI-safe budget)."""
        lg = LatticeGraph()
        claims = [
            Claim(
                id=f"CLM-LC-{i:05d}",
                title=f"LC claim {i}",
                confidence=0.3 + (i % 70) / 100,
                region="East",
                domain="D1",
            )
            for i in range(10_000)
        ]
        lg.add_claims(claims)
        svc = SPARQLService(lg)

        start = time.monotonic()
        result = svc.low_confidence_claims(0.7)
        elapsed = time.monotonic() - start
        assert result.count > 0
        assert elapsed < 2.0, (
            f"low_confidence took {elapsed:.2f}s "
            f"(SLO: <2s)"
        )

    def test_serialization_10k_under_5s(self):
        """Serializing 10k nodes to Turtle < 5s."""
        lg = LatticeGraph()
        claims = [
            Claim(
                id=f"CLM-SER-{i:05d}",
                title=f"Ser claim {i}",
                confidence=0.8,
                region="East",
                domain="D1",
            )
            for i in range(10_000)
        ]
        lg.add_claims(claims)
        svc = SPARQLService(lg)

        start = time.monotonic()
        ttl = svc.export_turtle()
        elapsed = time.monotonic() - start
        assert len(ttl) > 0
        assert elapsed < 5.0, (
            f"Turtle export took {elapsed:.2f}s "
            f"(SLO: <5s)"
        )


# ── Edge cases ─────────────────────────────────────────


class TestEdgeCases:
    def test_empty_graph_queries(self):
        lg = LatticeGraph()
        svc = SPARQLService(lg)
        result = svc.all_claims()
        assert result.count == 0

    def test_claim_with_none_confidence(self):
        lg = LatticeGraph()
        claim = Claim(
            id="CLM-NONE",
            title="No confidence",
            confidence=None,
        )
        lg.add_claims([claim])
        svc = SPARQLService(lg)
        result = svc.all_claims()
        assert result.count == 1

    def test_empty_correlation_group(self):
        lg = LatticeGraph()
        claim = Claim(
            id="CLM-EMPTY-CG",
            title="Empty CG",
            correlation_group="",
        )
        lg.add_claims([claim])
        assert lg.triple_count > 0

    def test_cluster_with_no_sources(self):
        lg = LatticeGraph()
        cluster = CorrelationCluster(
            id="CG-EMPTY",
            label="Empty cluster",
            sources=[],
            domains=[],
            regions=[],
        )
        lg.add_clusters([cluster])
        g = lg.graph
        uri = DS["cluster/CG-EMPTY"]
        sources = list(
            g.objects(uri, DS.hasSource),
        )
        assert len(sources) == 0

    def test_rdf_metrics_empty_graph(self):
        lg = LatticeGraph()
        svc = SPARQLService(lg)
        metrics = svc.rdf_metrics()
        assert metrics["claim_count"] == 0
        assert metrics["triple_count"] == 0
