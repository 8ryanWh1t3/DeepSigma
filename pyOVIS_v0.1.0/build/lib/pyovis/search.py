from __future__ import annotations

from dataclasses import dataclass

from .store import SemanticStore


@dataclass
class Residual:
    object_id: str
    nearest_id: str | None
    nearest_score: float | None


def find_residuals(store: SemanticStore, threshold: float = 0.45) -> list[Residual]:
    results: list[Residual] = []
    for oid, *_rest, vec in store.iter_vectors():
        hits = store.search(vec, top_k=1, exclude_id=oid)
        if not hits:
            results.append(Residual(oid, None, None))
        elif hits[0].score < threshold:
            results.append(Residual(oid, hits[0].object_id, hits[0].score))
    return results
