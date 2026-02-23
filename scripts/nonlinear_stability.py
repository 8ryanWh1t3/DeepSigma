#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
RK = ROOT / "release_kpis"

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


def parse_version(version: str) -> tuple[int, int, int]:
    m = re.match(r"^v(\d+)\.(\d+)\.(\d+)$", version.strip())
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Missing required artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sorted_history() -> list[dict]:
    history = load_json(RK / "history.json")
    entries = history.get("entries", [])
    entries.sort(key=lambda e: parse_version(str(e.get("version", "v0.0.0"))))
    return entries


def kpi_series(entries: list[dict]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {k: [] for k in KPI_KEYS}
    for entry in entries:
        values = entry.get("values", {})
        for key in KPI_KEYS:
            out[key].append(float(values.get(key, 0.0)))
    return out


def deltas(values: list[float]) -> list[float]:
    return [values[i] - values[i - 1] for i in range(1, len(values))]


def accelerations(values: list[float]) -> list[float]:
    first = deltas(values)
    return [first[i] - first[i - 1] for i in range(1, len(first))]


def compute_ssi(entries: list[dict]) -> dict:
    series = kpi_series(entries)

    all_abs_deltas: list[float] = []
    all_abs_accels: list[float] = []
    pos_accel_count = 0
    accel_count = 0

    for key in KPI_KEYS:
        d = deltas(series[key])
        a = accelerations(series[key])
        all_abs_deltas.extend(abs(x) for x in d)
        all_abs_accels.extend(abs(x) for x in a)
        pos_accel_count += sum(1 for x in a if x > 0)
        accel_count += len(a)

    avg_abs_delta = mean(all_abs_deltas) if all_abs_deltas else 0.0
    avg_abs_accel = mean(all_abs_accels) if all_abs_accels else 0.0

    # A) Stability Index math components (0..100)
    # 1) KPI Volatility: high average release-to-release movement lowers stability.
    volatility_norm = clamp(avg_abs_delta / 1.5, 0.0, 1.0)
    kpi_volatility_score = round((1.0 - volatility_norm) * 100.0, 2)

    # 2) Drift Acceleration: second derivative of KPI motion.
    accel_norm = clamp(avg_abs_accel / 1.0, 0.0, 1.0)
    drift_acceleration_score = round((1.0 - accel_norm) * 100.0, 2)

    # 3) Authority perturbation sensitivity: weak authority and volatile authority reduce stability.
    authority = series["authority_modeling"]
    authority_latest = authority[-1] if authority else 0.0
    authority_vol = mean(abs(x) for x in deltas(authority)) if len(authority) > 1 else 0.0
    authority_sensitivity_norm = clamp(max(0.0, (7.0 - authority_latest) / 4.0) + (authority_vol / 1.0) * 0.5, 0.0, 1.0)
    authority_sensitivity_score = round((1.0 - authority_sensitivity_norm) * 100.0, 2)

    # 4) Economic variance sensitivity from TEC spread + economic KPI volatility.
    tec = load_json(RK / "tec_executive.json")
    base_cost = float(tec["base"]["cost"])
    low_cost = float(tec["low"]["cost"])
    high_cost = float(tec["high"]["cost"])
    spread_ratio = (high_cost - low_cost) / base_cost if base_cost else 0.0

    econ = series["economic_measurability"]
    econ_vol = mean(abs(x) for x in deltas(econ)) if len(econ) > 1 else 0.0
    economic_sensitivity_norm = clamp((0.7 * min(1.0, spread_ratio)) + (0.3 * min(1.0, econ_vol / 1.0)), 0.0, 1.0)
    economic_variance_score = round((1.0 - economic_sensitivity_norm) * 100.0, 2)

    # Weighted SSI.
    ssi = round(
        (kpi_volatility_score * 0.35)
        + (drift_acceleration_score * 0.30)
        + (authority_sensitivity_score * 0.20)
        + (economic_variance_score * 0.15),
        2,
    )

    # Confidence band from evidence richness.
    current_version = entries[-1].get("version", "unknown") if entries else "unknown"
    evidence_signals = {
        "history_depth_ge_4": len(entries) >= 4,
        "kpi_merged_present": (RK / f"kpi_{current_version}_merged.json").exists(),
        "tec_present": (RK / "tec_executive.json").exists(),
        "security_metrics_present": (RK / "security_metrics.json").exists(),
        "scalability_metrics_present": (RK / "scalability_metrics.json").exists(),
        "roadmap_forecast_present": (RK / "roadmap_forecast.json").exists(),
    }
    signal_count = sum(1 for v in evidence_signals.values() if v)
    confidence = clamp(0.35 + (signal_count * 0.09), 0.35, 0.90)
    band_half_width = round((1.0 - confidence) * 20.0, 2)  # 0-20 points half width
    ssi_low = round(clamp(ssi - band_half_width, 0.0, 100.0), 2)
    ssi_high = round(clamp(ssi + band_half_width, 0.0, 100.0), 2)

    # B) Instability gating thresholds
    drift_accel_index = round(accel_norm, 4)
    positive_accel_ratio = round((pos_accel_count / accel_count) if accel_count else 0.0, 4)
    severe_divergence = drift_accel_index >= 0.75 and positive_accel_ratio >= 0.45

    if ssi < 55 or severe_divergence:
        gate = "fail"
    elif ssi < 70 or drift_accel_index >= 0.55:
        gate = "warn"
    else:
        gate = "pass"

    return {
        "version": current_version,
        "ssi": ssi,
        "ssi_band": {"low": ssi_low, "high": ssi_high},
        "confidence": round(confidence, 3),
        "components": {
            "kpi_volatility_score": kpi_volatility_score,
            "drift_acceleration_score": drift_acceleration_score,
            "authority_sensitivity_score": authority_sensitivity_score,
            "economic_variance_score": economic_variance_score,
        },
        "raw": {
            "avg_abs_kpi_delta": round(avg_abs_delta, 4),
            "avg_abs_kpi_acceleration": round(avg_abs_accel, 4),
            "drift_acceleration_index": drift_accel_index,
            "positive_acceleration_ratio": positive_accel_ratio,
            "tec_spread_ratio": round(spread_ratio, 4),
        },
        "thresholds": {
            "pass": {
                "ssi_min": 70,
                "drift_acceleration_index_max": 0.55,
            },
            "warn": {
                "ssi_min": 55,
                "drift_acceleration_index_max": 0.75,
            },
            "fail": {
                "ssi_below": 55,
                "or_drift_acceleration_index_gte": 0.75,
            },
        },
        "gate": gate,
        "evidence_signals": evidence_signals,
    }


def compute_forecast(stability: dict) -> dict:
    roadmap_forecast = load_json(RK / "roadmap_forecast.json")
    forecast = roadmap_forecast.get("forecast", {})
    drift_factor = 1.0 - (float(stability["raw"]["drift_acceleration_index"]) * 0.4)

    adjusted: dict[str, dict] = {}
    for version, payload in forecast.items():
        confidence = float(payload.get("confidence", 0.5))
        base_delta = payload.get("kpi_delta_expected", {})
        out_delta: dict[str, float] = {}
        for key in KPI_KEYS:
            raw_value = float(base_delta.get(key, 0.0))
            adjusted_value = raw_value * confidence * drift_factor
            out_delta[key] = round(adjusted_value, 2)

        adjusted[version] = {
            "status": payload.get("status", "unknown"),
            "adjustment_factors": {
                "roadmap_confidence": round(confidence, 3),
                "drift_factor": round(drift_factor, 3),
            },
            "kpi_delta_adjusted": out_delta,
        }

    return {"schema": "stability_adjusted_forecast_v1", "adjusted_forecast": adjusted}


def simulate_instability(entries: list[dict], stability: dict) -> dict:
    latest = entries[-1]
    latest_values = {k: float(latest.get("values", {}).get(k, 0.0)) for k in KPI_KEYS}

    scenarios = {
        "mild": {
            "description": "single-cycle turbulence with constrained spread",
            "shock": {
                "automation_depth": -0.6,
                "scalability": -0.4,
                "economic_measurability": -0.5,
                "authority_modeling": -0.3,
            },
        },
        "moderate": {
            "description": "broad system stress and governance lag",
            "shock": {
                "automation_depth": -1.2,
                "scalability": -0.9,
                "economic_measurability": -1.0,
                "authority_modeling": -0.8,
                "data_integration": -0.6,
            },
        },
        "severe": {
            "description": "compound drift with authority + economic instability",
            "shock": {
                "automation_depth": -2.0,
                "scalability": -1.8,
                "economic_measurability": -1.7,
                "authority_modeling": -1.4,
                "data_integration": -1.1,
                "operational_maturity": -0.8,
            },
        },
    }

    results: dict[str, dict] = {}
    base_ssi = float(stability["ssi"])
    base_accel = float(stability["raw"]["drift_acceleration_index"])

    for name, config in scenarios.items():
        perturbed = dict(latest_values)
        for key, delta in config["shock"].items():
            perturbed[key] = clamp(perturbed.get(key, 0.0) + float(delta), 0.0, 10.0)

        shock_magnitude = mean(abs(float(x)) for x in config["shock"].values())
        simulated_accel = clamp(base_accel + (shock_magnitude / 3.0), 0.0, 1.0)

        # Approximate SSI degradation from shock and acceleration.
        ssi_drop = (shock_magnitude * 10.0) + (simulated_accel * 12.0)
        ssi_projected = round(clamp(base_ssi - ssi_drop, 0.0, 100.0), 2)

        if ssi_projected < 55 or simulated_accel >= 0.75:
            gate = "fail"
        elif ssi_projected < 70 or simulated_accel >= 0.55:
            gate = "warn"
        else:
            gate = "pass"

        results[name] = {
            "description": config["description"],
            "shock": {k: round(v, 2) for k, v in config["shock"].items()},
            "projected_kpis": {k: round(v, 2) for k, v in perturbed.items()},
            "projected_ssi": ssi_projected,
            "projected_drift_acceleration_index": round(simulated_accel, 4),
            "gate": gate,
        }

    return {"schema": "stability_simulation_v1", "version": latest.get("version", "unknown"), "scenarios": results}


def write_markdown(stability: dict, forecast: dict, simulation: dict) -> None:
    version = stability["version"]
    lines = [
        f"# Nonlinear Stability Report — {version}",
        "",
        "## A) System Stability Index (SSI) Math",
        "",
        "`SSI = 0.35*Volatility + 0.30*DriftAccel + 0.20*Authority + 0.15*Economic`",
        "",
        "Where each component is normalized to `0..100` (higher is more stable):",
        "- Volatility score: `100 * (1 - clamp(avg_abs_kpi_delta/1.5, 0, 1))`",
        "- Drift acceleration score: `100 * (1 - clamp(avg_abs_kpi_acceleration/1.0, 0, 1))`",
        "- Authority sensitivity score: authority strength and authority volatility penalty",
        "- Economic variance score: TEC spread ratio and economic KPI variance penalty",
        "",
        f"- SSI: **{stability['ssi']}**",
        f"- Confidence: **{stability['confidence']}**",
        f"- Band: **[{stability['ssi_band']['low']}, {stability['ssi_band']['high']}]**",
        "",
        "## B) Instability Gating Thresholds",
        "",
        "- `PASS`: SSI >= 70 and drift_acceleration_index < 0.55",
        "- `WARN`: 55 <= SSI < 70 or 0.55 <= drift_acceleration_index < 0.75",
        "- `FAIL`: SSI < 55 or drift_acceleration_index >= 0.75",
        "",
        f"- Current drift_acceleration_index: **{stability['raw']['drift_acceleration_index']}**",
        f"- Current gate: **{stability['gate'].upper()}**",
        "",
        "## C) Forecasted Radar Movement (Stability-Adjusted)",
        "",
    ]

    for version_key, payload in forecast["adjusted_forecast"].items():
        lines.append(f"### {version_key} ({payload['status']})")
        lines.append(
            f"- Factors: roadmap_confidence={payload['adjustment_factors']['roadmap_confidence']}, drift_factor={payload['adjustment_factors']['drift_factor']}"
        )
        lines.append("| KPI | Adjusted Delta |")
        lines.append("|---|---:|")
        for key in KPI_KEYS:
            lines.append(f"| {key} | {payload['kpi_delta_adjusted'][key]:.2f} |")
        lines.append("")

    lines.extend([
        "## D) v2.0.6 Instability Simulation",
        "",
        "Scenario stress-tests on the current release baseline:",
        "",
    ])

    for name, payload in simulation["scenarios"].items():
        lines.append(f"### {name.title()}")
        lines.append(f"- Description: {payload['description']}")
        lines.append(f"- Projected SSI: **{payload['projected_ssi']}**")
        lines.append(f"- Projected drift_acceleration_index: **{payload['projected_drift_acceleration_index']}**")
        lines.append(f"- Gate: **{payload['gate'].upper()}**")
        lines.append("")

    (RK / "nonlinear_stability_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    entries = sorted_history()
    if len(entries) < 3:
        raise SystemExit("Need at least 3 release entries in history.json for nonlinear stability analysis")

    stability = compute_ssi(entries)
    forecast = compute_forecast(stability)
    simulation = simulate_instability(entries, stability)

    stability_path = RK / f"stability_{stability['version']}.json"
    simulation_path = RK / f"stability_simulation_{stability['version']}.json"

    stability_path.write_text(json.dumps(stability, indent=2) + "\n", encoding="utf-8")
    simulation_path.write_text(json.dumps(simulation, indent=2) + "\n", encoding="utf-8")
    (RK / "stability_adjusted_forecast.json").write_text(json.dumps(forecast, indent=2) + "\n", encoding="utf-8")

    write_markdown(stability, forecast, simulation)

    print(f"Wrote: {stability_path}")
    print(f"Wrote: {simulation_path}")
    print(f"Wrote: {RK / 'stability_adjusted_forecast.json'}")
    print(f"Wrote: {RK / 'nonlinear_stability_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
