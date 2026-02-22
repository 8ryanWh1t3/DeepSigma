#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_history(path: Path) -> dict:
    if not path.exists():
        return {"schema": "repo_kpi_history_v1", "entries": []}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_spec(spec_path: Path) -> list[dict]:
    lines = spec_path.read_text(encoding="utf-8").splitlines()
    kpis: list[dict] = []
    current_key: str | None = None
    meta: dict = {}
    for line in lines:
        s = line.strip()
        if s.startswith("- key:"):
            current_key = s.split(":", 1)[1].strip()
            meta = {"key": current_key}
            continue
        if not current_key:
            continue
        if s.startswith("label:"):
            meta["label"] = s.split(":", 1)[1].strip().strip('"').strip("'")
        elif s.startswith("source:"):
            meta["source"] = s.split(":", 1)[1].strip()
        elif s.startswith("floor:"):
            meta["floor"] = float(s.split(":", 1)[1].strip())
        elif s.startswith("max_drop:"):
            meta["max_drop"] = float(s.split(":", 1)[1].strip())

        if (
            "label" in meta
            and "source" in meta
            and "floor" in meta
            and "max_drop" in meta
        ):
            kpis.append(meta)
            current_key = None
            meta = {}
    return kpis


def main() -> int:
    outdir = ROOT / "release_kpis"
    history_path = outdir / "history.json"
    version = (outdir / "VERSION.txt").read_text(encoding="utf-8").strip()
    merged_path = outdir / f"kpi_{version}_merged.json"
    if not merged_path.exists():
        raise SystemExit(f"Missing merged KPI file: {merged_path}. Run make kpi first.")

    current = json.loads(merged_path.read_text(encoding="utf-8"))
    current_values = current["values"]

    spec_path = ROOT / "governance" / "kpi_spec.yaml"
    kpis = parse_spec(spec_path)
    if len(kpis) != 8:
        raise SystemExit(
            f"Spec parse error: expected 8 KPI definitions with label/floor/max_drop/source, got {len(kpis)}"
        )

    history = load_history(history_path)
    entries = history.get("entries", [])
    previous = entries[-1] if entries else None
    previous_values = previous.get("values", {}) if previous else {}

    failures: list[str] = []
    warnings: list[str] = []

    for kpi in kpis:
        key = kpi["key"]
        floor = float(kpi["floor"])
        value = float(current_values.get(key, 0))
        if value < floor:
            failures.append(f"{kpi['label']} below floor: {value:.1f} < {floor:.1f}")

    if previous and previous.get("version") != version:
        for kpi in kpis:
            key = kpi["key"]
            max_drop = float(kpi["max_drop"])
            if key in previous_values:
                prev_value = float(previous_values[key])
                cur_value = float(current_values.get(key, 0))
                drop = prev_value - cur_value
                if drop > max_drop:
                    failures.append(
                        f"{kpi['label']} regressed too much: {prev_value:.1f} -> {cur_value:.1f} (drop {drop:.1f} > {max_drop:.1f})"
                    )
                elif drop > 0:
                    warnings.append(
                        f"{kpi['label']} regressed: {prev_value:.1f} -> {cur_value:.1f}"
                    )

    if not previous:
        entries.append({"version": version, "values": current_values})
    elif previous.get("version") != version:
        entries.append({"version": version, "values": current_values})
    else:
        entries[-1] = {"version": version, "values": current_values}
    history["entries"] = entries
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")

    report_path = outdir / "KPI_GATE_REPORT.md"
    lines = [f"# KPI Gate Report - {version}", ""]
    if previous and previous.get("version") != version:
        lines.append(f"Previous: {previous.get('version')}")
    lines.append("")
    if failures:
        lines.append("## FAILURES")
        lines.extend(f"- {item}" for item in failures)
        lines.append("")
    if warnings:
        lines.append("## WARNINGS")
        lines.extend(f"- {item}" for item in warnings)
        lines.append("")
    if not failures and not warnings:
        lines.append("## PASS")
        lines.append("- No floors violated")
        lines.append("- No regressions beyond max_drop")
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {report_path}")

    if failures:
        raise SystemExit("KPI gate FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
