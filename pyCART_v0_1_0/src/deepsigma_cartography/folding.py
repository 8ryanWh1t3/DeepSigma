"""Reversible display grouping. A folded group graph is never a navigation graph."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .atlas import Atlas, MapView
from .util import Record, ValidationError, canonical_json, digest


@dataclass(frozen=True)
class FoldGroup(Record):
    id: str
    label: str
    member_ids: tuple[str, ...]
    states: tuple[str, ...]


@dataclass(frozen=True)
class FoldLink(Record):
    source_group: str
    predicate: str
    target_group: str
    status: str
    edge_ids: tuple[str, ...]
    internal: bool


@dataclass(frozen=True)
class FoldedMap(Record):
    by: str
    groups: tuple[FoldGroup, ...]
    links: tuple[FoldLink, ...]
    source_view: MapView
    source_view_fingerprint: str
    summary_only: bool = True
    warning: str = "Group adjacency can imply false transitive routes. Navigate only the original MapView."

    def unfold(self) -> MapView:
        if self.source_view.fingerprint != self.source_view_fingerprint:
            raise ValidationError("Fold source fingerprint mismatch")
        return self.source_view

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FoldedMap:
        try:
            raw = dict(data["source_view"])
            raw["atlas"] = Atlas.from_dict(raw["atlas"])
            if raw.get("scopes") is not None:
                raw["scopes"] = tuple(raw["scopes"])
            if raw.get("layers") is not None:
                raw["layers"] = tuple(raw["layers"])
            source = MapView(**raw)
            rebuilt = fold(source, by=data["by"])
            if canonical_json(rebuilt) != canonical_json(data):
                raise ValidationError("Fold summary or source was altered")
            return rebuilt
        except (KeyError, TypeError) as exc:
            raise ValidationError(f"Malformed fold: {exc}") from exc


def fold(view: MapView, *, by: str = "layer") -> FoldedMap:
    """Group every node and retain every original edge, including internal edges."""
    if not isinstance(view, MapView):
        raise ValidationError("fold requires a MapView")
    if by not in ("layer", "scope", "kind"):
        raise ValidationError("by must be layer, scope, or kind")
    members: dict[str, list] = defaultdict(list)
    for node in view.nodes:
        members[getattr(node, by)].append(node)
    groups = tuple(FoldGroup("group:" + digest([by, label])[:24], label,
                             tuple(n.id for n in nodes), tuple(sorted({n.status.value for n in nodes})))
                   for label, nodes in sorted(members.items()))
    membership = {nid: group.id for group in groups for nid in group.member_ids}
    links: dict[tuple, list] = defaultdict(list)
    for edge in view.edges:
        key = (membership[edge.source], edge.predicate, membership[edge.target], edge.status.value)
        links[key].append(edge.id)
    result = tuple(FoldLink(*key, tuple(sorted(ids)), key[0] == key[2]) for key, ids in sorted(links.items()))
    return FoldedMap(by, groups, result, view, view.fingerprint)
