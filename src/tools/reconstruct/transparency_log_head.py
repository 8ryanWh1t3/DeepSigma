#!/usr/bin/env python3
"""Transparency log head generator — snapshot of current log state.

Produces a LOG_HEAD.json capturing the latest entry, entry count, and
a SHA-256 of the full log content for anchoring or external attestation.

Usage:
    python src/tools/reconstruct/transparency_log_head.py \
        --log-path artifacts/transparency_log/log.ndjson

    python src/tools/reconstruct/transparency_log_head.py \
        --log-path artifacts/transparency_log/log.ndjson \
        --out /tmp/LOG_HEAD.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from time_controls import observed_now  # noqa: E402


def generate_head(log_path: Path) -> dict:
    """Read the transparency log and return a head snapshot dict."""
    if not log_path.exists():
        return {
            "head_version": "1.0",
            "entry_count": 0,
            "latest_entry_id": None,
            "latest_entry_hash": None,
            "chain_head_hash": None,
            "generated_at": observed_now(),
        }

    text = log_path.read_text()
    stripped = text.strip()

    if not stripped:
        return {
            "head_version": "1.0",
            "entry_count": 0,
            "latest_entry_id": None,
            "latest_entry_hash": None,
            "chain_head_hash": None,
            "generated_at": observed_now(),
        }

    # Count entries and find last
    lines = stripped.split("\n")
    entries = []
    for line in lines:
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not entries:
        return {
            "head_version": "1.0",
            "entry_count": 0,
            "latest_entry_id": None,
            "latest_entry_hash": None,
            "chain_head_hash": None,
            "generated_at": observed_now(),
        }

    last = entries[-1]

    # SHA-256 of full log content
    chain_head_hash = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    return {
        "head_version": "1.0",
        "entry_count": len(entries),
        "latest_entry_id": last.get("entry_id"),
        "latest_entry_hash": last.get("entry_hash"),
        "chain_head_hash": chain_head_hash,
        "generated_at": observed_now(),
    }


def write_head(log_path: Path, out_path: Path | None = None) -> Path:
    """Generate and write LOG_HEAD.json. Returns the output path."""
    head = generate_head(log_path)
    if out_path is None:
        out_path = log_path.parent / "LOG_HEAD.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write(json.dumps(head, indent=2, sort_keys=True) + "\n")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transparency log head generator — snapshot of log state"
    )
    parser.add_argument("--log-path", type=Path, required=True,
                        help="Path to transparency log NDJSON")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output path (default: <log_dir>/LOG_HEAD.json)")
    args = parser.parse_args()

    head_path = write_head(args.log_path, args.out)
    head = json.loads(head_path.read_text())

    print("=" * 55)
    print("  Transparency Log Head")
    print("=" * 55)
    print(f"  Entries:    {head['entry_count']}")
    print(f"  Latest ID:  {head['latest_entry_id'] or '(empty)'}")
    print(f"  Head hash:  {head['chain_head_hash'] or '(empty)'}")
    print(f"  Written to: {head_path}")
    print("=" * 55)

    return 0


if __name__ == "__main__":
    sys.exit(main())
