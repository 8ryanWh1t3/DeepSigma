from pyaltcog.clustering import cluster_signals
from pyaltcog.models import DiscoverySurface, FrictionSignalRecord


def sig(i, text, tags, stream="S", domain="D"):
    return FrictionSignalRecord(
        id=f"FSR-{i}", stream_id=stream, surface=DiscoverySurface.REPEATED_EXCEPTION,
        statement=text, source="x", detected_at="2026-01-01T00:00:00+00:00",
        strength=0.8, tags=tags, domain=domain,
    )


def test_similar_signals_cluster():
    a = sig(1, "identity reset after sensor handoff", ["handoff", "identity"])
    b = sig(2, "repeated identity reset following handoff", ["handoff", "identity"])
    clusters = cluster_signals([a, b], min_similarity=0.2, created_at="t")
    assert len(clusters) == 1
    assert clusters[0].signal_ids == ["FSR-1", "FSR-2"]


def test_different_streams_do_not_cluster():
    a = sig(1, "same terms handoff reset", ["handoff"], stream="A")
    b = sig(2, "same terms handoff reset", ["handoff"], stream="B")
    assert len(cluster_signals([a, b], min_similarity=0.0, created_at="t")) == 2


def test_order_does_not_change_cluster_identity():
    a = sig(1, "identity reset handoff", ["handoff", "identity"])
    b = sig(2, "identity reset handoff", ["handoff", "identity"])
    x = cluster_signals([a, b], min_similarity=0.2, created_at="t")[0]
    y = cluster_signals([b, a], min_similarity=0.2, created_at="t")[0]
    assert x.id == y.id


def test_unrelated_signals_separate():
    a = sig(1, "sensor identity reset", ["sensor"])
    b = sig(2, "budget approval latency", ["budget"], domain="finance")
    assert len(cluster_signals([a, b], min_similarity=0.4, created_at="t")) == 2
