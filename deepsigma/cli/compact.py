"""deepsigma compact — JSONL evidence compaction.

Merges daily JSONL files into weekly/monthly rollups, deduplicates
redundant records, and organizes archives into hot/warm/cold tiers.

Usage:
    deepsigma compact --input /path/to/evidence --retention 30
    deepsigma compact --input /path/to/evidence --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Fields that identify unique records by type
_ID_FIELDS = {
    "events": "event_id",
    "drift": "drift_id",
    "claims": "id",
    "correlation": "id",
    "snapshots": "id",
    "sync": "id",
    "envelopes": "envelope_id",
    "replication": "id",
}

# Default heartbeat event types to deduplicate
_HEARTBEAT_TYPES = frozenset({"heartbeat", "ping", "health_check", "keepalive"})


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "compact",
        help="Compact JSONL evidence files (dedup + tier)",
    )
    p.add_argument(
        "--input", "-i", required=True,
        help="Directory containing JSONL files to compact",
    )
    p.add_argument(
        "--retention", "-r", type=int, default=30,
        help="Days to keep in hot tier (default: 30)",
    )
    p.add_argument(
        "--warm-days", type=int, default=7,
        help="Days after retention before moving to cold (default: 7)",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen without making changes",
    )
    p.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output results as JSON",
    )
    p.set_defaults(func=run)


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load records from a JSONL file, skipping malformed lines."""
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    """Atomically write records to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, default=str) + "\n")
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _dedupe_records(
    records: List[Dict[str, Any]], id_field: str
) -> List[Dict[str, Any]]:
    """Deduplicate records by ID, keeping last occurrence."""
    seen: Dict[str, Dict[str, Any]] = {}
    no_id: List[Dict[str, Any]] = []
    for r in records:
        key = r.get(id_field, "")
        if key:
            seen[key] = r
        else:
            no_id.append(r)
    return list(seen.values()) + no_id


def _strip_heartbeats(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove redundant heartbeat events, keeping one per hour."""
    non_heartbeat = []
    heartbeat_by_hour: Dict[str, Dict[str, Any]] = {}

    for r in records:
        event_type = r.get("event_type", "")
        if event_type in _HEARTBEAT_TYPES:
            ts = r.get("timestamp", "")[:13]  # YYYY-MM-DDTHH
            heartbeat_by_hour[ts] = r  # keep last per hour
        else:
            non_heartbeat.append(r)

    return non_heartbeat + list(heartbeat_by_hour.values())


def _tier_records(
    records: List[Dict[str, Any]],
    now: datetime,
    retention_days: int,
    warm_days: int,
) -> Dict[str, List[Dict[str, Any]]]:
    """Split records into hot/warm/cold tiers by timestamp."""
    hot_cutoff = (now - timedelta(days=retention_days)).isoformat()
    warm_cutoff = (now - timedelta(days=retention_days + warm_days)).isoformat()

    hot: List[Dict[str, Any]] = []
    warm: List[Dict[str, Any]] = []
    cold: List[Dict[str, Any]] = []

    for r in records:
        ts = r.get("timestamp", "")
        if ts >= hot_cutoff:
            hot.append(r)
        elif ts >= warm_cutoff:
            warm.append(r)
        else:
            cold.append(r)

    return {"hot": hot, "warm": warm, "cold": cold}


def compact_file(
    path: Path,
    retention_days: int = 30,
    warm_days: int = 7,
    dry_run: bool = False,
    now: datetime | None = None,
) -> Dict[str, Any]:
    """Compact a single JSONL file.

    Returns a summary dict with counts.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    stem = path.stem
    id_field = _ID_FIELDS.get(stem, "id")

    records = _load_jsonl(path)
    original_count = len(records)

    if original_count == 0:
        return {
            "file": str(path),
            "original": 0,
            "deduped": 0,
            "hot": 0,
            "warm": 0,
            "cold": 0,
            "removed_heartbeats": 0,
        }

    # Step 1: Deduplicate
    deduped = _dedupe_records(records, id_field)

    # Step 2: Strip heartbeats
    cleaned = _strip_heartbeats(deduped)
    heartbeats_removed = len(deduped) - len(cleaned)

    # Step 3: Tier by age
    tiers = _tier_records(cleaned, now, retention_days, warm_days)

    summary = {
        "file": str(path),
        "original": original_count,
        "deduped": len(deduped),
        "hot": len(tiers["hot"]),
        "warm": len(tiers["warm"]),
        "cold": len(tiers["cold"]),
        "removed_heartbeats": heartbeats_removed,
    }

    if not dry_run:
        parent = path.parent
        base = path.stem

        # Write hot tier (replaces original)
        if tiers["hot"]:
            _write_jsonl(path, tiers["hot"])
        elif path.exists():
            path.unlink()

        # Write warm tier
        if tiers["warm"]:
            _write_jsonl(parent / f"{base}-warm.jsonl", tiers["warm"])

        # Write cold tier
        if tiers["cold"]:
            _write_jsonl(parent / f"{base}-cold.jsonl", tiers["cold"])

    return summary


def compact_directory(
    input_dir: Path,
    retention_days: int = 30,
    warm_days: int = 7,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    """Compact all JSONL files in a directory (recursively)."""
    results = []
    now = datetime.now(timezone.utc)

    for jsonl_file in sorted(input_dir.rglob("*.jsonl")):
        # Skip already-tiered files
        if jsonl_file.stem.endswith("-warm") or jsonl_file.stem.endswith("-cold"):
            continue

        result = compact_file(
            jsonl_file,
            retention_days=retention_days,
            warm_days=warm_days,
            dry_run=dry_run,
            now=now,
        )
        results.append(result)

    return results


def run(args: argparse.Namespace) -> int:
    input_dir = Path(args.input)
    if not input_dir.is_dir():
        print(f"Error: {input_dir} is not a directory", file=sys.stderr)
        return 1

    results = compact_directory(
        input_dir,
        retention_days=args.retention,
        warm_days=args.warm_days,
        dry_run=args.dry_run,
    )

    if args.json_output:
        print(json.dumps({"compaction": results}, indent=2))
    else:
        total_original = sum(r["original"] for r in results)
        total_hot = sum(r["hot"] for r in results)
        total_warm = sum(r["warm"] for r in results)
        total_cold = sum(r["cold"] for r in results)
        total_hb = sum(r["removed_heartbeats"] for r in results)

        mode = "[DRY RUN] " if args.dry_run else ""
        print(f"{mode}Compacted {len(results)} JSONL files:")
        print(f"  Original: {total_original} records")
        print(f"  Hot:      {total_hot} records")
        print(f"  Warm:     {total_warm} records")
        print(f"  Cold:     {total_cold} records")
        if total_hb:
            print(f"  Heartbeats removed: {total_hb}")

    return 0
