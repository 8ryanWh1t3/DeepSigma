#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def clamp(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, value))


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def version_from_file(outdir: Path) -> str:
    version_file = outdir / "VERSION.txt"
    if not version_file.exists():
        return "v0.0.0"
    return version_file.read_text(encoding="utf-8").strip()


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def score_from_inputs(
    issue_deltas: dict[str, Any] | None,
    merged: dict[str, Any] | None,
    history: dict[str, Any] | None,
) -> tuple[float, list[dict[str, Any]], dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    base = 5.0

    diagnostics: dict[str, Any] = {
        "closed_since_total": 0,
        "open_total": 0,
        "credit_delta_total": 0.0,
        "debt_delta_total": 0.0,
        "open_p0_caps": 0,
        "kpi_average": None,
        "kpi_average_delta": None,
    }

    if issue_deltas:
        kpis = issue_deltas.get("kpis", {})
        if isinstance(kpis, dict):
            closed = 0
            open_count = 0
            credit = 0.0
            debt = 0.0
            p0_caps = 0
            for details in kpis.values():
                if not isinstance(details, dict):
                    continue
                closed += int(details.get("closed_since_count", 0))
                open_count += int(details.get("open_count", 0))
                credit += float(details.get("credit_delta", 0.0))
                debt += float(details.get("debt_delta", 0.0))
                if details.get("cap_if_open_p0") is not None:
                    p0_caps += 1

            diagnostics["closed_since_total"] = closed
            diagnostics["open_total"] = open_count
            diagnostics["credit_delta_total"] = round(credit, 2)
            diagnostics["debt_delta_total"] = round(debt, 2)
            diagnostics["open_p0_caps"] = p0_caps

            base += min(2.0, closed / 25.0)
            base -= min(2.5, debt / 10.0)
            base -= min(1.0, open_count / 200.0)

            if debt > credit:
                signals.append(
                    {
                        "id": "debt_exceeds_credit",
                        "severity": "high",
                        "message": "Issue debt delta exceeds closure credit delta.",
                        "value": {"credit_delta": round(credit, 2), "debt_delta": round(debt, 2)},
                    }
                )
            if p0_caps > 0:
                signals.append(
                    {
                        "id": "open_p0_caps",
                        "severity": "high",
                        "message": "One or more KPI tracks report open P0 caps.",
                        "value": {"kpi_tracks": p0_caps},
                    }
                )

    if merged:
        values = merged.get("values", {})
        if isinstance(values, dict):
            numeric_values = [float(v) for v in values.values() if isinstance(v, (int, float))]
            kpi_avg = average(numeric_values)
            diagnostics["kpi_average"] = round(kpi_avg, 2)
            base += clamp((kpi_avg - 5.0) / 2.5, -2.0, 2.0)
            if kpi_avg < 6.0:
                signals.append(
                    {
                        "id": "kpi_mean_low",
                        "severity": "medium",
                        "message": "Merged KPI mean is below target threshold (6.0).",
                        "value": {"kpi_average": round(kpi_avg, 2)},
                    }
                )

    if history:
        entries = history.get("entries", [])
        if isinstance(entries, list) and len(entries) >= 2:
            latest = entries[-1].get("values", {})
            previous = entries[-2].get("values", {})
            if isinstance(latest, dict) and isinstance(previous, dict):
                deltas = []
                for key, current in latest.items():
                    if key in previous and isinstance(current, (int, float)) and isinstance(
                        previous[key], (int, float)
                    ):
                        deltas.append(float(current) - float(previous[key]))
                avg_delta = average(deltas)
                diagnostics["kpi_average_delta"] = round(avg_delta, 3)
                base += clamp(avg_delta, -1.0, 1.0)
                if avg_delta < 0:
                    signals.append(
                        {
                            "id": "kpi_trend_down",
                            "severity": "medium",
                            "message": "KPI average trend is negative versus previous release.",
                            "value": {"avg_delta": round(avg_delta, 3)},
                        }
                    )

    return round(clamp(base), 2), signals, diagnostics


def main() -> int:
    outdir = ROOT / "release_kpis"
    outdir.mkdir(parents=True, exist_ok=True)

    version = version_from_file(outdir)
    issue_deltas = load_json(outdir / "issue_deltas.json")
    merged = load_json(outdir / f"kpi_{version}_merged.json")
    history = load_json(outdir / "history.json")

    score, signals, diagnostics = score_from_inputs(issue_deltas, merged, history)
    payload = {
        "schema": "pulse_insights_v1",
        "generated_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "version": version,
        "source": "pulse",
        "insights_score": score,
        "signal_count": len(signals),
        "signals": signals,
        "inputs": {
            "issue_deltas_present": issue_deltas is not None,
            "kpi_merged_present": merged is not None,
            "history_present": history is not None,
        },
        "diagnostics": diagnostics,
    }

    out_path = outdir / "insights_metrics.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
