#!/usr/bin/env python3
"""Replay Harness (Scaffold)

Purpose:
- Re-run a sealed DecisionEpisode against recorded context (or stubs)
- Compare expected vs observed outcomes (dual-run / regression)

Usage:
  python tools/replay_episode.py examples/episodes/01_success.json

This is a scaffold: it demonstrates the structure and outputs a replay report.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/replay_episode.py <episode.json>")
        raise SystemExit(2)

    p = Path(sys.argv[1])
    episode = json.loads(p.read_text(encoding="utf-8"))

    report = {
        "replayAt": iso_now(),
        "episodeId": episode.get("episodeId"),
        "decisionType": episode.get("decisionType"),
        "mode": "stub",
        "notes": "Scaffold replay: no external tools invoked. Replace stubs with real adapters.",
        "checks": {
            "sealPresent": bool(episode.get("seal")),
            "hasDeadlines": "decisionWindowMs" in episode,
            "hasFreshness": "context" in episode and ("ttlMs" in episode["context"] or "maxFeatureAgeMs" in episode["context"]),
            "hasVerification": "verification" in episode
        },
        "result": "ok"
    }

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
