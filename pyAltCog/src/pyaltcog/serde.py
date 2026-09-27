from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Type, TypeVar

T = TypeVar("T")


def to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {k: to_primitive(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): to_primitive(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_primitive(v) for v in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        to_primitive(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def dump_json(value: Any, path: str | Path, *, indent: int = 2) -> None:
    Path(path).write_text(
        json.dumps(to_primitive(value), sort_keys=True, indent=indent, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
