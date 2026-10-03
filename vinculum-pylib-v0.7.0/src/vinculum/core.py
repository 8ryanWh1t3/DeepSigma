"""Typed, immutable representations. A representation is not reality or authority."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from fractions import Fraction
from typing import Any

from .utils import identifier, number, primitive, timestamp, unit_score


class Side(str, Enum):
    LANGUAGE = 'L'
    MATHEMATICS = 'M'


class PairStatus(str, Enum):
    ALIGNED = 'ALIGNED'
    PARTIAL = 'PARTIAL'
    CONFLICT = 'CONFLICT'
    UNRESOLVED = 'UNRESOLVED'
    NOT_COMPARABLE = 'NOT_COMPARABLE'


class CheckState(str, Enum):
    PASS = 'PASS'
    FAIL = 'FAIL'
    UNKNOWN = 'UNKNOWN'
    NOT_APPLICABLE = 'NOT_APPLICABLE'


@dataclass(frozen=True)
class PDProfile:
    """P/D descriptors of this representation, not a truth probability.

    Both may be present on either side, at any order; neither is inferred from L/M.
    Balance is not contradiction. The two channels need not sum to one.
    """
    probabilistic: float | None = None
    deterministic: float | None = None
    basis: str = 'not assessed'

    def __post_init__(self):
        object.__setattr__(self, 'probabilistic', unit_score(self.probabilistic, 'P'))
        object.__setattr__(self, 'deterministic', unit_score(self.deterministic, 'D'))
        identifier(self.basis, 'P/D basis')

    def vector(self) -> dict[str, Any]:
        p, d = self.probabilistic, self.deterministic
        if p is None or d is None or p + d == 0:
            return {'P': p, 'D': d, 'position': None, 'balance': None, 'assessed': False}
        v = (d - p) / (p + d)
        return {'P': p, 'D': d, 'position': v, 'balance': 1 - abs(v), 'assessed': True}


@dataclass(frozen=True)
class SupportFactor:
    """An attributed coefficient, not automatically a calibrated probability.

    dependency_group marks factors that draw on the same underlying evidence.
    Factors never rescale an observed numeric value.
    """
    name: str
    value: float | None
    basis: str
    order: int = 2
    source_id: str | None = None
    dependency_group: str | None = None
    kind: str = 'declared'

    def __post_init__(self):
        identifier(self.name, 'factor name')
        identifier(self.basis, 'factor basis')
        if type(self.order) is not int or self.order < 1:
            raise ValueError('support order must be a positive integer')
        object.__setattr__(self, 'value', unit_score(self.value, self.name))
        if self.source_id is not None:
            identifier(self.source_id)
        if self.dependency_group is not None:
            identifier(self.dependency_group)
        if self.kind not in {'declared', 'measured', 'calibrated', 'assumed'}:
            raise ValueError('unknown support kind')


@dataclass(frozen=True)
class SupportProfile:
    factors: tuple[SupportFactor, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, 'factors', tuple(self.factors))
        if any(not isinstance(f, SupportFactor) for f in self.factors):
            raise TypeError('factors must be SupportFactor instances')
        if len({f.name for f in self.factors}) != len(self.factors):
            raise ValueError('support factor names must be unique within a representation')

    def assess(self) -> dict[str, Any]:
        """Conservative bottleneck, not repeated multiplication of correlated scores."""
        grouped: dict[str, list[float | None]] = {}
        for f in self.factors:
            key = f.dependency_group or f.source_id or f'factor:{f.name}'
            grouped.setdefault(key, []).append(f.value)
        known = sum(f.value is not None for f in self.factors)
        complete = bool(self.factors) and known == len(self.factors)
        values = [f.value for f in self.factors if f.value is not None]
        return {
            'strength': min(values) if complete else None,
            'known_bottleneck': min(values) if values else None,
            'coverage': known / len(self.factors) if self.factors else 0.0,
            'known_factors': known, 'expected_factors': len(self.factors),
            'dependency_groups': len(grouped), 'aggregation': 'minimum/bottleneck',
            'factors': primitive(self.factors),
        }


@dataclass(frozen=True)
class NumericRange:
    """Closed/open numeric bounds; None represents an unbounded endpoint.

    This is an admissible set, not a probability distribution. Use quantity=None on
    a Representation when a numeric meaning is unknown.
    """
    lower: Fraction | None
    upper: Fraction | None
    lower_inclusive: bool = True
    upper_inclusive: bool = True

    def __post_init__(self):
        lo = None if self.lower is None else number(self.lower)
        hi = None if self.upper is None else number(self.upper)
        object.__setattr__(self, 'lower', lo)
        object.__setattr__(self, 'upper', hi)
        if not isinstance(self.lower_inclusive, bool) or not isinstance(self.upper_inclusive, bool):
            raise ValueError('inclusivity must be boolean')
        if lo is None and hi is None:
            raise ValueError('unconstrained/unknown is quantity=None, not an all-real bound')
        if lo is not None and hi is not None:
            if lo > hi or (lo == hi and not (self.lower_inclusive and self.upper_inclusive)):
                raise ValueError('numeric range is empty or reversed')

    @classmethod
    def point(cls, value: Any) -> 'NumericRange':
        return cls(number(value), number(value))

    @classmethod
    def around(cls, value: Any, tolerance: Any) -> 'NumericRange':
        v, t = number(value), number(tolerance)
        if t < 0:
            raise ValueError('tolerance cannot be negative')
        return cls(v - t, v + t)

    @classmethod
    def constraint(cls, op: str, value: Any, upper: Any = None) -> 'NumericRange':
        v = number(value)
        if op in {'eq', '=='}:
            return cls.point(v)
        if op in {'le', '<='}:
            return cls(None, v)
        if op in {'lt', '<'}:
            return cls(None, v, upper_inclusive=False)
        if op in {'ge', '>='}:
            return cls(v, None)
        if op in {'gt', '>'}:
            return cls(v, None, lower_inclusive=False)
        if op in {'between', 'range'}:
            if upper is None:
                raise ValueError('between requires upper bound')
            return cls(v, number(upper))
        raise ValueError(f'unsupported numeric operator: {op}')

    @property
    def is_point(self) -> bool:
        return self.lower is not None and self.lower == self.upper


@dataclass(frozen=True)
class TimeWindow:
    start: datetime
    end: datetime

    def __post_init__(self):
        a, b = timestamp(self.start), timestamp(self.end)
        if a > b:
            raise ValueError('time window is reversed')
        object.__setattr__(self, 'start', a)
        object.__setattr__(self, 'end', b)

    @classmethod
    def instant(cls, at: str | datetime) -> 'TimeWindow':
        return cls(timestamp(at), timestamp(at))


@dataclass(frozen=True)
class Scope:
    scope_id: str | None = None
    population: str | None = None
    denominator: str | None = None
    granularity: str | None = None
    location: str | None = None
    definition_version: str | None = None
    window: TimeWindow | None = None
    timeless: bool = False

    def __post_init__(self):
        if self.window is not None and not isinstance(self.window, TimeWindow):
            raise TypeError('window must be a TimeWindow')
        if self.timeless and self.window is not None:
            raise ValueError('scope cannot be both timeless and time-bound')
        if not isinstance(self.timeless, bool):
            raise ValueError('timeless must be boolean')
        for k in ('scope_id', 'population', 'denominator', 'granularity', 'location', 'definition_version'):
            if getattr(self, k) is not None:
                identifier(getattr(self, k), k)


@dataclass(frozen=True)
class Representation:
    id: str
    side: Side
    order: int
    entity: str | None
    concept: str | None
    quantity: NumericRange | None = None
    unit: str | None = None
    scope: Scope = field(default_factory=Scope)
    text: str = ''
    pd: PDProfile = field(default_factory=PDProfile)
    support: SupportProfile = field(default_factory=SupportProfile)
    source_ids: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    method: str | None = None
    material: bool = True
    definition_id: str | None = None

    def __post_init__(self):
        identifier(self.id)
        if not isinstance(self.scope, Scope) or not isinstance(self.pd, PDProfile) or not isinstance(self.support, SupportProfile):
            raise TypeError('scope, pd and support must use their declared dataclass types')
        object.__setattr__(self, 'side', Side(self.side))
        if type(self.order) is not int or self.order < 1:
            raise ValueError('representation order must be a positive integer')
        for k in ('entity', 'concept', 'unit', 'method', 'definition_id'):
            if getattr(self, k) is not None:
                identifier(getattr(self, k), k)
        if not isinstance(self.text, str) or not isinstance(self.material, bool):
            raise ValueError('invalid text/material fields')
        if self.quantity is not None and not isinstance(self.quantity, NumericRange):
            raise TypeError('quantity must be NumericRange or None')
        for k in ('source_ids', 'depends_on'):
            if isinstance(getattr(self, k), str):
                raise TypeError(f'{k} must be a sequence of IDs, not a string')
            vals = tuple(getattr(self, k))
            if len(set(vals)) != len(vals):
                raise ValueError(f'duplicate {k}')
            for v in vals:
                identifier(v)
            object.__setattr__(self, k, vals)
        if self.id in self.depends_on:
            raise ValueError('representation cannot depend on itself')


@dataclass(frozen=True)
class HingeOrderState:
    """P/D and support at one examination order of ONE specified hinge.

    This object is attached to a PairSpec, never stored as a free-standing truth node.
    """
    order: int
    pd: PDProfile = field(default_factory=PDProfile)
    support: SupportProfile = field(default_factory=SupportProfile)
    note: str = 'not assessed'

    def __post_init__(self):
        if type(self.order) is not int or self.order < 1:
            raise ValueError('hinge state order must be a positive integer')
        if not isinstance(self.pd, PDProfile) or not isinstance(self.support, SupportProfile):
            raise TypeError('hinge order state needs typed P/D and support')
        identifier(self.note, 'hinge order note')


@dataclass(frozen=True)
class PairSpec:
    id: str
    left_id: str
    right_id: str
    rationale: str
    hinge_orders: tuple[int, ...] = (1, 2, 3, 4, 5)
    alignment_support: float | None = None
    alignment_basis: str | None = None
    distance_scale: Fraction | None = None  # in LEFT unit; explicit domain choice
    weight: float = 1.0
    hinge_states: tuple[HingeOrderState, ...] = ()

    def __post_init__(self):
        for k in ('id', 'left_id', 'right_id', 'rationale'):
            identifier(getattr(self, k), k)
        if self.left_id == self.right_id:
            raise ValueError('a pair must contain two different representations')
        orders = tuple(self.hinge_orders)
        if not orders or len(set(orders)) != len(orders) or any(type(o) is not int or o < 1 for o in orders):
            raise ValueError('hinge orders must be unique positive integers')
        object.__setattr__(self, 'hinge_orders', orders)
        states = tuple(self.hinge_states)
        if any(not isinstance(h, HingeOrderState) for h in states) or len({h.order for h in states}) != len(states):
            raise ValueError('hinge states must be typed and have unique orders')
        object.__setattr__(self, 'hinge_states', states)
        object.__setattr__(self, 'alignment_support', unit_score(self.alignment_support, 'alignment support'))
        if self.alignment_support is not None and not self.alignment_basis:
            raise ValueError('alignment support needs an attributed basis')
        if self.distance_scale is not None:
            s = number(self.distance_scale)
            if s <= 0:
                raise ValueError('distance scale must be positive')
            object.__setattr__(self, 'distance_scale', s)
        if number(self.weight) <= 0:
            raise ValueError('pair weight must be positive')
        import math
        w = float(self.weight)
        if not math.isfinite(w) or w <= 0:
            raise ValueError('pair weight must be representable as a positive finite float')
        object.__setattr__(self, 'weight', w)


@dataclass(frozen=True)
class HingeCheck:
    name: str
    order: int
    state: CheckState
    reason: str
    required: bool = True

    def __post_init__(self):
        identifier(self.name)
        identifier(self.reason)
        object.__setattr__(self, 'state', CheckState(self.state))
        if type(self.order) is not int or self.order < 1 or not isinstance(self.required, bool):
            raise ValueError('invalid hinge-check order or required flag')


@dataclass(frozen=True)
class PairResult:
    pair_id: str
    left_id: str
    right_id: str
    left_side: Side
    right_side: Side
    language_order: int | None
    mathematics_order: int | None
    hinge_orders: tuple[int, ...]
    status: PairStatus
    comparable: bool | None
    checks: tuple[HingeCheck, ...]
    discrepancy: dict[str, Any]
    support: dict[str, Any]
    coverage: dict[str, Any]
    raw_collision_score: float | None
    supported_collision_score: float | None
    dependency_warnings: tuple[str, ...]
    input_fingerprint: str
    weight: float = 1.0
    hinge_assessments: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return primitive(self)
