"""Read-after-write verifier (scaffold)."""

from __future__ import annotations
from typing import Any, Dict

def verify(read_fn, expected: Dict[str, Any]) -> Dict[str, Any]:
    """
    read_fn: callable that returns the authoritative state after the write.
    expected: dict of expected key/value postconditions.

    Returns: {result: pass|fail|inconclusive, details: {...}}
    """
    try:
        state = read_fn()
    except Exception as e:
        return {"result": "inconclusive", "details": {"error": str(e)}}

    mismatches = {}
    for k, v in expected.items():
        if state.get(k) != v:
            mismatches[k] = {"expected": v, "got": state.get(k)}

    if mismatches:
        return {"result": "fail", "details": {"mismatches": mismatches, "state": state}}
    return {"result": "pass", "details": {"state": state}}
