#!/usr/bin/env python3
"""Render benchmark throughput trend from benchmark_history.json."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "release_kpis" / "benchmark_history.json"
OUTDIR = ROOT / "release_kpis"


def main() -> int:
    if not HISTORY.exists():
        print("SKIP: no benchmark_history.json yet")
        return 0

    data = json.loads(HISTORY.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    if not entries:
        print("SKIP: no benchmark entries")
        return 0

    indices = list(range(1, len(entries) + 1))
    rps = [e.get("throughput_records_per_second", 0) for e in entries]
    wall = [e.get("wall_clock_seconds", 0) for e in entries]
    labels = [e.get("run_started_at", f"run-{i}")[:10] for i, e in enumerate(entries)]

    fig, ax1 = plt.subplots(figsize=(10, 5))

    color_rps = "#2563eb"
    ax1.set_xlabel("Benchmark Run")
    ax1.set_ylabel("Throughput (records/sec)", color=color_rps)
    ax1.bar(indices, rps, color=color_rps, alpha=0.7, label="Throughput (rps)")
    ax1.tick_params(axis="y", labelcolor=color_rps)
    ax1.set_xticks(indices)
    ax1.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)

    # 80% regression floor line
    if len(rps) >= 2:
        peak_rps = max(rps[:-1])
        ax1.axhline(y=peak_rps * 0.80, color="#dc2626", linestyle="--", alpha=0.6, label="80% floor")

    ax1.legend(loc="upper left")
    ax1.set_title("DISR Re-encrypt Benchmark Trend")

    fig.tight_layout()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTDIR / "benchmark_trend.png", dpi=150)
    fig.savefig(OUTDIR / "benchmark_trend.svg")
    plt.close(fig)

    # Markdown table
    md_lines = [
        "# Benchmark Trend",
        "",
        "| Run | Date | Throughput (rps) | Wall (s) | Evidence |",
        "|-----|------|-----------------|----------|----------|",
    ]
    for i, e in enumerate(entries):
        date = e.get("run_started_at", "—")[:10]
        t = e.get("throughput_records_per_second", 0)
        w = e.get("wall_clock_seconds", 0)
        ev = e.get("evidence_level", "—")
        md_lines.append(f"| {i + 1} | {date} | {t:,.0f} | {w:.3f} | {ev} |")
    md_lines.append("")

    (OUTDIR / "benchmark_trend.md").write_text("\n".join(md_lines), encoding="utf-8")

    print(f"Wrote: {OUTDIR / 'benchmark_trend.png'}")
    print(f"Wrote: {OUTDIR / 'benchmark_trend.svg'}")
    print(f"Wrote: {OUTDIR / 'benchmark_trend.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
