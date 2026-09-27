import numpy as np

from pyovis.resonator import build_candidate_edges
from pyovis.schemas import SemanticObject
from pyovis.store import SemanticStore


def make(oid):
    return SemanticObject(oid, "text", f"file:///{oid}", oid, 1, 1, text=oid)


def test_candidate_edges_never_authoritative(tmp_path):
    store = SemanticStore(tmp_path / "x.db")
    store.initialize()
    store.upsert(make("A"), np.array([1.0, 0.0], dtype=np.float32), "test", "m")
    store.upsert(make("B"), np.array([0.99, 0.01], dtype=np.float32), "test", "m")
    edges = build_candidate_edges(store, threshold=0.9, top_k=2)
    assert edges
    assert all(e.relationship == "UNRESOLVED" for e in edges)
    assert all(e.authoritative is False for e in edges)
    assert all(e.requires_resonator is True for e in edges)
