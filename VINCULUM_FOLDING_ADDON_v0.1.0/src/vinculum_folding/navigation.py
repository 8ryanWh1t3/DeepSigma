"""Read-only traversal across version-pinned episodes with a recorded return path."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Iterable

from .model import FoldEpisode, FoldError, digest, fields, identifier


@dataclass(frozen=True, order=True)
class NodeRef:
    episode_id: str
    revision: int
    node_id: str

    def __post_init__(self):
        identifier(self.episode_id, "episode_id")
        identifier(self.node_id, "node_id")
        if type(self.revision) is not int or self.revision < 1:
            raise FoldError("node reference must pin a positive revision")


@dataclass(frozen=True)
class Step:
    owner_episode_id: str
    owner_revision: int
    link_id: str
    reverse: bool
    source: NodeRef
    target: NodeRef
    relation: str
    rationale: str
    resolved: bool


@dataclass(frozen=True)
class NavigationSession:
    world_digest: str
    trail: tuple[NodeRef, ...]
    steps: tuple[Step, ...] = ()

    @property
    def current(self) -> NodeRef:
        return self.trail[-1]

    def to_dict(self):
        return {"schema": "vinculum.folding.trail/1", "world_digest": self.world_digest,
                "start": asdict(self.trail[0]),
                "steps": [{"owner_episode_id": s.owner_episode_id, "owner_revision": s.owner_revision,
                           "link_id": s.link_id, "reverse": s.reverse} for s in self.steps]}


class FoldWorld:
    """Immutable collection of captured episodes. Cross-episode targets never float.

    Missing target episodes remain visible as unresolved links. The world is not
    an authorization boundary: the host must filter accessible material first.
    """
    __slots__ = ("_episodes", "_edges", "_nodes", "_digest")

    def __init__(self, episodes: Iterable[FoldEpisode]):
        catalog, nodes, edges = {}, {}, []
        for episode in episodes:
            if not isinstance(episode, FoldEpisode):
                raise FoldError("FoldWorld requires validated FoldEpisode snapshots")
            data = episode.to_dict()
            key = (data["episode_id"], data["revision"])
            if key in catalog:
                raise FoldError("duplicate episode/revision in world")
            catalog[key] = episode
            for node in data["nodes"]:
                nodes[NodeRef(*key, node["id"])] = node["id"]
            for fold in data["folds"]:
                edges.append((key, fold["id"], NodeRef(*key, fold["from_node"]),
                              NodeRef(*key, fold["to_node"]), fold["relation"], fold["rationale"]))
            for link in data["external_links"]:
                edges.append((key, link["id"], NodeRef(*key, link["from_node"]),
                              NodeRef(link["to_episode_id"], link["to_revision"], link["to_node"]),
                              link["relation"], link["rationale"]))
        self._episodes = MappingProxyType(catalog)
        self._nodes = MappingProxyType(nodes)
        self._edges = tuple(sorted(edges, key=lambda e: (e[0], e[1])))
        self._digest = digest([[*key, ep.digest] for key, ep in sorted(catalog.items())])

    @property
    def digest(self):
        return self._digest

    def node(self, ref: NodeRef):
        if ref not in self._nodes:
            raise FoldError("node is not loaded at the pinned episode/revision")
        return next(n for n in self._episodes[(ref.episode_id, ref.revision)].to_dict()["nodes"] if n["id"] == ref.node_id)

    def links(self, ref: NodeRef) -> tuple[Step, ...]:
        self.node(ref)
        result = []
        for owner, link_id, a, b, relation, rationale in self._edges:
            if a == ref:
                result.append(Step(*owner, link_id, False, a, b, relation, rationale, b in self._nodes))
            if b == ref:
                result.append(Step(*owner, link_id, True, b, a, relation, rationale, a in self._nodes))
        return tuple(result)

    def start(self, ref: NodeRef) -> NavigationSession:
        self.node(ref)
        return NavigationSession(self.digest, (ref,))

    def _check(self, session: NavigationSession) -> None:
        if not isinstance(session, NavigationSession) or session.world_digest != self.digest:
            raise FoldError("navigation session is stale or belongs to another world")
        if not session.trail or len(session.trail) != len(session.steps) + 1 or len(session.steps) > 10000:
            raise FoldError("invalid or oversized traversal trail")
        for i, step in enumerate(session.steps):
            if step.source != session.trail[i] or step.target != session.trail[i + 1] or step not in self.links(step.source) or not step.resolved:
                raise FoldError("traversal path cannot be replayed against this world")
        self.node(session.current)

    def follow(self, session: NavigationSession, step: Step) -> NavigationSession:
        self._check(session)
        if len(session.steps) >= 10000:
            raise FoldError("maximum traversal length reached")
        if step not in self.links(session.current):
            raise FoldError("step is not an adjacent recorded relationship")
        if not step.resolved:
            raise FoldError("target episode/revision is not loaded; traversal withheld")
        return NavigationSession(self.digest, session.trail + (step.target,), session.steps + (step,))

    def back(self, session: NavigationSession) -> NavigationSession:
        self._check(session)
        if not session.steps:
            return session
        return NavigationSession(self.digest, session.trail[:-1], session.steps[:-1])

    def replay(self, data: dict) -> NavigationSession:
        fields(data, {"schema", "world_digest", "start", "steps"}, {"schema", "world_digest", "start", "steps"}, "trail")
        if data["schema"] != "vinculum.folding.trail/1" or data["world_digest"] != self.digest:
            raise FoldError("trail schema or pinned world digest mismatch")
        fields(data["start"], {"episode_id", "revision", "node_id"}, {"episode_id", "revision", "node_id"}, "trail start")
        if type(data["steps"]) is not list or len(data["steps"]) > 10000:
            raise FoldError("invalid trail length")
        session = self.start(NodeRef(**data["start"]))
        for item in data["steps"]:
            fields(item, {"owner_episode_id", "owner_revision", "link_id", "reverse"},
                   {"owner_episode_id", "owner_revision", "link_id", "reverse"}, "trail step")
            if type(item["reverse"]) is not bool or type(item["owner_revision"]) is not int:
                raise FoldError("invalid trail step types")
            matches = [s for s in self.links(session.current)
                       if (s.owner_episode_id, s.owner_revision, s.link_id, s.reverse) ==
                          (item["owner_episode_id"], item["owner_revision"], item["link_id"], item["reverse"])]
            if len(matches) != 1:
                raise FoldError("trail step is missing or ambiguous")
            session = self.follow(session, matches[0])
        return session

    def neighborhood(self, ref: NodeRef, *, depth: int = 1, max_nodes: int = 1000) -> dict:
        """Bounded BFS. Cycles are safe; truncation and missing targets are explicit."""
        if type(depth) is not int or not 0 <= depth <= 100 or type(max_nodes) is not int or not 1 <= max_nodes <= 10000:
            raise FoldError("invalid traversal capacity")
        self.node(ref)
        seen, frontier, unresolved, truncated = {ref}, [ref], set(), False
        for _ in range(depth):
            next_frontier = []
            for current in frontier:
                for step in self.links(current):
                    if not step.resolved:
                        unresolved.add(step.target)
                    elif step.target not in seen:
                        if len(seen) >= max_nodes:
                            truncated = True
                        else:
                            seen.add(step.target)
                            next_frontier.append(step.target)
            frontier = next_frontier
        return {"schema": "vinculum.folding.neighborhood/1", "world_digest": self.digest,
                "focus": asdict(ref), "nodes": [asdict(n) for n in sorted(seen)],
                "unresolved_targets": [asdict(n) for n in sorted(unresolved)],
                "depth": depth, "capacity_truncated": truncated,
                "boundary": "Recorded relationship reach, not causal effect, priority, permission or complete operational impact."}
