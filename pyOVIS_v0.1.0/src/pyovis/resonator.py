from __future__ import annotations

import json
from pathlib import Path

from .schemas import CandidateEdge
from .store import SemanticStore


def _prov(obj) -> dict:
    return {
        "uri": obj.uri,
        "sha256": obj.sha256,
        "modality": obj.modality,
        "page": obj.page,
    }


def build_candidate_edges(
    store: SemanticStore, threshold: float = 0.70, top_k: int = 5
) -> list[CandidateEdge]:
    edges: list[CandidateEdge] = []
    seen: set[tuple[str, str]] = set()
    for source_id, *_rest, vec in store.iter_vectors():
        source = store.get_object(source_id)
        if source is None:
            continue
        for hit in store.search(vec, top_k=top_k, exclude_id=source_id):
            if hit.score < threshold:
                continue
            pair = tuple(sorted((source_id, hit.object_id)))
            if pair in seen:
                continue
            seen.add(pair)
            target = store.get_object(hit.object_id)
            if target is None:
                continue
            edges.append(
                CandidateEdge(
                    source=source_id,
                    candidate=hit.object_id,
                    similarity=round(hit.score, 6),
                    source_provenance=_prov(source),
                    candidate_provenance=_prov(target),
                )
            )
    edges.sort(key=lambda e: e.similarity, reverse=True)
    return edges


def export_candidate_edges(
    store: SemanticStore, output: Path, threshold: float = 0.70, top_k: int = 5
) -> int:
    edges = build_candidate_edges(store, threshold=threshold, top_k=top_k)
    output.write_text(
        json.dumps([edge.to_dict() for edge in edges], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return len(edges)
