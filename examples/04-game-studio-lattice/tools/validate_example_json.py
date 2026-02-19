#!/usr/bin/env python3
"""Validate Game Studio Lattice example JSON files.

Checks that episodes, drift signals, and patch artifacts have required
top-level keys. Uses only stdlib (json, glob, sys, pathlib).

Usage:
    python ./examples/04-game-studio-lattice/tools/validate_example_json.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EXAMPLE_DIR = Path(__file__).resolve().parent.parent

# Required keys per artifact type (best-effort — warn on extras, fail on missing ID)
EPISODE_REQUIRED = {
    "id_fields": ["episode_id", "episodeId"],  # accept either
    "required": ["title", "severity", "claims_affected", "seal"],
    "recommended": ["domain_primary", "domains_affected", "dlr", "rs", "ds", "mg"],
}

DRIFT_REQUIRED = {
    "id_fields": ["ds_id", "drift_id", "driftId", "signal_id"],
    "required": ["severity", "domains_affected", "affected_claims"],
    "recommended": ["category", "detected_at", ["correlation_group", "correlation_groups"]],
}

PATCH_REQUIRED = {
    "id_fields": ["patch_id", "patchId"],
    "required": ["trigger_drift_signal", "patch_sequence", "closure_conditions"],
    "recommended": ["severity", "domains", "selected_option"],
}


def _has_any_key(data: dict, keys: list[str]) -> str | None:
    """Return the first matching key found, or None."""
    for k in keys:
        if k in data:
            return k
    return None


def validate_files(
    directory: Path,
    spec: dict,
    label: str,
) -> tuple[int, int, list[str]]:
    """Validate all .json files in directory against spec.

    Returns (passed, failed, messages).
    """
    passed = 0
    failed = 0
    messages: list[str] = []

    json_files = sorted(directory.glob("*.json"))
    if not json_files:
        messages.append(f"  WARNING: No .json files found in {directory.name}/")
        return passed, failed, messages

    for fp in json_files:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            failed += 1
            messages.append(f"  FAIL {fp.name}: Invalid JSON — {e}")
            continue

        issues: list[str] = []
        warnings: list[str] = []

        # Check ID field
        id_key = _has_any_key(data, spec["id_fields"])
        if id_key is None:
            issues.append(f"missing ID (expected one of: {spec['id_fields']})")

        # Check required fields
        for key in spec["required"]:
            if key not in data:
                issues.append(f"missing required key: {key}")

        # Check recommended fields (warn only)
        for key in spec.get("recommended", []):
            if isinstance(key, list):
                # Accept any of the listed alternatives
                if not any(k in data for k in key):
                    warnings.append(f"missing recommended key: {' or '.join(key)}")
            elif key not in data:
                warnings.append(f"missing recommended key: {key}")

        if issues:
            failed += 1
            messages.append(f"  FAIL {fp.name}: {'; '.join(issues)}")
        else:
            passed += 1
            status = "PASS"
            if warnings:
                status += f" (warnings: {'; '.join(warnings)})"
            messages.append(f"  {status} {fp.name}")

    return passed, failed, messages


def main() -> None:
    print("Game Studio Lattice — JSON Validation")
    print("=" * 50)

    total_passed = 0
    total_failed = 0

    # Episodes
    ep_dir = EXAMPLE_DIR / "episodes"
    print(f"\nEpisodes ({ep_dir.name}/):")
    p, f, msgs = validate_files(ep_dir, EPISODE_REQUIRED, "episode")
    total_passed += p
    total_failed += f
    for m in msgs:
        print(m)

    # Drift signals
    ds_dir = EXAMPLE_DIR / "drift_signals"
    print(f"\nDrift Signals ({ds_dir.name}/):")
    p, f, msgs = validate_files(ds_dir, DRIFT_REQUIRED, "drift_signal")
    total_passed += p
    total_failed += f
    for m in msgs:
        print(m)

    # Patches
    patch_dir = EXAMPLE_DIR / "patches"
    print(f"\nPatches ({patch_dir.name}/):")
    p, f, msgs = validate_files(patch_dir, PATCH_REQUIRED, "patch")
    total_passed += p
    total_failed += f
    for m in msgs:
        print(m)

    # Summary
    print("\n" + "=" * 50)
    total = total_passed + total_failed
    print(f"Total: {total} files checked — {total_passed} passed, {total_failed} failed")

    if total_failed > 0:
        print("\nValidation FAILED")
        sys.exit(1)
    else:
        print("\nAll files valid")


if __name__ == "__main__":
    main()
