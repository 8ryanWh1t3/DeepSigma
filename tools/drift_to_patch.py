#!/usr/bin/env python3
"""Drift-to-patch automation CLI. Closes #5, closes #9.

Reads drift events and generates policy pack patch suggestions.

Usage:
    python tools/drift_to_patch.py --input data/ --output patches/ --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


PATCH_RULES: Dict[str, Dict[str, Any]] = {
    "ttl_breach": {
        "action": "increase_ttl",
        "description": "Increase TTL to reduce freshness breaches",
        "field": "ttlMs",
        "multiplier": 1.5,
    },
    "budget_overrun": {
        "action": "increase_budget",
        "description": "Increase decision window to reduce budget overruns",
        "field": "decisionWindowMs",
        "multiplier": 1.3,
    },
    "verification_failure": {
        "action": "add_hitl_step",
        "description": "Add human-in-the-loop degrade step for verification failures",
        "field": "degradeLadder",
        "insert": "hitl",
    },
    "repeated_degrade": {
        "action": "reorder_ladder",
        "description": "Move frequently used degrade step earlier in ladder",
        "field": "degradeLadder",
    },
}


def _load_drift_events(input_path: Path) -> List[Dict[str, Any]]:
    """Load drift events from a file or directory."""
    events = []
    if input_path.is_file():
        events.append(json.loads(input_path.read_text(encoding="utf-8")))
    elif input_path.is_dir():
        for f in sorted(input_path.glob("*.json")):
            if "drift" in f.name or f.name.endswith(".drift.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if "driftId" in data or "driftType" in data or "type" in data:
                        events.append(data)
                except (json.JSONDecodeError, KeyError):
                    continue
    if not events:
        for f in sorted(input_path.glob("*.json")) if input_path.is_dir() else []:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if "driftId" in data or "driftType" in data or "type" in data:
                    events.append(data)
            except (json.JSONDecodeError, KeyError):
                continue
    return events


def _get_drift_type(event: Dict[str, Any]) -> str:
    """Extract drift type from various event formats."""
    if "driftType" in event:
        return event["driftType"]
    if "type" in event:
        return event["type"]
    drift = event.get("drift", {})
    return drift.get("type", "unknown")


def _get_drift_severity(event: Dict[str, Any]) -> str:
    """Extract severity from various event formats."""
    if "severity" in event:
        return event["severity"]
    drift = event.get("drift", {})
    return drift.get("severity", "yellow")


def generate_patch(event: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a patch suggestion for a single drift event."""
    drift_type = _get_drift_type(event)
    severity = _get_drift_severity(event)

    rule = PATCH_RULES.get(drift_type, PATCH_RULES.get("outcome", {}))

    return {
        "patchId": f"patch-{event.get('driftId', 'unknown')}",
        "driftId": event.get("driftId", ""),
        "driftType": drift_type,
        "severity": severity,
        "action": rule.get("action", "manual_review"),
        "description": rule.get("description", f"Manual review needed for {drift_type}"),
        "field": rule.get("field", ""),
        "suggestion": rule,
    }


def main():
    ap = argparse.ArgumentParser(description="Generate patch suggestions from drift events")
    ap.add_argument("--input", required=True, help="Drift events directory or file")
    ap.add_argument("--output", help="Output directory for patch files")
    ap.add_argument("--dry-run", action="store_true", help="Print suggestions without writing")
    args = ap.parse_args()

    input_path = Path(args.input)
    events = _load_drift_events(input_path)
    if not events:
        print(f"No drift events found in {args.input}")
        raise SystemExit(0)

    patches = [generate_patch(e) for e in events]

    if args.dry_run or not args.output:
        report = {
            "driftEventsProcessed": len(events),
            "patchesGenerated": len(patches),
            "patches": patches,
        }
        print(json.dumps(report, indent=2))
    else:
        out_dir = Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)
        for patch in patches:
            path = out_dir / f"{patch['patchId']}.json"
            path.write_text(json.dumps(patch, indent=2), encoding="utf-8")
        print(f"Generated {len(patches)} patch suggestions in {args.output}/")


if __name__ == "__main__":
    main()
