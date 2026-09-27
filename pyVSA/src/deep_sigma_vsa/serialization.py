from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any


def to_primitive(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): to_primitive(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_primitive(v) for v in value]
    return value


def dumps(value: Any, *, indent: int | None = None) -> str:
    return json.dumps(to_primitive(value), indent=indent, sort_keys=True, ensure_ascii=False)
