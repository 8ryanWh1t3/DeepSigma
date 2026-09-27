from __future__ import annotations

from typing import Protocol, Sequence


class EmbeddingAdapter(Protocol):
    """Optional adapter only. The core library never requires embeddings."""

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        ...


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Vectors must have equal dimensions.")
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
