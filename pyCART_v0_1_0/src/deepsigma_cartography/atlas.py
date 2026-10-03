"""Immutable semantic atlas and explicit, time-bound analytical projections."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping

from .models import DEFAULT_PREDICATES, Edge, Evidence, Node, Predicate, Status, active
from .util import SCHEMA, Record, ValidationError, canonical_json, digest, freeze, parse_json, strings, text, timestamp


def _indexed(records: Any, cls: type, label: str) -> tuple[tuple, Mapping]:
    if not isinstance(records, (tuple, list)) or not all(isinstance(r, cls) for r in records):
        raise ValidationError(f"{label} must be a sequence of {cls.__name__} records")
    result = tuple(sorted(records, key=lambda r: r.id))
    index = {r.id: r for r in result}
    if len(result) != len(index):
        raise ValidationError(f"Duplicate {label} ID")
    return result, MappingProxyType(index)


@dataclass(frozen=True)
class Atlas(Record):
    id: str
    title: str
    nodes: tuple[Node, ...] = ()
    edges: tuple[Edge, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    predicates: tuple[Predicate, ...] = DEFAULT_PREDICATES
    attributes: Mapping[str, Any] = field(default_factory=dict)
    schema: str = SCHEMA
    _nodes: Mapping[str, Node] = field(init=False, repr=False, compare=False)
    _edges: Mapping[str, Edge] = field(init=False, repr=False, compare=False)
    _evidence: Mapping[str, Evidence] = field(init=False, repr=False, compare=False)
    _predicates: Mapping[str, Predicate] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        text(self.id, "id")
        text(self.title, "title")
        if self.schema != SCHEMA:
            raise ValidationError(f"Unsupported atlas schema: {self.schema}")
        for name, cls in (("nodes", Node), ("edges", Edge), ("evidence", Evidence), ("predicates", Predicate)):
            records, index = _indexed(getattr(self, name), cls, name)
            object.__setattr__(self, name, records)
            object.__setattr__(self, "_" + name, index)
        if not isinstance(self.attributes, Mapping):
            raise ValidationError("attributes must be a JSON object")
        object.__setattr__(self, "attributes", freeze(self.attributes))
        ids = [x.id for collection in (self.nodes, self.edges, self.evidence) for x in collection]
        if len(set(ids)) != len(ids):
            raise ValidationError("Node, edge, and evidence IDs must be globally distinct")
        for record in (*self.nodes, *self.edges):
            if set(record.evidence_ids) - self._evidence.keys():
                raise ValidationError(f"Unresolved evidence ID on {record.id}")
        for edge in self.edges:
            if edge.source not in self._nodes or edge.target not in self._nodes:
                raise ValidationError(f"Dangling endpoint on edge {edge.id}")
            if edge.predicate not in self._predicates:
                raise ValidationError(f"Unknown predicate {edge.predicate}; declare it in the legend")
            predicate = self._predicates[edge.predicate]
            if predicate.source_kinds and self._nodes[edge.source].kind not in predicate.source_kinds:
                raise ValidationError(f"Invalid source kind on edge {edge.id}")
            if predicate.target_kinds and self._nodes[edge.target].kind not in predicate.target_kinds:
                raise ValidationError(f"Invalid target kind on edge {edge.id}")

    @property
    def fingerprint(self) -> str:
        return digest(self)

    def node(self, node_id: str) -> Node:
        try:
            return self._nodes[node_id]
        except KeyError as exc:
            raise ValidationError(f"Node not represented: {node_id}") from exc

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Atlas:
        if not isinstance(data, Mapping):
            raise ValidationError("Atlas must be a JSON object")
        if data.get("schema") != SCHEMA:
            raise ValidationError("Missing or unsupported atlas schema")
        value = dict(data)
        try:
            for name, record_type in (("nodes", Node), ("edges", Edge), ("evidence", Evidence), ("predicates", Predicate)):
                if name not in value or not isinstance(value[name], (list, tuple)):
                    raise ValidationError(f"Missing or invalid {name} array")
                value[name] = tuple(record_type(**item) for item in value[name])
            return cls(**value)
        except (TypeError, KeyError) as exc:
            raise ValidationError(f"Invalid atlas field: {exc}") from exc

    @classmethod
    def load(cls, path: str | Path) -> Atlas:
        return cls.from_dict(parse_json(Path(path).read_text(encoding="utf-8")))

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_text(canonical_json(self) + "\n", encoding="utf-8")
        return path

    def view(self, *, as_of: str, scopes: tuple[str, ...] | None = None,
             layers: tuple[str, ...] | None = None, include_inferred: bool = True) -> MapView:
        """Create an analytical slice. Scope/layer selection is NOT access control."""
        if type(include_inferred) is not bool:
            raise ValidationError("include_inferred must be a boolean")
        for name, value in (("scopes", scopes), ("layers", layers)):
            if value is not None and (not isinstance(value, (list, tuple)) or not all(isinstance(x, str) for x in value)):
                raise ValidationError(f"{name} must be a string sequence or None")
        as_of = timestamp(as_of)
        nodes = tuple(n for n in self.nodes if active(n, as_of) and
                      (scopes is None or n.scope in scopes) and
                      (layers is None or n.layer in layers) and
                      (include_inferred or n.status != Status.INFERRED))
        ids = {n.id for n in nodes}
        edges = tuple(e for e in self.edges if e.source in ids and e.target in ids and active(e, as_of) and
                      (include_inferred or e.status != Status.INFERRED))
        used_evidence = {eid for item in (*nodes, *edges) for eid in item.evidence_ids}
        projection = Atlas(self.id, self.title, nodes, edges,
                           tuple(e for e in self.evidence if e.id in used_evidence),
                           self.predicates, self.attributes)
        return MapView(projection, as_of, self.fingerprint,
                       tuple(sorted(scopes)) if scopes is not None else None,
                       tuple(sorted(layers)) if layers is not None else None, include_inferred)


@dataclass(frozen=True)
class MapView(Record):
    atlas: Atlas
    as_of: str
    source_fingerprint: str
    scopes: tuple[str, ...] | None = None
    layers: tuple[str, ...] | None = None
    include_inferred: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.atlas, Atlas):
            raise ValidationError("MapView requires an Atlas")
        object.__setattr__(self, "as_of", timestamp(self.as_of))
        if not isinstance(self.source_fingerprint, str) or not re.fullmatch(r"[a-f0-9]{64}", self.source_fingerprint):
            raise ValidationError("source_fingerprint must be a SHA-256 digest")
        if type(self.include_inferred) is not bool:
            raise ValidationError("include_inferred must be a boolean")
        for name in ("scopes", "layers"):
            if getattr(self, name) is not None:
                object.__setattr__(self, name, strings(getattr(self, name), name))
        for node in self.atlas.nodes:
            if not active(node, self.as_of) or (self.scopes is not None and node.scope not in self.scopes) or (self.layers is not None and node.layer not in self.layers):
                raise ValidationError("Node violates the MapView temporal/scope contract")
        for record in (*self.atlas.nodes, *self.atlas.edges):
            if not active(record, self.as_of) or (not self.include_inferred and record.status == Status.INFERRED):
                raise ValidationError("Record violates the MapView temporal/status contract")

    @property
    def fingerprint(self) -> str:
        return digest(self)

    @property
    def nodes(self) -> tuple[Node, ...]:
        return self.atlas.nodes

    @property
    def edges(self) -> tuple[Edge, ...]:
        return self.atlas.edges

    def node(self, node_id: str) -> Node:
        return self.atlas.node(node_id)
