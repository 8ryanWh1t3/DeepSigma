import numpy as np

from pyovis.schemas import SemanticObject
from pyovis.search import find_residuals
from pyovis.store import SemanticStore


def make(oid):
    return SemanticObject(oid, "text", f"file:///{oid}", oid, 1, 1, text=oid)


def test_residual_detection(tmp_path):
    store = SemanticStore(tmp_path / "x.db")
    store.initialize()
    store.upsert(make("A"), np.array([1.0, 0.0], dtype=np.float32), "test", "m")
    store.upsert(make("B"), np.array([0.99, 0.01], dtype=np.float32), "test", "m")
    store.upsert(make("C"), np.array([0.0, 1.0], dtype=np.float32), "test", "m")
    residuals = find_residuals(store, threshold=0.5)
    ids = {r.object_id for r in residuals}
    assert "C" in ids
