"""Pair-local, cross-order alignment checks. No global independent hinge score."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .core import (CheckState, HingeCheck, PairResult, PairSpec, PairStatus, Representation, Side)
from .math import UnitRegistry, compare_ranges
from .utils import fingerprint, timestamp


@dataclass(frozen=True)
class HingePolicy:
    id: str = 'strict-pair-v1'
    require_time: bool = True
    required_context: tuple[str, ...] = ('scope_id', 'population', 'denominator', 'granularity')
    require_same_method: bool = False
    max_age_seconds: float | None = None
    as_of: datetime | None = None
    support_aggregation: str = 'minimum'
    product_basis: str | None = None

    def __post_init__(self):
        from .utils import number
        if not isinstance(self.require_time, bool) or not isinstance(self.require_same_method, bool):
            raise ValueError('hinge policy switches must be booleans')
        allowed = {'scope_id', 'population', 'denominator', 'granularity', 'location', 'definition_version'}
        object.__setattr__(self, 'required_context', tuple(self.required_context))
        if not set(self.required_context) <= allowed:
            raise ValueError('unsupported required scope dimension')
        if self.support_aggregation not in {'minimum', 'product'}:
            raise ValueError('support aggregation must be minimum or product')
        if self.support_aggregation == 'product' and not self.product_basis:
            raise ValueError('product support requires an explicit basis; it is not automatically a probability')
        if self.max_age_seconds is not None:
            if number(self.max_age_seconds) < 0 or self.as_of is None:
                raise ValueError('freshness needs nonnegative max_age_seconds and explicit as_of')
        if self.as_of is not None:
            object.__setattr__(self, 'as_of', timestamp(self.as_of))


class HingeEvaluator:
    """Evaluate ONLY an explicit pair. Required checks cannot be skipped by order selection.

    Custom checks can add restrictions but cannot override built-in checks. Extension
    code is trusted application code, not code accepted from a payload or an LLM.
    """
    def __init__(self, policy: HingePolicy | None = None, units: UnitRegistry | None = None):
        self.policy = policy or HingePolicy()
        self.units = units or UnitRegistry.default()
        self._extensions: dict[str, Callable] = {}

    def register_check(self, name: str, check: Callable):
        if name in self._extensions or not name:
            raise ValueError('extension names must be nonempty and unique')
        if not callable(check):
            raise TypeError('check must be callable')
        self._extensions[name] = check
        return self

    def evaluate(self, left: Representation, right: Representation, pair: PairSpec,
                 *, dependency_warnings: tuple[str, ...] = (), missing_dependencies: bool = False) -> PairResult:
        if not isinstance(left, Representation) or not isinstance(right, Representation):
            raise TypeError('hinges accept representations only; narrative context is not measurable')
        if (left.id, right.id) != (pair.left_id, pair.right_id):
            raise ValueError('pair endpoints do not match supplied representations')
        checks = []

        def exact(name, a, b, order=1, required=True):
            if a is None and b is None and not required:
                state, why = CheckState.NOT_APPLICABLE, 'not declared on either side; not required by this contract'
            elif a is None or b is None:
                state, why = CheckState.UNKNOWN, 'missing on one or both representations'
            elif a == b:
                state, why = CheckState.PASS, 'exact match in supplied representations'
            else:
                state, why = CheckState.FAIL, 'declared identities or scopes differ; not a numeric contradiction'
            checks.append(HingeCheck(name, order, state, why, required))

        exact('entity', left.entity, right.entity)
        exact('concept', left.concept, right.concept)
        for name in ('scope_id', 'population', 'denominator', 'granularity', 'location', 'definition_version'):
            a, b = getattr(left.scope, name), getattr(right.scope, name)
            # If either side declares a scope boundary, the other must address it.
            req = name in self.policy.required_context or a is not None or b is not None
            exact(name, a, b, 4 if name in {'location', 'scope_id', 'definition_version'} else 2, req)

        lu, ru = self.units.get(left.unit), self.units.get(right.unit)
        if lu is None or ru is None:
            checks.append(HingeCheck('units', 2, CheckState.UNKNOWN, 'unit missing or unregistered'))
        elif lu.dimension != ru.dimension:
            checks.append(HingeCheck('units', 2, CheckState.FAIL, 'incompatible physical/numeric dimensions'))
        else:
            checks.append(HingeCheck('units', 2, CheckState.PASS, 'dimensions match; exact registered conversion applied'))

        a, b = left.scope, right.scope
        time_required = self.policy.require_time or a.window is not None or b.window is not None or a.timeless or b.timeless
        if a.timeless and b.timeless:
            state, why = CheckState.PASS, 'both explicitly scoped as timeless'
        elif a.timeless != b.timeless:
            state, why = CheckState.FAIL, 'timeless vs time-bound/unspecified scope is not an implicit equivalence'
        elif a.window is None or b.window is None:
            state = CheckState.UNKNOWN if time_required else CheckState.NOT_APPLICABLE
            why = 'time window missing; no implicit now() or freshness assumption'
        elif a.window == b.window:
            state, why = CheckState.PASS, 'same UTC interval; unequal aggregate windows are not interchangeable'
        else:
            state, why = CheckState.FAIL, 'different UTC intervals; overlap alone does not make aggregates equivalent'
        checks.append(HingeCheck('time', 4, state, why, time_required))

        if self.policy.max_age_seconds is not None:
            ages = []
            for node in (left, right):
                if not node.scope.timeless and node.scope.window is not None:
                    ages.append((self.policy.as_of - node.scope.window.end).total_seconds())
            if any(age < 0 for age in ages):
                state, why = CheckState.UNKNOWN, 'future-dated data relative to the explicit evaluation clock'
            elif any(age > self.policy.max_age_seconds for age in ages):
                state, why = CheckState.UNKNOWN, 'stale for this evaluation contract; refresh needed'
            else:
                state, why = CheckState.PASS, 'within explicit freshness limit, or explicitly timeless'
            checks.append(HingeCheck('freshness', 4, state, why))

        if left.quantity is None or right.quantity is None:
            state, why = CheckState.UNKNOWN, 'semantic or numeric value not resolved; no numeric comparison possible'
        else:
            state, why = CheckState.PASS, 'both quantities represented as explicit admissible numeric sets'
        checks.append(HingeCheck('numeric_meaning', 1, state, why))
        exact('method', left.method, right.method, 3, self.policy.require_same_method)
        # Distinct measurement methods are allowed by default; observations may corroborate.
        if not self.policy.require_same_method:
            checks[-1] = HingeCheck('method', 3,
                                   CheckState.PASS if left.method and right.method else CheckState.UNKNOWN,
                                   'methods documented; equality is not required' if left.method and right.method else 'method metadata incomplete', False)
        checks.append(HingeCheck('dependence', 5,
                                 CheckState.UNKNOWN if missing_dependencies or dependency_warnings else CheckState.PASS,
                                 '; '.join(dependency_warnings) if dependency_warnings else 'no declared shared roots detected; independence not proven', False))
        for name, callback in sorted(self._extensions.items()):
            try:
                c = callback(left, right, pair)
                if not isinstance(c, HingeCheck) or c.name in {x.name for x in checks}:
                    raise ValueError('extension must return a uniquely named HingeCheck')
            except Exception as exc:
                c = HingeCheck(f'extension:{name}', max(pair.hinge_orders), CheckState.UNKNOWN,
                               f'extension unavailable ({type(exc).__name__})', True)
            checks.append(c)

        required = [c for c in checks if c.required and c.state is not CheckState.NOT_APPLICABLE]
        known = sum(c.state in {CheckState.PASS, CheckState.FAIL} for c in required)
        if any(c.state is CheckState.FAIL for c in required):
            comparable, status = False, PairStatus.NOT_COMPARABLE
        elif any(c.state is CheckState.UNKNOWN for c in required):
            comparable, status = None, PairStatus.UNRESOLVED
        else:
            comparable, status = True, PairStatus.ALIGNED

        discrepancy = {'relation': 'NOT_EVALUATED', 'signed_delta': None, 'boundary_gap': None,
                       'normalized_magnitude': None, 'raw_conflict': None}
        raw = None
        if comparable:
            e = self.units.normalize(left.quantity, left.unit)
            o = self.units.normalize(right.quantity, right.unit)
            scale = None if pair.distance_scale is None else pair.distance_scale * lu.factor
            status, discrepancy, raw = compare_ranges(e, o, scale)
            from .utils import number, number_text, primitive
            discrepancy['original_expected'] = primitive(left.quantity)
            discrepancy['original_observed'] = primitive(right.quantity)
            discrepancy['left_unit'] = left.unit
            discrepancy['right_unit'] = right.unit
            sd = discrepancy.get('signed_delta')
            discrepancy['signed_delta_left_unit'] = None if sd is None else number_text(number(sd) / lu.factor)
            discrepancy['boundary_gap_left_unit'] = number_text(number(discrepancy['boundary_gap']) / lu.factor)
            discrepancy['dimension'] = lu.dimension
            discrepancy['unit_note'] = 'values/deltas in the registered base unit; raw source values retained in nodes'

        ls, rs = left.support.assess(), right.support.assess()
        hinge_strengths = tuple(h.support.assess()['strength'] for h in pair.hinge_states)
        strengths = (ls['strength'], rs['strength'], pair.alignment_support) + hinge_strengths
        if any(x is None for x in strengths) or missing_dependencies:
            joint = None
        elif self.policy.support_aggregation == 'minimum':
            joint = min(strengths)
        else:
            import math
            joint = math.prod(strengths)
        support = {
            'left': ls, 'right': rs, 'alignment_strength': pair.alignment_support,
            'alignment_basis': pair.alignment_basis, 'joint_strength': joint,
            'aggregation': self.policy.support_aggregation,
            'product_basis': self.policy.product_basis,
            'interpretation': 'declared support indicator, not probability of truth or operational risk',
            'missing_dependencies': missing_dependencies,
            'declared_higher_order_hinge_strengths': list(hinge_strengths),
        }
        used_orders = tuple(sorted(set(pair.hinge_orders) | {h.order for h in pair.hinge_states} | {c.order for c in checks if c.required}))
        language_order = left.order if left.side is Side.LANGUAGE else (right.order if right.side is Side.LANGUAGE else None)
        math_order = right.order if right.side is Side.MATHEMATICS else (left.order if left.side is Side.MATHEMATICS else None)
        state_map = {h.order: h for h in pair.hinge_states}
        hinge_assessments = tuple({
            'notation': f'H({left.side.value}{left.order},{right.side.value}{right.order};{k})',
            'order': k, 'pair_id': pair.id,
            'pd': state_map[k].pd.vector() if k in state_map else None,
            'support': state_map[k].support.assess() if k in state_map else None,
            'note': state_map[k].note if k in state_map else 'no extra higher-order coefficient asserted',
            'checks': [c.name for c in checks if c.order == k],
        } for k in used_orders)
        return PairResult(
            pair.id, left.id, right.id, left.side, right.side, language_order, math_order,
            used_orders, status, comparable, tuple(checks), discrepancy, support,
            {'alignment_metadata': known / len(required) if required else 0.0,
             'left_support': ls['coverage'], 'right_support': rs['coverage'],
             'comparison_performed': bool(comparable)},
            raw, None if raw is None or joint is None else raw * joint,
            tuple(dependency_warnings),
            fingerprint({'left': left, 'right': right, 'pair': pair, 'policy': self.policy,
                         'units': self.units.definitions(), 'checks': checks,
                         'dependency_warnings': dependency_warnings}), pair.weight, hinge_assessments)
