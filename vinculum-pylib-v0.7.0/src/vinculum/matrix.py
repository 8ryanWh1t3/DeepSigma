"""Sparse pair graph, cross-order matrix, dependency-aware hierarchical reporting."""
from __future__ import annotations
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .core import PairResult, PairSpec, PairStatus, Representation, Side
from .hinge import HingeEvaluator
from .utils import fingerprint, identifier, primitive

LANGUAGE_ORDERS = {1: 'Content', 2: 'Qualification', 3: 'Support', 4: 'Context', 5: 'Dependence'}
MATH_ORDERS = {1: 'Value', 2: 'Uncertainty', 3: 'Support / model', 4: 'Applicability', 5: 'Dependence'}


@dataclass(frozen=True)
class ObjectGroup:
    id: str
    kind: str
    members: tuple[str, ...] = ()
    children: tuple[str, ...] = ()

    def __post_init__(self):
        identifier(self.id)
        identifier(self.kind)
        object.__setattr__(self, 'members', tuple(self.members))
        object.__setattr__(self, 'children', tuple(self.children))
        if len(set(self.members)) != len(self.members) or len(set(self.children)) != len(self.children):
            raise ValueError('duplicate group members/children')


def summarize(results, unpaired=()):
    results = tuple(results)
    counts = {s.value: sum(r.status is s for r in results) for s in PairStatus}
    resolved = [r for r in results if r.status in {PairStatus.ALIGNED, PairStatus.CONFLICT}]
    raw = [r for r in results if r.raw_collision_score is not None]
    supported = [r for r in results if r.supported_collision_score is not None]
    if counts['CONFLICT']:
        status = 'CONFLICT'
    elif counts['PARTIAL']:
        status = 'PARTIAL'
    elif counts['UNRESOLVED'] or unpaired:
        status = 'UNRESOLVED' if results else 'UNMEASURED'
    elif counts['NOT_COMPARABLE']:
        status = 'NOT_COMPARABLE' if counts['NOT_COMPARABLE'] == len(results) else 'UNRESOLVED'
    else:
        status = 'ALIGNED' if results else 'UNMEASURED'
    max_weight = max((r.weight for r in raw), default=1.0)
    weight_sum = sum(r.weight / max_weight for r in raw)
    return {
        'status': status, 'selected_pairs': len(results), 'status_counts': counts,
        'resolved_pair_coverage': len(resolved) / len(results) if results else 0.0,
        'support_assessed_pair_coverage': len(supported) / len(results) if results else 0.0,
        'unpaired_material_nodes': list(unpaired),
        'max_raw_collision_score': max((r.raw_collision_score for r in raw), default=None),
        'weighted_mean_raw_collision_score': sum(r.raw_collision_score * (r.weight / max_weight) for r in raw) / weight_sum if weight_sum else None,
        'max_supported_collision_score': max((r.supported_collision_score for r in supported), default=None),
        'has_gaps': bool(unpaired) or len(resolved) != len(results) or len(supported) != len(results),
        'note': 'means use assessed selected pairs only; maxima, counts and gaps remain visible; no cross-unit delta sum',
    }


@dataclass(frozen=True)
class EvaluationReport:
    graph_id: str
    representations: tuple[Representation, ...]
    pairs: tuple[PairResult, ...]
    matrix: dict[str, Any]
    summary: dict[str, Any]
    groups: dict[str, Any]
    contract: dict[str, Any]
    input_fingerprint: str

    def to_dict(self):
        return {'schema': 'vinculum.crossorder.report/1', 'engine_version': '0.7.0', **primitive(self)}

    def pair(self, pair_id):
        for pair in self.pairs:
            if pair.pair_id == pair_id:
                return pair
        raise KeyError(pair_id)


