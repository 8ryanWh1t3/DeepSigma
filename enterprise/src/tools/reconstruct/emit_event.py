#!/usr/bin/env python3
"""Deterministic telemetry event emitter.

Event IDs are derived from content hashes (event_type + run_id + payload),
not random number generation. Telemetry is append-only.

Usage:
    python src/tools/reconstruct/emit_event.py \\
        --event-type drift_flag --run-id RUN-abc12345 \\
        --severity RED --payload '{"decision_id": "DEC-001"}'
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from canonical_json import canonical_dumps, sha256_text
from deterministic_ids import det_id
from time_controls import observed_now

DEFAULT_TELEMETRY_DIR = Path("artifacts/sample_data/prompt_os_telemetry")

VALID_EVENT_TYPES = [
    "drift_flag",
    "seal_complete",
    "replay_pass",
    "replay_fail",
    "patch_applied",
]

VALID_SEVERITIES = ["GREEN", "YELLOW", "RED"]

TELEMETRY_COLUMNS = [
    "EventID",
    "Timestamp",
    "EventType",
    "Severity",
    "RunID",
    "Payload",
]


def build_event_id(event_type: str, run_id: str, payload: dict) -> str:
    """Derive a deterministic event ID from content."""
    content = canonical_dumps({
        "event_type": event_type,
        "run_id": run_id,
        "payload": payload,
    })
    h = sha256_text(content)
    return det_id("EVT", h, length=8)


def emit_event(
    event_type: str,
    run_id: str,
    severity: str,
    payload: dict,
    telemetry_dir: Path = DEFAULT_TELEMETRY_DIR,
) -> dict:
    """Build and append a deterministic telemetry event.

    Returns the event dict.
    """
    event_id = build_event_id(event_type, run_id, payload)
    timestamp = observed_now()

    event = {
        "event_id": event_id,
        "event_type": event_type,
        "run_id": run_id,
        "severity": severity,
        "observed_at": timestamp,
        "payload": payload,
    }

    # Append to CSV
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    csv_path = telemetry_dir / "telemetry_events.csv"
    write_header = not csv_path.exists()

    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(TELEMETRY_COLUMNS)
        writer.writerow([
            event_id,
            timestamp,
            event_type,
            severity,
            run_id,
            json.dumps(payload, sort_keys=True),
        ])

    return event


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit a deterministic telemetry event"
    )
    parser.add_argument(
        "--event-type",
        required=True,
        choices=VALID_EVENT_TYPES,
        help="Event type",
    )
    parser.add_argument("--run-id", required=True, help="Sealed run ID")
    parser.add_argument(
        "--severity",
        required=True,
        choices=VALID_SEVERITIES,
        help="Event severity",
    )
    parser.add_argument(
        "--payload",
        default="{}",
        help="JSON payload string",
    )
    parser.add_argument(
        "--telemetry-dir",
        type=Path,
        default=DEFAULT_TELEMETRY_DIR,
        help="Telemetry output directory",
    )
    args = parser.parse_args()

    payload = json.loads(args.payload)
    event = emit_event(
        event_type=args.event_type,
        run_id=args.run_id,
        severity=args.severity,
        payload=payload,
        telemetry_dir=args.telemetry_dir,
    )

    print(f"Emitted: {event['event_id']} ({event['event_type']}/{event['severity']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
