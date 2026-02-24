#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROADMAP_PATH = ROOT / "roadmap" / "roadmap.json"
OUTDIR = ROOT / "release_kpis"

KPI_KEYS = [
    "technical_completeness",
    "automation_depth",
    "authority_modeling",
    "enterprise_readiness",
    "scalability",
    "data_integration",
    "economic_measurability",
    "operational_maturity",
]

# Deterministic intent mapping: roadmap statements -> expected KPI deltas.
DELTA_RULES = {
    "disr": {"security": 1.0, "ops": 0.6, "authority": 0.5},
    "confidence": {"automation": 0.5, "economic": 0.4, "ops": 0.3},
    "eligibility": {"automation": 0.6, "economic": 0.7},
    "determinism": {"automation": 0.6, "technical": 0.4, "ops": 0.5},
    "kpi": {"automation": 0.5, "ops": 0.4},
    "tec": {"economic": 0.9, "ops": 0.3},
    "connector": {"integration": 1.0, "enterprise": 0.8, "scalability": 0.4},
    "provider": {"security": 0.6, "scalability": 0.7, "integration": 0.4},
    "authority": {"authority": 1.0, "ops": 0.4},
    "schema": {"technical": 0.3, "integration": 0.8, "enterprise": 0.4},
}

ALIAS_TO_KPI = {
    "technical": "technical_completeness",
    "automation": "automation_depth",
    "authority": "authority_modeling",
    "enterprise": "enterprise_readiness",
    "scalability": "scalability",
    "integration": "data_integration",
    "economic": "economic_measurability",
    "ops": "operational_maturity",
    "security": "operational_maturity",
}


def empty_delta() -> dict[str, float]:
    return {key: 0.0 for key in KPI_KEYS}


def add_weighted(delta: dict[str, float], alias: str, value: float) -> None:
    kpi = ALIAS_TO_KPI[alias]
    delta[kpi] += value


def score_statements(statements: list[str]) -> dict[str, float]:
    delta = empty_delta()
    for text in statements:
        lowered = text.lower()
        for token, weights in DELTA_RULES.items():
            if token in lowered:
                for alias, value in weights.items():
                    add_weighted(delta, alias, value)
    # cap per release to keep estimates conservative
    for key in delta:
        delta[key] = round(max(0.0, min(2.0, delta[key])), 2)
    return delta


def confidence_for_status(status: str) -> float:
    if status == "active":
        return 0.75
    if status == "dormant":
        return 0.45
    return 0.35


def main() -> int:
    if not ROADMAP_PATH.exists():
        raise SystemExit(f"Missing roadmap file: {ROADMAP_PATH}")

    roadmap = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))
    forecast: dict[str, dict] = {}

    for version, payload in roadmap.items():
        status = str(payload.get("status", "unknown"))
        statements: list[str] = []
        for field in ("scope", "focus"):
            statements.extend(payload.get(field, []))

        delta = score_statements(statements)
        confidence = confidence_for_status(status)
        forecast[version] = {
            "status": status,
            "kpi_delta_expected": delta,
            "confidence": confidence,
            "notes": "Forecast is deterministic from roadmap statements; values are capped per release.",
        }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    out_json = OUTDIR / "roadmap_forecast.json"
    out_json.write_text(json.dumps({"schema": "roadmap_forecast_v1", "forecast": forecast}, indent=2), encoding="utf-8")

    lines = ["# Roadmap KPI Forecast", ""]
    for version, payload in forecast.items():
        lines.append(f"## {version} ({payload['status']})")
        lines.append(f"- Confidence: **{payload['confidence']:.2f}**")
        lines.append("")
        lines.append("| KPI | Expected Delta |")
        lines.append("|---|---:|")
        for key in KPI_KEYS:
            lines.append(f"| {key} | {payload['kpi_delta_expected'][key]:.2f} |")
        lines.append("")
    out_md = OUTDIR / "roadmap_forecast.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
