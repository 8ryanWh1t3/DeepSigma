#!/usr/bin/env python3
"""Drift-to-Patch automation CLI tool.

Closes #9.

Reads drift events, classifies them, and generates patch suggestions.

Usage:
    python tools/drift_to_patch.py --input examples/drift/
        python tools/drift_to_patch.py --input examples/drift/ --output patches/
            python tools/drift_to_patch.py --input examples/drift/ --dry-run
            """
from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List


PATCH_RULES: Dict[str, Dict[str, Any]] = {
      "time": {
                "suggestedAction": "dte_change",
                "description": "Increase decisionWindowMs or reduce P99 latency",
                "confidence": 0.8,
      },
      "freshness": {
                "suggestedAction": "ttl_change",
                "description": "Tighten TTL bounds or increase cache refresh frequency",
                "confidence": 0.85,
      },
      "fallback": {
                "suggestedAction": "routing_change",
                "description": "Review degrade ladder step thresholds",
                "confidence": 0.7,
      },
      "verify": {
                "suggestedAction": "verification_change",
                "description": "Investigate verification failures and tighten action contracts",
                "confidence": 0.9,
      },
      "bypass": {
                "suggestedAction": "action_scope_tighten",
                "description": "Review bypass conditions and add guardrails",
                "confidence": 0.75,
      },
      "outcome": {
                "suggestedAction": "manual_review",
                "description": "Unexpected outcome requires human investigation",
                "confidence": 0.5,
      },
}


def iso_now() -> str:
      return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_drift_events(input_path: Path) -> List[Dict[str, Any]]:
      """Load drift events from a directory or single file."""
      events = []
      if input_path.is_file():
                events.append(json.loads(input_path.read_text(encoding="utf-8")))
elif input_path.is_dir():
        for f in sorted(input_path.glob("*.json")):
                      if "drift" in f.name or f.name.endswith(".drift.json"):
                                        events.append(json.loads(f.read_text(encoding="utf-8")))
                                if not events:
                                              for f in sorted(input_path.glob("*.json")):
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
              "patchId": "patch_" + uuid.uuid4().hex[:12],
              "driftEventId": event.get("driftId", "unknown"),
              "episodeId": event.get("episodeId", "unknown"),
              "driftType": drift_type,
              "severity": severity,
              "suggestedAction": rule.get("suggestedAction", "manual_review"),
              "description": rule.get("description", "Requires manual investigation"),
              "confidence": rule.get("confidence", 0.5),
              "generatedAt": iso_now(),
    }


def main():
      ap = argparse.ArgumentParser(description="Generate patch suggestions from drift events")
    ap.add_argument("--input", required=True, help="Drift events directory or file")
    ap.add_argument("--output", help="Output directory for patch files")
    ap.add_argument("--dry-run", action="store_true", help="Print suggestions without writing")
    args = ap.parse_args()

    events = load_drift_events(Path(args.input))

    if not events:
              print(f"No drift events found in {args.input}")
        raise SystemExit(0)

    patches = [generate_patch(e) for e in events]

    if args.dry_run or not args.output:
              report = {
                            "generatedAt": iso_now(),
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
