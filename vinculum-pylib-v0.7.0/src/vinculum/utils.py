"""Exact numeric boundaries and deterministic serialization for cross-order evaluation."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from fractions import Fraction
import hashlib
import json
import math
from typing import Any


def number(value: Any) -> Fraction:
    """Accept finite decimal numbers, or exact 'numerator/denominator' strings.

    Floats are interpreted through their decimal string, not their binary expansion.
    Use strings/Decimal/Fraction for precision-sensitive input. Booleans are not counts.
    """
    if isinstance(value, bool):
        raise ValueError('boolean is not a numeric measurement')
    if isinstance(value, Fraction):
        result = value
    else:
        s = str(value)
        if len(s) > 4096:
            raise ValueError('numeric literal too long')
        try:
            if '/' in s:
                parts = s.split('/')
                if len(parts) != 2 or not all(p.lstrip('+-').isdigit() for p in parts):
                    raise ValueError('invalid fraction')
                result = Fraction(int(parts[0]), int(parts[1]))
            else:
                d = Decimal(s)
                if not d.is_finite() or abs(d.adjusted()) > 1000:
                    raise ValueError('measurement must be finite and bounded in size')
                result = Fraction(d)
        except (InvalidOperation, ZeroDivisionError, TypeError, OverflowError) as exc:
            raise ValueError('invalid numeric measurement') from exc
    if result.numerator.bit_length() > 4096 or result.denominator.bit_length() > 4096:
        raise ValueError('numeric representation too large')
    return result


def number_text(value: Fraction | None) -> str | None:
    if value is None:
        return None
    value = number(value)
    if value.denominator == 1:
        return str(value.numerator)
    # Use exact decimal text only for terminating expansions; otherwise preserve a fraction.
    den, twos, fives = value.denominator, 0, 0
    while den % 2 == 0:
        den //= 2
        twos += 1
    while den % 5 == 0:
        den //= 5
        fives += 1
    if den != 1:
        return f'{value.numerator}/{value.denominator}'
    places = max(twos, fives)
    n = abs(value.numerator) * (10 ** places // value.denominator)
    s = str(n).rjust(places + 1, '0')
    return ('-' if value < 0 else '') + s[:-places] + '.' + s[-places:]


def unit_score(value: Any, name: str = 'score') -> float | None:
    """Scores must be explicitly 0..1; never guess whether 95 means .95."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f'{name} cannot be boolean')
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ValueError(f'{name} must be finite and in [0, 1]')
    return result


def identifier(value: str, name: str = 'identifier') -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 2048:
        raise ValueError(f'{name} must be a nonempty string of at most 2048 characters')
    return value


def timestamp(value: str | datetime) -> datetime:
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('timestamps must include an explicit timezone')
    return dt.astimezone(timezone.utc)


def primitive(obj: Any) -> Any:
    if isinstance(obj, Fraction):
        return number_text(obj)
    if isinstance(obj, Decimal):
        return number_text(number(obj))
    if isinstance(obj, datetime):
        return timestamp(obj).isoformat().replace('+00:00', 'Z')
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return {f.name: primitive(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, dict):
        return {str(k): primitive(v) for k, v in obj.items()}
    if isinstance(obj, (tuple, list)):
        return [primitive(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError('nonfinite JSON value')
    return obj


def canonical_json(obj: Any) -> str:
    return json.dumps(primitive(obj), sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def fingerprint(obj: Any) -> str:
    """Content fingerprint, NOT an authenticity signature or an authority grant."""
    return hashlib.sha256(canonical_json(obj).encode('utf-8')).hexdigest()


def read_json(text: str) -> Any:
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError(f'duplicate JSON key: {k}')
            out[k] = v
        return out
    def bad_constant(s):
        raise ValueError(f'invalid JSON constant: {s}')
    return json.loads(text, object_pairs_hook=unique, parse_constant=bad_constant)
