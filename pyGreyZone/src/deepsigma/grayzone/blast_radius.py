"""Traverse only user-supplied dependencies, with bounded depth."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping


def exposed_dependencies(start: str, graph: Mapping[str, Iterable[str]], *,
                         max_hops: int = 3) -> dict[str, tuple[str, ...]]:
    """Return shortest paths from start across known edges: node -> dependent nodes."""
    if max_hops < 0:
        raise ValueError("max_hops must be nonnegative")
    found: dict[str, tuple[str, ...]] = {start: (start,)}
    todo = deque([start])
    while todo:
        node = todo.popleft()
        if len(found[node]) - 1 >= max_hops:
            continue
        for target in sorted(set(graph.get(node, ()))):
            if target not in found:
                found[target] = (*found[node], target)
                todo.append(target)
    found.pop(start)
    return found
