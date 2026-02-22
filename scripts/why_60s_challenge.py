#!/usr/bin/env python3
from __future__ import annotations

import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_ = ROOT / "pilot"

QUESTIONS = [
    ("Find the most recent DLR ID", "pilot/decisions"),
    ("Find any Assumption ID (A-*)", "pilot/assumptions"),
    ("Find any Drift ID (DRIFT-*)", "pilot/drift"),
    ("Find any Patch ID (PATCH-*)", "pilot/patches"),
]


def main() -> int:
    print("WHY-60s Challenge — You have 60 seconds total.")
    start = time.time()

    for i, (question, rel) in enumerate(QUESTIONS, 1):
        elapsed = time.time() - start
        if elapsed > 60:
            print("TIME — FAIL")
            return 2
        print(f"[{i}/4] {question} (look in {rel})")
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
