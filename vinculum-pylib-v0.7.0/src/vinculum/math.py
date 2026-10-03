"""Exact unit normalization and interval reasoning; no eval() and no sensor truth claims."""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Any
from .core import NumericRange, PairStatus
from .utils import number, number_text, primitive


@dataclass(frozen=True)
class UnitDefinition:
    symbol: str
    dimension: str
    factor: Fraction = Fraction(1)
    offset: Fraction = Fraction(0)

    def __post_init__(self):
        if not self.symbol or not self.dimension:
            raise ValueError('unit symbol and dimension required')
        object.__setattr__(self, 'factor', number(self.factor))
        object.__setattr__(self, 'offset', number(self.offset))
        if self.factor <= 0:
            raise ValueError('unit factor must be positive')


class UnitRegistry:
    def __init__(self, definitions=()):
        self._units = {}
        for u in definitions:
            self.register(u)

    @classmethod
    def default(cls):
        U = UnitDefinition
        return cls([
            U('count', 'count'), U('item', 'count'),
            U('ratio', 'ratio'), U('%', 'ratio', Fraction(1, 100)),
            U('s', 'time'), U('min', 'time', 60), U('h', 'time', 3600), U('day', 'time', 86400),
            U('m', 'length'), U('cm', 'length', Fraction(1, 100)), U('km', 'length', 1000),
            U('ft', 'length', Fraction(381, 1250)), U('in', 'length', Fraction(127, 5000)),
            U('m/s', 'speed'), U('km/h', 'speed', Fraction(5, 18)), U('mph', 'speed', Fraction(1397, 3125)),
            U('K', 'temperature'), U('C', 'temperature', 1, Fraction(27315, 100)),
            U('F', 'temperature', Fraction(5, 9), Fraction(45967, 180)),
            U('USD', 'currency:USD'), U('USD_cent', 'currency:USD', Fraction(1, 100)),
            U('EUR', 'currency:EUR'),  # no implicit currency conversion
        ])

    def register(self, unit: UnitDefinition):
        if unit.symbol in self._units:
            raise ValueError(f'duplicate unit: {unit.symbol}')
        self._units[unit.symbol] = unit
        return self

    def get(self, symbol):
        return self._units.get(symbol)

    def definitions(self):
        return tuple(self._units[k] for k in sorted(self._units))

    def normalize(self, value: NumericRange, symbol: str) -> NumericRange:
        u = self.get(symbol)
        if u is None:
            raise ValueError(f'unregistered unit: {symbol}')
        cv = lambda v: None if v is None else v * u.factor + u.offset
        return NumericRange(cv(value.lower), cv(value.upper), value.lower_inclusive, value.upper_inclusive)


def _before(a: NumericRange, b: NumericRange) -> bool:
    if a.upper is None or b.lower is None:
        return False
    return a.upper < b.lower or (a.upper == b.lower and not (a.upper_inclusive and b.lower_inclusive))


def _subset(inner: NumericRange, outer: NumericRange) -> bool:
    lower = outer.lower is None or (
        inner.lower is not None and (
            inner.lower > outer.lower or
            (inner.lower == outer.lower and (outer.lower_inclusive or not inner.lower_inclusive))))
    upper = outer.upper is None or (
        inner.upper is not None and (
            inner.upper < outer.upper or
            (inner.upper == outer.upper and (outer.upper_inclusive or not inner.upper_inclusive))))
    return lower and upper


def compare_ranges(expected: NumericRange, observed: NumericRange, scale: Fraction | None = None):
    """Right observed admissible set checked against left expected admissible set."""
    if _before(expected, observed) or _before(observed, expected):
        status, relation, raw = PairStatus.CONFLICT, 'DISJOINT', 100.0
    elif _subset(observed, expected):
        status, relation, raw = PairStatus.ALIGNED, 'OBSERVATION_WITHIN_EXPECTATION', 0.0
    else:
        status, relation, raw = PairStatus.PARTIAL, 'OVERLAP_NOT_CONTAINED', None
    delta = observed.lower - expected.lower if expected.is_point and observed.is_point else None
    if _before(expected, observed):
        gap = observed.lower - expected.upper
    elif _before(observed, expected):
        gap = expected.lower - observed.upper
    else:
        gap = Fraction(0)
    # Open-bound violation at the same endpoint has distance 0 but remains a conflict.
    norm = None if scale is None else float(min(Fraction(1), abs(delta if delta is not None else gap) / scale))
    return status, {
        'expected_normalized': primitive(expected), 'observed_normalized': primitive(observed),
        'signed_delta': number_text(delta), 'boundary_gap': number_text(gap),
        'normalized_magnitude': norm, 'normalization_scale': number_text(scale),
        'relation': relation, 'raw_conflict': status is PairStatus.CONFLICT,
        'interpretation': 'comparison of representations; not an adjudication of physical truth',
    }, raw


def beta_calibration(successes: int, trials: int, alpha: Any = 1, beta: Any = 1) -> dict[str, Any]:
    """Optional, explicitly modeled beta-binomial update for a defined calibration bin.

    Assumes exchangeable Bernoulli outcomes. Callers define population, independence,
    held-out protocol and relevance; this does not calibrate arbitrary tracker scores.
    """
    if type(successes) is not int or type(trials) is not int or not 0 <= successes <= trials:
        raise ValueError('need 0 <= integer successes <= integer trials')
    a, b = number(alpha), number(beta)
    if a <= 0 or b <= 0:
        raise ValueError('beta prior parameters must be positive')
    aa, bb = a + successes, b + trials - successes
    mean = aa / (aa + bb)
    var = aa * bb / ((aa + bb) ** 2 * (aa + bb + 1))
    return {'model': 'beta-binomial; exchangeable outcomes assumed', 'trials': trials,
            'successes': successes, 'posterior_alpha': number_text(aa), 'posterior_beta': number_text(bb),
            'posterior_mean': float(mean), 'posterior_variance': float(var),
            'data_available': trials > 0, 'warning': 'zero trials gives a prior, not measured calibration'}
