#!/usr/bin/env python3
"""Scalability regression gate — fails CI if benchmark regresses."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "enterprise" / "release_kpis" / "benchmark_history.json"
REPORT = ROOT / "enterprise" / "release_kpis" / "SCALABILITY_GATE_REPORT.md"

SCORE_REGRESSION_LIMIT = 1.0  # max allowed score drop
THROUGHPUT_FLOOR_RATIO = 0.80  # must retain >=80% of previous throughput


def load_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    data = json.loads(HISTORY.read_text(encoding="utf-8"))
    entries = data.get("entries")
    return entries if isinstance(entries, list) else []


def main() -> int:
    entries = load_history()
    lines: list[str] = ["# Scalability Regression Gate Report\n"]
    failures: list[str] = []

    if len(entries) < 2:
        lines.append("**SKIP** — fewer than 2 benchmark entries; no baseline for comparison.\n")
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print("SKIP: not enough history for regression check")
        return 0

    prev, latest = entries[-2], entries[-1]

    prev_score = prev.get("throughput_records_per_second", 0)
    latest_score = latest.get("throughput_records_per_second", 0)
    prev_wall = prev.get("wall_clock_seconds", 0)
    latest_wall = latest.get("wall_clock_seconds", 0)

    # Check evidence level
    evidence = latest.get("evidence_level", "unknown")
    if evidence not in ("real_workload", "ci_benchmark"):
        failures.append(f"Evidence level is `{evidence}`, expected `real_workload` or `ci_benchmark`.")

    # Check throughput regression
    if prev_score > 0:
        ratio = latest_score / prev_score
        if ratio < THROUGHPUT_FLOOR_RATIO:
            failures.append(
                f"Throughput regressed: {latest_score:.0f} rps vs previous {prev_score:.0f} rps "
                f"({ratio:.1%}, floor is {THROUGHPUT_FLOOR_RATIO:.0%})."
            )

    lines.append(f"| Metric | Previous | Latest | Status |")
    lines.append(f"|--------|----------|--------|--------|")
    lines.append(f"| Throughput (rps) | {prev_score:,.0f} | {latest_score:,.0f} | {'PASS' if not failures else 'FAIL'} |")
    lines.append(f"| Wall clock (s) | {prev_wall:.3f} | {latest_wall:.3f} | — |")
    lines.append(f"| Evidence level | — | {evidence} | {'PASS' if evidence in ('real_workload', 'ci_benchmark') else 'FAIL'} |")
    lines.append("")

    if failures:
        lines.append("## Failures\n")
        for f in failures:
            lines.append(f"- {f}")
        lines.append("")

    status = "FAIL" if failures else "PASS"
    lines.append(f"**Gate: {status}**\n")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Scalability gate: {status}")
    if failures:
        for f in failures:
            print(f"  - {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
