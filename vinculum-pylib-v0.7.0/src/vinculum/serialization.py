"""Strict JSON scenario IO; no code, model loading, pickle or executable expressions."""
from __future__ import annotations
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any
from .codec import Transformation
from .context import NarrativeContext
from .core import (NumericRange, PDProfile, PairSpec, Representation, Scope, SupportFactor, SupportProfile, TimeWindow, HingeOrderState)
from .hinge import HingeEvaluator, HingePolicy
from .math import UnitDefinition, UnitRegistry
from .matrix import ObjectGroup, PairGraph
from .utils import canonical_json, primitive, read_json

SCHEMA = 'vinculum.crossorder.scenario/1'


def _strict(cls, data):
    if not isinstance(data, dict):
        raise ValueError(f'{cls.__name__} must be a JSON object')
    extra = set(data) - {f.name for f in fields(cls)}
    if extra:
        raise ValueError(f'unknown {cls.__name__} fields: {sorted(extra)}')
    return data


def representation_from_dict(data):
    d = dict(_strict(Representation, data))
    if d.get('quantity') is not None:
        d['quantity'] = NumericRange(**_strict(NumericRange, d['quantity']))
    scope = dict(_strict(Scope, d.get('scope', {})))
    if scope.get('window') is not None:
        scope['window'] = TimeWindow(**_strict(TimeWindow, scope['window']))
    d['scope'] = Scope(**scope)
    d['pd'] = PDProfile(**_strict(PDProfile, d.get('pd', {})))
    sp = _strict(SupportProfile, d.get('support', {}))
    d['support'] = SupportProfile(tuple(SupportFactor(**_strict(SupportFactor, f)) for f in sp.get('factors', ())))
    return Representation(**d)


@dataclass
class Scenario:
    graph: PairGraph
    policy: HingePolicy
    units: UnitRegistry
    transformations: tuple[Transformation, ...] = ()

    def evaluate(self):
        return self.graph.evaluate(HingeEvaluator(self.policy, self.units))

    def to_dict(self):
        return {
            'schema': SCHEMA, 'id': self.graph.id, 'orders_l': self.graph.orders_l, 'orders_m': self.graph.orders_m,
            'representations': primitive(tuple(sorted(self.graph.nodes.values(), key=lambda n: n.id))),
            'pairs': primitive(tuple(sorted(self.graph.pairs.values(), key=lambda n: n.id))),
            'groups': primitive(tuple(sorted(self.graph.groups.values(), key=lambda n: n.id))),
            'policy': primitive(self.policy), 'units': primitive(self.units.definitions()),
            'transformations': primitive(self.transformations), 'context': primitive(self.graph.context),
        }


def scenario_from_dict(data: dict[str, Any]):
    allowed = {'schema', 'id', 'orders_l', 'orders_m', 'representations', 'pairs', 'groups', 'policy', 'units', 'transformations', 'context'}
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError('unknown scenario fields or invalid scenario object')
    if data.get('schema') != SCHEMA:
        raise ValueError(f'expected scenario schema {SCHEMA}')
    g = PairGraph(data.get('id', 'VINCULUM'), data.get('orders_l', 5), data.get('orders_m', 5))
    if len(data.get('representations', ())) > 100000 or len(data.get('pairs', ())) > 100000:
        raise ValueError('scenario exceeds reference loader size limits')
    for d in data.get('representations', ()):
        g.add_node(representation_from_dict(d))
    for d in data.get('pairs', ()):
        d = dict(_strict(PairSpec, d))
        states = []
        for h in d.get('hinge_states', ()):
            h = dict(_strict(HingeOrderState, h))
            h['pd'] = PDProfile(**_strict(PDProfile, h.get('pd', {})))
            sp = _strict(SupportProfile, h.get('support', {}))
            h['support'] = SupportProfile(tuple(SupportFactor(**_strict(SupportFactor, f)) for f in sp.get('factors', ())))
            states.append(HingeOrderState(**h))
        d['hinge_states'] = tuple(states)
        g.add_pair_spec(PairSpec(**d))
    for d in data.get('groups', ()):
        g.add_group(ObjectGroup(**_strict(ObjectGroup, d)))
    if data.get('context') is not None:
        g.context = NarrativeContext(**_strict(NarrativeContext, data['context']))
    policy = HingePolicy(**_strict(HingePolicy, data.get('policy', {})))
    units = UnitRegistry.default() if 'units' not in data else UnitRegistry(
        UnitDefinition(**_strict(UnitDefinition, d)) for d in data['units'])
    tx = tuple(Transformation(**_strict(Transformation, d)) for d in data.get('transformations', ()))
    return Scenario(g, policy, units, tx)


def load_scenario(path: str | Path, *, max_bytes=25000000):
    path = Path(path)
    if path.stat().st_size > max_bytes:
        raise ValueError('scenario file exceeds byte limit')
    return scenario_from_dict(read_json(path.read_text(encoding='utf-8')))


def save_scenario(scenario: Scenario, path: str | Path):
    Path(path).write_text(canonical_json(scenario.to_dict()) + '\n', encoding='utf-8')
