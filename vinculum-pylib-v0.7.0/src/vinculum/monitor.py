"""Bounded reference pairing monitor. Proposes; caller selects; hinge evaluates."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from .core import Representation, Side
from .math import UnitRegistry
from .matrix import PairGraph
from .utils import fingerprint, timestamp


@dataclass(frozen=True)
class PairProposal:
    left_id: str
    right_id: str
    matched_fields: tuple[str, ...]
    pending_fields: tuple[str, ...]
    match_score: float
    ambiguous: bool
    explanation: str = 'metadata completeness score; not a calibrated match probability; numeric values were not used to match'


class PairingMonitor:
    def __init__(self, *, max_nodes=10000, units: UnitRegistry | None = None):
        if type(max_nodes) is not int or max_nodes < 1:
            raise ValueError('max_nodes must be a positive integer')
        self.max_nodes = max_nodes
        self.units = units or UnitRegistry.default()
        self._nodes = {}
        self._index = {}

    def ingest(self, node: Representation) -> tuple[PairProposal, ...]:
        if not isinstance(node, Representation):
            raise TypeError('monitor accepts normalized representations, not unparsed sensor payloads')
        if node.id in self._nodes:
            if fingerprint(node) != fingerprint(self._nodes[node.id]):
                raise ValueError('changed event must receive a new versioned id')
            return ()
        if len(self._nodes) >= self.max_nodes:
            raise OverflowError('monitor buffer full; explicitly expire or persist records before continuing')
        self._nodes[node.id] = node
        key = (node.entity, node.concept)
        candidates = []
        if node.entity is not None and node.concept is not None:
            for other_id in sorted(self._index.get(key, ())):
                other = self._nodes[other_id]
                if other.side is node.side:
                    continue
                matched, pending, incompatible = ['entity', 'concept'], [], False
                for attr in ('scope_id', 'population', 'denominator', 'granularity', 'location', 'definition_version'):
                    a, b = getattr(node.scope, attr), getattr(other.scope, attr)
                    if a is None and b is None and attr in {'location', 'definition_version'}:
                        continue
                    if a is None or b is None:
                        pending.append(attr)
                    elif a == b:
                        matched.append(attr)
                    else:
                        incompatible = True
                ua, ub = self.units.get(node.unit), self.units.get(other.unit)
                if ua is None or ub is None:
                    pending.append('units')
                elif ua.dimension == ub.dimension:
                    matched.append('units')
                else:
                    incompatible = True
                if node.scope.timeless and other.scope.timeless:
                    matched.append('time')
                elif node.scope.timeless != other.scope.timeless:
                    incompatible = True
                elif node.scope.window is None or other.scope.window is None:
                    pending.append('time')
                elif node.scope.window == other.scope.window:
                    matched.append('time')
                else:
                    incompatible = True
                if not incompatible:
                    l, r = (node, other) if node.side is Side.LANGUAGE else (other, node)
                    candidates.append((l.id, r.id, tuple(matched), tuple(pending)))
            self._index.setdefault(key, set()).add(node.id)
        return tuple(PairProposal(l, r, matched, pending, len(matched) / (len(matched) + len(pending)),
                                  len(candidates) > 1) for l, r, matched, pending in candidates)

    def expire_before(self, before: str | datetime) -> tuple[str, ...]:
        """Explicit, logged eviction. Timeless/missing-time events are not silently discarded."""
        before = timestamp(before)
        expired = [n.id for n in self._nodes.values() if n.scope.window and n.scope.window.end < before]
        for key in expired:
            n = self._nodes.pop(key)
            self._index.get((n.entity, n.concept), set()).discard(key)
        return tuple(sorted(expired))

    def select(self, graph: PairGraph, proposal: PairProposal, *, rationale: str):
        # A caller's explicit selection handles ambiguity; the hinge still checks compatibility.
        for key in (proposal.left_id, proposal.right_id):
            node = self._nodes.get(key)
            if node is None:
                raise ValueError('proposal endpoint expired or is missing')
            if key not in graph.nodes:
                graph.add_node(node)
            elif fingerprint(graph.nodes[key]) != fingerprint(node):
                raise ValueError('graph snapshot differs from monitored record')
        graph.add_pair(proposal.left_id, proposal.right_id, rationale=rationale,
                       alignment_support=None, alignment_basis='explicit selection; match_score is not probability')
        return graph
