from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(slots=True)
class DependencyGraph:
    edges: dict[str, set[str]]

    @classmethod
    def from_dependencies(cls, dependencies: dict[str, list[str]]) -> "DependencyGraph":
        # Edge A -> B means B depends on A (A can affect B downstream).
        edges: dict[str, set[str]] = defaultdict(set)
        for node, parents in dependencies.items():
            edges.setdefault(node, set())
            for parent in parents:
                edges[parent].add(node)
                edges.setdefault(parent, set())
        return cls(dict(edges))

    def downstream(self, node: str) -> list[str]:
        seen: set[str] = set()
        q = deque([node])
        while q:
            cur = q.popleft()
            for nxt in self.edges.get(cur, set()):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        return sorted(seen)

    def cycles(self) -> list[list[str]]:
        color: dict[str, int] = {n: 0 for n in self.edges}
        stack: list[str] = []
        found: set[tuple[str, ...]] = set()

        def canonical(cycle: list[str]) -> tuple[str, ...]:
            body = cycle[:-1]
            if not body:
                return tuple(cycle)
            rots = [tuple(body[i:] + body[:i]) for i in range(len(body))]
            best = min(rots)
            return best + (best[0],)

        def dfs(node: str) -> None:
            color[node] = 1
            stack.append(node)
            for nxt in self.edges.get(node, set()):
                if color.get(nxt, 0) == 0:
                    dfs(nxt)
                elif color.get(nxt) == 1 and nxt in stack:
                    i = stack.index(nxt)
                    found.add(canonical(stack[i:] + [nxt]))
            stack.pop()
            color[node] = 2

        for node in list(self.edges):
            if color[node] == 0:
                dfs(node)
        return [list(x) for x in sorted(found)]