class PairGraph:
    """A container can have nodes without pairs. Unpaired nodes receive no collision score."""
    def __init__(self, id='VINCULUM', orders_l=5, orders_m=5):
        identifier(id)
        if type(orders_l) is not int or type(orders_m) is not int or min(orders_l, orders_m) < 1:
            raise ValueError('matrix dimensions must be positive integers')
        self.id, self.orders_l, self.orders_m = id, orders_l, orders_m
        self._nodes: dict[str, Representation] = {}
        self._pairs: dict[str, PairSpec] = {}
        self._groups: dict[str, ObjectGroup] = {}
        self.context = None  # non-scored NarrativeContext; explicitly excluded from numeric results

    @property
    def nodes(self):
        return MappingProxyType(self._nodes)

    @property
    def pairs(self):
        return MappingProxyType(self._pairs)

    @property
    def groups(self):
        return MappingProxyType(self._groups)

    def add_node(self, node: Representation):
        if not isinstance(node, Representation):
            raise TypeError('only Representation nodes may enter the measurable graph')
        if node.id in self._nodes:
            raise ValueError(f'duplicate representation id: {node.id}')
        self._nodes[node.id] = node
        return self

    def add_pair(self, left_id, right_id, *, id=None, rationale='explicit caller-selected pair', **kwargs):
        spec = PairSpec(id or f'{left_id}::{right_id}', left_id, right_id, rationale, **kwargs)
        return self.add_pair_spec(spec)

    def add_pair_spec(self, spec):
        if spec.id in self._pairs:
            raise ValueError('duplicate pair id')
        if spec.left_id not in self._nodes or spec.right_id not in self._nodes:
            raise ValueError('pair references a missing representation')
        if any((x.left_id, x.right_id) == (spec.left_id, spec.right_id) for x in self._pairs.values()):
            raise ValueError('same ordered pair cannot be counted twice')
        self._pairs[spec.id] = spec
        return self

    def add_group(self, group):
        if not isinstance(group, ObjectGroup) or group.id in self._groups:
            raise ValueError('invalid or duplicate object group')
        self._groups[group.id] = group
        return self

    def _lineage(self):
        # Iterative topological walk avoids a recursion-limit failure for deep documents.
        pending = {k: set(v.depends_on) & self._nodes.keys() for k, v in self._nodes.items()}
        reverse: dict[str, set] = {k: set() for k in self._nodes}
        for k, deps in pending.items():
            for dep in deps:
                reverse[dep].add(k)
        queue = sorted(k for k, deps in pending.items() if not deps)
        roots, ancestors, missing = {}, {}, {}
        while queue:
            key = queue.pop()
            node = self._nodes[key]
            rr, aa = set(node.source_ids), set(node.depends_on)
            mm = any(d not in self._nodes for d in node.depends_on)
            for dep in node.depends_on:
                if dep in self._nodes:
                    rr |= roots[dep]
                    aa |= ancestors[dep]
                    mm = mm or missing[dep]
            roots[key], ancestors[key], missing[key] = rr, aa, mm
            for child in reverse[key]:
                pending[child].remove(key)
                if not pending[child]:
                    queue.append(child)
        if len(roots) != len(self._nodes):
            raise ValueError('cyclic representation dependence; cannot claim independent support')
        return roots, ancestors, missing

    def _group_members(self):
        done, active = {}, set()
        def visit(key):
            if key in active:
                raise ValueError('cyclic object-group hierarchy')
            if key in done:
                return done[key]
            if key not in self._groups:
                raise ValueError('missing child group')
            active.add(key)
            group = self._groups[key]
            members = set(group.members)
            if not members <= self._nodes.keys():
                raise ValueError('group references missing representations')
            for child in group.children:
                members |= visit(child)
            active.remove(key)
            done[key] = members
            return members
        for key in sorted(self._groups):
            visit(key)
        return done

    def structure_fingerprint(self):
        return fingerprint({'id': self.id, 'orders': [self.orders_l, self.orders_m],
                            'nodes': sorted(self._nodes.values(), key=lambda n: n.id),
                            'pairs': sorted(self._pairs.values(), key=lambda n: n.id),
                            'groups': sorted(self._groups.values(), key=lambda n: n.id)})

    def evaluate(self, evaluator: HingeEvaluator | None = None):
        evaluator = evaluator or HingeEvaluator()
        roots, ancestors, missing = self._lineage()
        group_members = self._group_members()
        results = []
        for spec in sorted(self._pairs.values(), key=lambda p: p.id):
            l, r = self._nodes[spec.left_id], self._nodes[spec.right_id]
            warnings = []
            shared = roots[l.id] & roots[r.id]
            if shared:
                warnings.append('shared source roots: ' + ', '.join(sorted(shared)))
            shared_ancestors = ancestors[l.id] & ancestors[r.id]
            if shared_ancestors:
                warnings.append('shared dependencies: ' + ', '.join(sorted(shared_ancestors)))
            if l.id in ancestors[r.id] or r.id in ancestors[l.id]:
                warnings.append('one representation is derived from the other; not independent corroboration')
            mm = missing[l.id] or missing[r.id]
            if mm:
                warnings.append('missing declared dependency; support is incomplete')
            results.append(evaluator.evaluate(l, r, spec, dependency_warnings=tuple(warnings), missing_dependencies=mm))
        represented = {i for r in results for i in (r.left_id, r.right_id)}
        unpaired = sorted(n.id for n in self._nodes.values() if n.material and n.id not in represented)
        nl = max([self.orders_l] + [n.order for n in self._nodes.values() if n.side is Side.LANGUAGE])
        nm = max([self.orders_m] + [n.order for n in self._nodes.values() if n.side is Side.MATHEMATICS])
        if nl * nm > 10000:
            raise ValueError('matrix exceeds 10,000 display cells; split the reporting view')
        cells = []
        for i in range(1, nl + 1):
            for j in range(1, nm + 1):
                rr = [r for r in results if {r.left_side, r.right_side} == {Side.LANGUAGE, Side.MATHEMATICS}
                      and r.language_order == i and r.mathematics_order == j]
                summary = summarize(rr)
                cells.append({'language_order': i, 'mathematics_order': j,
                              'pair_ids': [r.pair_id for r in rr],
                              'status': summary['status'] if rr else 'UNPAIRED',
                              'max_raw_collision_score': summary['max_raw_collision_score'],
                              'max_supported_collision_score': summary['max_supported_collision_score']})
        groups = {}
        for key, members in sorted(group_members.items()):
            rr = [r for r in results if r.left_id in members and r.right_id in members]
            paired = {i for r in rr for i in (r.left_id, r.right_id)}
            uu = sorted(i for i in members if self._nodes[i].material and i not in paired)
            groups[key] = {'kind': self._groups[key].kind, 'members': sorted(members),
                           'pair_ids': [r.pair_id for r in rr], 'summary': summarize(rr, uu)}
        contract = {'graph_structure_fingerprint': self.structure_fingerprint(), 'policy': primitive(evaluator.policy), 'units': primitive(evaluator.units.definitions()),
                    'core_rule': 'only explicit pairs are evaluated; orders are examination levels, not certainty rankings',
                    'score_semantics': 'raw collision and support-weighted indication are separate; not truth, safety or permission'}
        input_fp = fingerprint({'nodes': sorted(self._nodes.values(), key=lambda n: n.id),
                                'pairs': sorted(self._pairs.values(), key=lambda p: p.id),
                                'groups': sorted(self._groups.values(), key=lambda g: g.id), 'contract': contract})
        return EvaluationReport(self.id, tuple(sorted(self._nodes.values(), key=lambda n: n.id)),
                                tuple(results), {'rows': nl, 'columns': nm, 'possible_order_slots': nl * nm,
                                                 'evaluated_order_slots': sum(bool(c['pair_ids']) for c in cells),
                                                 'cells': cells}, summarize(results, unpaired), groups, contract, input_fp)


class CrossOrderEngine:
    """Canonical v0.6 facade; legacy VinculumEngine.score remains a separate API."""
    def __init__(self, evaluator: HingeEvaluator | None = None):
        self.evaluator = evaluator or HingeEvaluator()

    def evaluate(self, graph: PairGraph):
        if not isinstance(graph, PairGraph):
            raise TypeError('CrossOrderEngine requires an explicit PairGraph')
        return graph.evaluate(self.evaluator)
