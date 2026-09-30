from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Any, Mapping, Sequence

from .exceptions import InvalidConstraint, UnitError
from .models import ConstraintEvaluation, ConstraintStatus


_UNIT_TABLE: dict[str, tuple[str, float]] = {
    "mm": ("length", 0.001),
    "cm": ("length", 0.01),
    "m": ("length", 1.0),
    "in": ("length", 0.0254),
    "ft": ("length", 0.3048),
    "s": ("time", 1.0),
    "min": ("time", 60.0),
    "h": ("time", 3600.0),
    "day": ("time", 86400.0),
}


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str

    def __post_init__(self) -> None:
        if self.unit not in _UNIT_TABLE:
            raise UnitError(f"unsupported unit: {self.unit}")

    @property
    def dimension(self) -> str:
        return _UNIT_TABLE[self.unit][0]

    def base_value(self) -> float:
        return float(self.value) * _UNIT_TABLE[self.unit][1]

    def convert_to(self, unit: str) -> "Quantity":
        if unit not in _UNIT_TABLE:
            raise UnitError(f"unsupported unit: {unit}")
        dim, scale = _UNIT_TABLE[unit]
        if dim != self.dimension:
            raise UnitError(f"incompatible units: {self.unit} and {unit}")
        return Quantity(self.base_value() / scale, unit)


def _coerce_quantity(value: Any) -> Any:
    if isinstance(value, Quantity):
        return value
    if isinstance(value, Mapping) and set(value.keys()) >= {"value", "unit"}:
        return Quantity(float(value["value"]), str(value["unit"]))
    return value


def _resolve(payload: Mapping[str, Any], field: str) -> tuple[bool, Any]:
    current: Any = payload
    for part in field.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return False, None
    return True, current


def _compare(actual: Any, op: str, expected: Any) -> bool:
    actual = _coerce_quantity(actual)
    expected = _coerce_quantity(expected)

    if isinstance(actual, Quantity) or isinstance(expected, Quantity):
        if not isinstance(actual, Quantity) or not isinstance(expected, Quantity):
            raise UnitError("quantity comparison requires units on both sides")
        if actual.dimension != expected.dimension:
            raise UnitError(f"dimension mismatch: {actual.dimension} vs {expected.dimension}")
        a = actual.base_value()
        e = expected.base_value()
        if op == "eq":
            return isclose(a, e, rel_tol=1e-12, abs_tol=1e-12)
        if op == "ne":
            return not isclose(a, e, rel_tol=1e-12, abs_tol=1e-12)
        if op == "gt":
            return a > e
        if op == "gte":
            return a >= e or isclose(a, e, rel_tol=1e-12, abs_tol=1e-12)
        if op == "lt":
            return a < e
        if op == "lte":
            return a <= e or isclose(a, e, rel_tol=1e-12, abs_tol=1e-12)
        raise InvalidConstraint(f"operator {op!r} is not supported for quantities")

    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "gt":
        return actual > expected
    if op == "gte":
        return actual >= expected
    if op == "lt":
        return actual < expected
    if op == "lte":
        return actual <= expected
    if op == "in":
        return actual in expected
    if op == "not_in":
        return actual not in expected
    if op == "contains":
        return expected in actual
    if op == "exists":
        return bool(actual) is bool(expected)
    if op == "between":
        if not isinstance(expected, Sequence) or isinstance(expected, (str, bytes)) or len(expected) != 2:
            raise InvalidConstraint("between expects a two-item sequence")
        return expected[0] <= actual <= expected[1]
    raise InvalidConstraint(f"unsupported operator: {op}")


@dataclass(frozen=True)
class Constraint:
    id: str
    field: str
    op: str
    expected: Any
    hard: bool = True
    weight: float = 1.0
    description: str = ""
    evidence_refs: tuple[str, ...] | list[str] = ()
    provenance_ref: str | None = None
    authority_ref: str | None = None
    authority_scope: str = "*"
    authority_action: str = "DEFINE_CONSTRAINT"
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise InvalidConstraint("constraint id cannot be empty")
        if not self.field.strip():
            raise InvalidConstraint("constraint field cannot be empty")
        if self.weight <= 0:
            raise InvalidConstraint("constraint weight must be > 0")
        if not self.authority_scope.strip():
            raise InvalidConstraint("constraint authority_scope cannot be empty")
        if not self.authority_action.strip():
            raise InvalidConstraint("constraint authority_action cannot be empty")
        object.__setattr__(self, "evidence_refs", tuple(str(v) for v in self.evidence_refs))

    def evaluate(self, payload: Mapping[str, Any]) -> ConstraintEvaluation:
        found, actual = _resolve(payload, self.field)
        if not found:
            return ConstraintEvaluation(
                constraint_id=self.id,
                status=ConstraintStatus.UNKNOWN,
                hard=self.hard,
                weight=self.weight,
                field=self.field,
                op=self.op,
                expected=self.expected,
                actual=None,
                reason="field not present",
                description=self.description,
            )

        try:
            passed = _compare(actual, self.op, self.expected)
        except (TypeError, ValueError, UnitError, InvalidConstraint) as exc:
            return ConstraintEvaluation(
                constraint_id=self.id,
                status=ConstraintStatus.UNKNOWN,
                hard=self.hard,
                weight=self.weight,
                field=self.field,
                op=self.op,
                expected=self.expected,
                actual=actual,
                reason=str(exc),
                description=self.description,
            )

        return ConstraintEvaluation(
            constraint_id=self.id,
            status=ConstraintStatus.PASS if passed else ConstraintStatus.FAIL,
            hard=self.hard,
            weight=self.weight,
            field=self.field,
            op=self.op,
            expected=self.expected,
            actual=actual,
            reason="",
            description=self.description,
        )
