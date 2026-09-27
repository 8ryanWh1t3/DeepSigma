import numpy as np

from pyovis.schemas import SemanticObject
from pyovis.store import SemanticStore


def obj(oid, text):
    return SemanticObject(oid, "text", f"file:///{oid}.txt", oid.lower(), 10, 1, text=text)


def test_store_roundtrip_and_search(tmp_path):
    store = SemanticStore(tmp_path / "x.db")
    store.initialize()
    store.upsert(obj("A", "alpha"), np.array([1.0, 0.0], dtype=np.float32), "test", "m")
    store.upsert(obj("B", "beta"), np.array([0.9, 0.1], dtype=np.float32), "test", "m")
    store.upsert(obj("C", "gamma"), np.array([0.0, 1.0], dtype=np.float32), "test", "m")
    hits = store.search(np.array([1.0, 0.0], dtype=np.float32), top_k=2)
    assert [h.object_id for h in hits] == ["A", "B"]
    assert store.count() == 3
