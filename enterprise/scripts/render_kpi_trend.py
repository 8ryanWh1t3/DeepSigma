#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    history_path = ROOT / "release_kpis" / "history.json"
    if not history_path.exists():
        raise SystemExit("Missing release_kpis/history.json")

    history = json.loads(history_path.read_text(encoding="utf-8"))
    entries: List[Dict] = history.get("entries", [])
    if not entries:
        raise SystemExit("No entries in history.json")

    spec_lines = (ROOT / "governance" / "kpi_spec.yaml").read_text(
        encoding="utf-8"
    ).splitlines()
    order: List[str] = []
    cur_key = None
    for line in spec_lines:
        stripped = line.strip()
        if stripped.startswith("- key:"):
            cur_key = stripped.split(":", 1)[1].strip()
        elif cur_key and stripped.startswith("label:"):
            order.append(cur_key)
            cur_key = None
    if len(order) != 8:
        raise SystemExit(f"Expected 8 KPI keys in spec; got {len(order)}")

    versions = [entry["version"] for entry in entries]
    averages: List[float] = []
    series = {key: [] for key in order}
    for entry in entries:
        values = entry.get("values", {})
        nums: List[float] = []
        for key in order:
            value = float(values.get(key, 0))
            series[key].append(value)
            nums.append(value)
        averages.append(sum(nums) / len(nums))

    fig = plt.figure(figsize=(10, 4), dpi=140)
    ax = plt.gca()
    ax.plot(versions, averages, linewidth=2, label="avg")
    for key in order:
        ax.plot(versions, series[key], linewidth=1, alpha=0.65, label=key)

    ax.set_title("Repo KPI Trend (history.json)")
    ax.set_xlabel("Release")
    ax.set_ylabel("Score (0-10)")
    ax.set_ylim(0, 10)
    ax.tick_params(axis="x", rotation=30)
    ax.grid(True, alpha=0.25)

    outdir = ROOT / "release_kpis"
    out_png = outdir / "kpi_trend.png"
    out_svg = outdir / "kpi_trend.svg"
    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)

    print(f"Wrote: {out_png}")
    print(f"Wrote: {out_svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
