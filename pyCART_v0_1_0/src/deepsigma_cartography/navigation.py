"""PATHFINDER-oriented traversal. Paths describe recorded structure, not causality."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from .atlas import MapView
from .util import Record, ValidationError


@dataclass(frozen=True)
class Step(Record):
    edge_id: str
    predicate: str
    from_id: str
    to_id: str
    stored_source: str
    stored_target: str
    status: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class Route(Record):
    source: str
    target: str
    status: str
    steps: tuple[Step, ...]
    view_fingerprint: str
    as_of: str
    depth_limited: bool = False

    @property
    def found(self) -> bool:
        return self.status == "RECORDED_ROUTE"


@dataclass(frozen=True)
class Reachability(Record):
    start: str
    mode: str
    node_ids: tuple[str, ...]
    routes: tuple[Route, ...]
    depth_limited: bool
    view_fingerprint: str
    as_of: str
    interpretation: str = "Recorded structural reachability, not predicted failure or causal proof."


def _limit(max_depth: int | None) -> None:
    if max_depth is not None and (type(max_depth) is not int or max_depth < 0):
        raise ValidationError("max_depth must be a nonnegative integer or None")


def adjacency(view: MapView, direction: str = "out", predicates: tuple[str, ...] | None = None) -> dict[str, list[tuple[str, Any]]]:
    if not isinstance(view, MapView):
        raise ValidationError("Navigation requires a MapView, not a folded summary")
    if direction not in ("out", "in", "both", "dependencies", "impact"):
        raise ValidationError("direction must be out, in, both, dependencies, or impact")
    if predicates is not None:
        if not isinstance(predicates, (tuple, list)):
            raise ValidationError("predicates must be a sequence or None")
        if set(predicates) - view.atlas._predicates.keys():
            raise ValidationError("Unknown predicate filter")
    result: dict[str, list[tuple[str, Any]]] = {n.id: [] for n in view.nodes}
    for edge in view.edges:
        if predicates is not None and edge.predicate not in predicates:
            continue
        source, target = edge.source, edge.target
        if direction in ("dependencies", "impact"):
            orientation = view.atlas._predicates[edge.predicate].dependency
            if orientation == "none":
                continue
            if orientation == "reverse":
                source, target = target, source
            if direction == "impact":
                source, target = target, source
            result[source].append((target, edge))
        else:
            if direction in ("out", "both"):
                result[source].append((target, edge))
            if direction in ("in", "both"):
                result[target].append((source, edge))
    for rows in result.values():
        rows.sort(key=lambda x: (x[0], x[1].id))
    return result


def _search(view: MapView, source: str, direction: str, predicates: tuple[str, ...] | None,
            max_depth: int | None) -> tuple[dict, bool]:
    _limit(max_depth)
    graph = adjacency(view, direction, predicates)
    view.node(source)
    parents: dict[str, tuple[str, Any] | None] = {source: None}
    depth = {source: 0}
    queue = deque([source])
    frontier: set[str] = set()
    while queue:
        current = queue.popleft()
        if max_depth is not None and depth[current] >= max_depth:
            frontier.add(current)
            continue
        for nxt, edge in graph[current]:
            if nxt not in parents:
                parents[nxt] = (current, edge)
                depth[nxt] = depth[current] + 1
                queue.append(nxt)
    # A limit is meaningful only when a reachable neighbor was left unexplored.
    limited = any(nxt not in parents for node in frontier for nxt, _ in graph[node])
    return parents, limited


def _route(view: MapView, source: str, target: str, parents: dict, limited: bool,
           fingerprint: str | None = None) -> Route:
    fp = fingerprint or view.fingerprint
    if target not in parents:
        return Route(source, target, "SEARCH_BOUND_REACHED" if limited else "NO_RECORDED_ROUTE",
                     (), fp, view.as_of, limited)
    steps = []
    current = target
    while parents[current] is not None:
        previous, edge = parents[current]
        steps.append(Step(edge.id, edge.predicate, previous, current, edge.source,
                          edge.target, edge.status.value, edge.evidence_ids))
        current = previous
    return Route(source, target, "RECORDED_ROUTE", tuple(reversed(steps)), fp, view.as_of)


def trace(view: MapView, source: str, target: str, *, direction: str = "out",
          predicates: tuple[str, ...] | None = None, max_depth: int | None = None) -> Route:
    """Return a deterministic minimum-hop path, with each edge's original direction."""
    view.node(target)
    parents, limited = _search(view, source, direction, predicates, max_depth)
    return _route(view, source, target, parents, limited)


def reach(view: MapView, start: str, *, mode: str = "out", max_depth: int | None = None,
          predicates: tuple[str, ...] | None = None) -> Reachability:
    parents, limited = _search(view, start, mode, predicates, max_depth)
    ids = tuple(sorted(set(parents) - {start}))
    fp = view.fingerprint
    return Reachability(start, mode, ids, tuple(_route(view, start, n, parents, False, fp) for n in ids),
                        limited, fp, view.as_of)


def dependencies(view: MapView, start: str, *, max_depth: int | None = None) -> Reachability:
    return reach(view, start, mode="dependencies", max_depth=max_depth)


def impact(view: MapView, start: str, *, max_depth: int | None = None) -> Reachability:
    return reach(view, start, mode="impact", max_depth=max_depth)


def dependency_cycles(view: MapView) -> tuple[tuple[str, ...], ...]:
    """Iterative strongly connected components; safe for long dependency chains."""
    graph = adjacency(view, "dependencies")
    reverse: dict[str, list[str]] = {n: [] for n in graph}
    for source, rows in graph.items():
        for target, _ in rows:
            reverse[target].append(source)
    seen: set[str] = set()
    finished: list[str] = []
    for root in sorted(graph):
        if root in seen:
            continue
        seen.add(root)
        stack = [(root, iter(n for n, _ in graph[root]))]
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                finished.append(node)
                stack.pop()
            elif nxt not in seen:
                seen.add(nxt)
                stack.append((nxt, iter(n for n, _ in graph[nxt])))
    seen.clear()
    cycles = []
    for root in reversed(finished):
        if root in seen:
            continue
        component = []
        stack = [root]
        seen.add(root)
        while stack:
            node = stack.pop()
            component.append(node)
            for nxt in reverse[node]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        if len(component) > 1 or any(n == root for n, _ in graph[root]):
            cycles.append(tuple(sorted(component)))
    return tuple(sorted(cycles))
