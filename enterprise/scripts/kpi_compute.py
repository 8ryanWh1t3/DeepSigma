#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def count_files(glob_pat: str) -> int:
    return len(list(ROOT.glob(glob_pat)))


def file_exists(path: str) -> bool:
    return (ROOT / path).exists()


def parse_ci_score() -> int | None:
    report = ROOT / "pilot" / "reports" / "ci_report.json"
    if not report.exists():
        return None
    try:
        obj = json.loads(report.read_text(encoding="utf-8"))
    except Exception:
        return None
    for key in ("ci_score", "score", "coherence_index"):
        value = obj.get(key)
        if isinstance(value, (int, float)):
            return int(value)
    return None


def clamp(value: float, lo: float = 0, hi: float = 10) -> float:
    return max(lo, min(hi, value))


def parse_security_metrics() -> dict | None:
    path = ROOT / "release_kpis" / "security_metrics.json"
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def parse_scalability_metrics() -> dict | None:
    path = ROOT / "release_kpis" / "scalability_metrics.json"
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def parse_insights_metrics() -> dict | None:
    path = ROOT / "release_kpis" / "insights_metrics.json"
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def summarize_insights(metrics: dict | None) -> dict:
    if not metrics:
        return {
            "present": False,
            "source": "release_kpis/insights_metrics.json",
            "score": None,
            "signals": 0,
        }

    score = None
    for key in ("insights_score", "score", "coverage_score"):
        value = metrics.get(key)
        if isinstance(value, (int, float)):
            score = round(clamp(float(value)), 2)
            break

    signals = metrics.get("signals")
    if isinstance(signals, list):
        signal_count = len(signals)
    elif isinstance(signals, dict):
        signal_count = len(signals.keys())
    elif isinstance(metrics.get("signal_count"), int):
        signal_count = int(metrics["signal_count"])
    else:
        signal_count = 0

    return {
        "present": True,
        "source": "release_kpis/insights_metrics.json",
        "score": score,
        "signals": signal_count,
    }


def is_kpi_eligible(metrics: dict) -> bool:
    return bool(metrics.get("kpi_eligible")) and metrics.get("evidence_level") == "real_workload"


def score_economic_measurability(metrics: dict) -> float:
    score = 3.0  # metrics present and parseable
    mttr = float(metrics.get("mttr_seconds", 0))
    rps = float(metrics.get("reencrypt_records_per_second", 0))
    mbm = float(metrics.get("reencrypt_mb_per_minute", 0))

    if mttr <= 300:
        score += 3
    elif mttr <= 600:
        score += 2
    elif mttr <= 1200:
        score += 1

    if rps >= 1:
        score += 2
    elif rps >= 0.1:
        score += 1

    if mbm >= 0.01:
        score += 2
    elif mbm >= 0.001:
        score += 1

    if not is_kpi_eligible(metrics):
        return clamp(min(score, 4.0))
    return clamp(score)


def score_scalability(metrics: dict) -> float:
    raw = metrics.get("scalability_score")
    if isinstance(raw, (int, float)):
        score = clamp(float(raw))
        if not is_kpi_eligible(metrics):
            return clamp(min(score, 4.0))
        return score
    throughput = float(metrics.get("throughput_records_per_second", 0))
    mbm = float(metrics.get("throughput_mb_per_minute", 0))
    score = 2.0
    if throughput >= 5000:
        score += 5
    elif throughput >= 1000:
        score += 4
    elif throughput >= 100:
        score += 2
    if mbm >= 500:
        score += 3
    elif mbm >= 100:
        score += 2
    elif mbm >= 10:
        score += 1
    if not is_kpi_eligible(metrics):
        return clamp(min(score, 4.0))
    return clamp(score)


def score_enterprise_readiness() -> float:
    points = 0
    points += 1 if file_exists("docs/docs/pilot/BRANCH_PROTECTION.md") else 0
    points += 1 if file_exists("docs/docs/pilot/PILOT_CONTRACT_ONEPAGER.md") else 0
    points += 1 if file_exists(".github/workflows/kpi.yml") else 0
    points += 1 if file_exists(".github/workflows/kpi_gate.yml") else 0
    points += 1 if file_exists("Makefile") else 0
    return clamp(points * 2)


def score_data_integration() -> float:
    points = 0
    for path in (
        "connectors",
        "scripts/connectors",
        "docs/docs/connectors",
        "docs/docs/integrations",
        "src/deepsigma/connectors",
        "src/services",
        "src/demos",
        "docs/examples",
    ):
        if (ROOT / path).exists():
            points += 1
    has_schemas = (ROOT / "schemas").exists()
    points += 1 if has_schemas else 0
    if has_schemas and (ROOT / "src").exists():
        points = max(points, 2)
    return clamp(points * 2)


def score_technical_completeness() -> float:
    points = 0
    points += 2 if (ROOT / "src").exists() else 0
    points += 2 if file_exists("scripts/compute_ci.py") else 0
    points += 2 if (ROOT / "tests").exists() else 0
    points += 2 if (ROOT / ".github" / "workflows").exists() else 0
    points += 2 if file_exists("pyproject.toml") or file_exists("setup.py") else 0
    return clamp(points)


def score_automation_depth() -> float:
    workflows = count_files(".github/workflows/*.yml") + count_files(".github/workflows/*.yaml")
    scripts = count_files("scripts/*.py")
    make = 2 if file_exists("Makefile") else 0
    value = (workflows * 1.2) + (scripts / 30 * 4) + make
    return clamp(value)


def score_operational_maturity() -> float:
    points = 0
    points += 2 if file_exists("scripts/pilot_in_a_box.py") else 0
    points += 1 if file_exists("scripts/why_60s_challenge.py") else 0
    points += 2 if (ROOT / "pilot" / "reports").exists() else 0
    points += 2 if file_exists(".github/workflows/coherence_ci.yml") else 0
    points += 1 if parse_ci_score() is not None else 0
    return clamp(points * 1.25)


def main() -> int:
    docs_root = ROOT / "docs" / "docs"
    metrics = parse_security_metrics()
    scalability_metrics = parse_scalability_metrics()
    insights_metrics = parse_insights_metrics()
    out = {
        "technical_completeness": round(score_technical_completeness(), 2),
        "automation_depth": round(score_automation_depth(), 2),
        "enterprise_readiness": round(score_enterprise_readiness(), 2),
        "data_integration": round(score_data_integration(), 2),
        "operational_maturity": round(score_operational_maturity(), 2),
        "_telemetry": {
            "test_files": count_files("tests/test_*.py") + count_files("tests/**/test_*.py"),
            "workflows": count_files(".github/workflows/*.yml") + count_files(".github/workflows/*.yaml"),
            "docs_md": len(list(docs_root.glob("**/*.md"))) if docs_root.exists() else 0,
            "security_metrics_present": metrics is not None,
            "scalability_metrics_present": scalability_metrics is not None,
            "insights_metrics_present": insights_metrics is not None,
            "insights": summarize_insights(insights_metrics),
        },
    }
    if metrics is not None:
        out["economic_measurability"] = round(score_economic_measurability(metrics), 2)
    if scalability_metrics is not None:
        out["scalability"] = round(score_scalability(scalability_metrics), 2)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
