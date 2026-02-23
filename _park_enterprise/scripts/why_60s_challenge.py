#!/usr/bin/env python3
from __future__ import annotations

import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "pilot"

PROMPTS = [
    ("Find the most recent Decision (DLR) file in pilot/decisions", PILOT / "decisions"),
    ("Find any Assumption file A-* in pilot/assumptions", PILOT / "assumptions"),
    ("Find any Drift file DRIFT-* in pilot/drift", PILOT / "drift"),
    ("Find any Patch file PATCH-* in pilot/patches", PILOT / "patches"),
]


def main() -> int:
    print("WHY-60s Challenge — total time limit: 60 seconds.")
    start = time.time()

    for i, (q, path) in enumerate(PROMPTS, 1):
        if (time.time() - start) > 60:
            print("TIME — FAIL")
            return 2
        print(f"[{i}/4] {q}")
        print(f"Folder: {path}")
        input("Press ENTER when you have the answer.")

    total = time.time() - start
    print(f"Done. Time: {total:.1f}s")
    if total <= 60:
        print("PASS — Retrieval under 60 seconds.")
        return 0
    print("FAIL — Over 60 seconds.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
