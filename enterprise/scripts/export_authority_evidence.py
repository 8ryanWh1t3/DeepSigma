#!/usr/bin/env python3
"""Export authority evidence chain for release artifacts (#415)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "artifacts" / "authority_ledger" / "ledger.ndjson"
OUT = ROOT / "release_kpis" / "authority_evidence.json"


def _hash_entries(entries: list[dict]) -> str:
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _verify_chain(entries: list[dict]) -> bool:
    """Walk the hash chain and verify continuity."""
    if not entries:
        return True
    for i, entry in enumerate(entries):
        expected_prev = entries[i - 1].get("entry_hash") if i > 0 else None
        if entry.get("prev_entry_hash") != expected_prev:
            return False
    return True


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    # Try JSON array format first, then NDJSON
    entries: list[dict] = []
    if LEDGER_PATH.exists():
        raw = LEDGER_PATH.read_text(encoding="utf-8").strip()
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    entries = [e for e in parsed if isinstance(e, dict)]
                elif isinstance(parsed, dict):
                    entries = [parsed]
            except json.JSONDecodeError:
                # Try NDJSON
                for line in raw.splitlines():
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass

    chain_verified = _verify_chain(entries)

    grant_count = sum(
        1 for e in entries
        if e.get("entry_type") not in ("AUTHORITY_REFUSAL", "snapshot")
    )
    refusal_count = sum(
        1 for e in entries if e.get("entry_type") == "AUTHORITY_REFUSAL"
    )
    signing_key_ids = sorted(
        {e.get("signing_key_id", "default") for e in entries if "signing_key_id" in e}
    ) or ["default"]

    evidence = {
        "schema": "authority_evidence_v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ledger_path": str(LEDGER_PATH.relative_to(ROOT)),
        "chain_verified": chain_verified,
        "chain_length": len(entries),
        "grant_count": grant_count,
        "refusal_count": refusal_count,
        "signing_key_ids": signing_key_ids,
        "verification_hash": _hash_entries(entries),
        "entries": entries,
    }

    OUT.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
