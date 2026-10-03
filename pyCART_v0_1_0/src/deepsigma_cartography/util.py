"""Strict, deterministic JSON and time utilities. Not RFC 8785 canonicalization."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

VERSION = "0.1.0"
SCHEMA = "deepsigma.cartography/1"


class CartographyError(Exception):
    """Base error for invalid input, missing records, and integrity failures."""


class ValidationError(CartographyError, ValueError):
    """A supplied representation violates the declared contract."""


class IntegrityError(CartographyError):
    """Stored bytes, sequence, or a pinned digest failed verification."""


class ConflictError(CartographyError):
    """Optimistic concurrency rejected a stale parent edition."""


def text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a nonempty string")
    if any(ord(c) < 32 for c in value):
        raise ValidationError(f"{field} must not contain control characters")
    return value


def instant(value: str | datetime) -> datetime:
    try:
        dt = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValidationError("Expected an ISO 8601 timestamp with a timezone") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValidationError("Naive timestamps are not accepted; supply Z or an offset")
    return dt.astimezone(timezone.utc)


def timestamp(value: str | datetime) -> str:
    return instant(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def freeze(value: Any) -> Any:
    """Defensively copy JSON values into deeply immutable containers."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError("NaN and infinity are not JSON values")
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(k, str) for k in value):
            raise ValidationError("JSON object keys must be strings")
        return MappingProxyType({k: freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    raise ValidationError(f"Unsupported JSON value type: {type(value).__name__}")


def plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if dataclasses.is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)
                if not f.name.startswith("_")}
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(plain(value), sort_keys=True, ensure_ascii=True,
                          separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ValidationError("Value cannot be serialized as strict JSON") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def parse_json(data: str) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        obj: dict[str, Any] = {}
        for key, value in pairs:
            if key in obj:
                raise ValidationError(f"Duplicate JSON key: {key}")
            obj[key] = value
        return obj

    def nonfinite(value: str) -> None:
        raise ValidationError(f"Nonfinite JSON number: {value}")

    try:
        return json.loads(data, object_pairs_hook=unique, parse_constant=nonfinite)
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"Invalid JSON: {exc}") from exc


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def strings(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValidationError(f"{name} must be a sequence of strings")
    result = tuple(text(v, name) for v in value)
    if len(set(result)) != len(result):
        raise ValidationError(f"{name} contains duplicates")
    return tuple(sorted(result))


class Record:
    def to_dict(self) -> dict[str, Any]:
        return plain(self)
