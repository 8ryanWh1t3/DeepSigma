from __future__ import annotations

import hashlib
from typing import Any

from .serde import canonical_json


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_id(prefix: str, value: Any, *, length: int = 16) -> str:
    return f"{prefix}-{stable_hash(value)[:length]}"
