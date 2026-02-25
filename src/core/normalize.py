"""Key normalization utilities for DecisionEpisode data.

Converts mixed-case keys to a canonical form at ingestion boundaries,
eliminating dual-access patterns throughout the codebase.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Union, overload

_SNAKE_RE = re.compile(r"_([a-z])")


def _snake_to_camel(key: str) -> str:
    """Convert a single snake_case key to camelCase."""
    return _SNAKE_RE.sub(lambda m: m.group(1).upper(), key)


@overload
def normalize_keys(data: Dict[str, Any], style: str = ...) -> Dict[str, Any]: ...
@overload
def normalize_keys(data: List[Any], style: str = ...) -> List[Any]: ...
@overload
def normalize_keys(data: Any, style: str = ...) -> Any: ...


def normalize_keys(
    data: Union[Dict[str, Any], List[Any], Any],
    style: str = "camel",
) -> Union[Dict[str, Any], List[Any], Any]:
    """Deep-normalize dictionary keys to the specified style.

    Args:
        data: A dict or list of dicts to normalize.
        style: Target style. Currently only "camel" (snake_case -> camelCase).

    Returns:
        A new dict/list with all keys converted.
    """
    if style != "camel":
        raise ValueError(f"Unsupported normalize style: {style!r}")

    if isinstance(data, list):
        return [normalize_keys(item, style) for item in data]
    if isinstance(data, dict):
        return {
            _snake_to_camel(k): normalize_keys(v, style)
            for k, v in data.items()
        }
    return data
