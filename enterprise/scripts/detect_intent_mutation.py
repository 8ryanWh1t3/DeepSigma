#!/usr/bin/env python3
"""Detect intent mutations between sealed runs.

Compares intent packets across consecutive sealed runs to flag unintended
changes to decision intent fields. Returns non-zero if drift is detected
without an explicit intent amendment record.

Supports --self-check for CI validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any


INTENT_FIELDS = [
    "decision_type",
    "objective",
    "constraints",
    "authority_required",
    "blast_radius",
    "reversibility",
]


def compute_intent_hash(intent: dict[str, Any]) -> str:
    """Compute a stable hash over intent-critical fields."""
    payload = {k: intent.get(k) for k in INTENT_FIELDS if k in intent}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def detect_mutations(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare two intent packets and return list of mutated fields."""
    mutations = []
    for field in INTENT_FIELDS:
        old_val = baseline.get(field)
        new_val = current.get(field)
        if old_val != new_val:
            mutations.append({
                "field": field,
                "baseline": old_val,
                "current": new_val,
            })
    return mutations


def check_intent_pair(
    baseline_path: Path,
    current_path: Path,
) -> tuple[bool, list[dict[str, Any]]]:
    """Check two intent packet files for mutations."""
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    current = json.loads(current_path.read_text(encoding="utf-8"))
    mutations = detect_mutations(baseline, current)
    return len(mutations) == 0, mutations


def run_self_check() -> int:
    """Validate intent mutation detection with synthetic fixtures."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Test 1: identical intents should pass
        intent_a = {
            "decision_type": "deployment",
            "objective": "ship v2.0.14",
            "constraints": ["zero downtime"],
            "authority_required": "DRI",
            "blast_radius": 3,
            "reversibility": 2,
        }
        mutations = detect_mutations(intent_a, intent_a)
        if mutations:
            print(f"FAIL: identical intents should have no mutations: {mutations}")
            return 2

        # Test 2: mutated field should be detected
        intent_b = dict(intent_a)
        intent_b["blast_radius"] = 5
        mutations = detect_mutations(intent_a, intent_b)
        if len(mutations) != 1:
            print(f"FAIL: expected 1 mutation, got {len(mutations)}")
            return 2
        if mutations[0]["field"] != "blast_radius":
            print(f"FAIL: expected blast_radius mutation, got {mutations[0]['field']}")
            return 2

        # Test 3: hash stability
        h1 = compute_intent_hash(intent_a)
        h2 = compute_intent_hash(intent_a)
        if h1 != h2:
            print("FAIL: intent hash is not stable")
            return 2

        h3 = compute_intent_hash(intent_b)
        if h1 == h3:
            print("FAIL: different intents should have different hashes")
            return 2

        # Test 4: file-based check
        (root / "baseline.json").write_text(json.dumps(intent_a), encoding="utf-8")
        (root / "current.json").write_text(json.dumps(intent_b), encoding="utf-8")
        passed, muts = check_intent_pair(root / "baseline.json", root / "current.json")
        if passed:
            print("FAIL: mutated intent should not pass")
            return 2

    print("PASS: intent mutation detection self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect intent mutations between sealed runs")
    parser.add_argument("--baseline", help="Path to baseline intent packet JSON")
    parser.add_argument("--current", help="Path to current intent packet JSON")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    if not args.baseline or not args.current:
        print("ERROR: --baseline and --current required", file=__import__("sys").stderr)
        return 1

    passed, mutations = check_intent_pair(Path(args.baseline), Path(args.current))
    if passed:
        print("PASS: no intent mutations detected")
        return 0

    print(f"ALERT: {len(mutations)} intent mutation(s) detected:")
    for m in mutations:
        print(f"  {m['field']}: {m['baseline']!r} -> {m['current']!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
