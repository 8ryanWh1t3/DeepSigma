import numpy as np

from pyovis.embedder import HashEmbedder


def test_hash_embedder_is_deterministic_and_normalized():
    emb = HashEmbedder(dim=64)
    a = emb.embed_text("hello")
    b = emb.embed_text("hello")
    assert np.allclose(a, b)
    assert np.isclose(np.linalg.norm(a), 1.0)
