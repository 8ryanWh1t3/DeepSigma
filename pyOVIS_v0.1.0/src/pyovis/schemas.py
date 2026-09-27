from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SemanticObject:
    id: str
    modality: str
    uri: str
    sha256: str
    size_bytes: int
    mtime_ns: int
    text: str | None = None
    page: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SearchHit:
    object_id: str
    score: float
    modality: str
    uri: str
    text: str | None
    metadata: dict[str, Any]


@dataclass
class CandidateEdge:
    source: str
    candidate: str
    similarity: float
    relationship: str = "UNRESOLVED"
    authoritative: bool = False
    requires_resonator: bool = True
    discovered_by: str = "pyOVIS"
    discovery_method: str = "OVIS_OMNI_EMBEDDING_COSINE"
    source_provenance: dict[str, Any] = field(default_factory=dict)
    candidate_provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["type"] = "SemanticCandidateEdge"
        return out
