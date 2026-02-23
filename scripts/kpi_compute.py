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


def score_economic_measurability() -> float:
    metrics = parse_security_metrics()
    if not metrics:
        return 0.0

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
    out = {
        "technical_completeness": round(score_technical_completeness(), 2),
        "automation_depth": round(score_automation_depth(), 2),
        "enterprise_readiness": round(score_enterprise_readiness(), 2),
        "data_integration": round(score_data_integration(), 2),
        "economic_measurability": round(score_economic_measurability(), 2),
        "operational_maturity": round(score_operational_maturity(), 2),
        "_telemetry": {
            "test_files": count_files("tests/test_*.py") + count_files("tests/**/test_*.py"),
            "workflows": count_files(".github/workflows/*.yml") + count_files(".github/workflows/*.yaml"),
            "docs_md": len(list(docs_root.glob("**/*.md"))) if docs_root.exists() else 0,
            "security_metrics_present": parse_security_metrics() is not None,
        },
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
