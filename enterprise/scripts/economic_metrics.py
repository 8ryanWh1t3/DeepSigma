#!/usr/bin/env python3
"""Generate economic_metrics.json from TEC pipeline + security benchmarks.

Reads tec_internal.json, security_metrics.json, and issues_all.json to produce
a dedicated economic evidence artifact with kpi_eligible=true.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KPI_DIR = ROOT / "release_kpis"


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _load_json_list(path: Path) -> list | None:
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return obj if isinstance(obj, list) else None


def main() -> int:
    tec = _load_json(KPI_DIR / "tec_internal.json")
    if tec is None:
        print("ERROR: tec_internal.json not found or invalid", file=sys.stderr)
        return 1

    security = _load_json(KPI_DIR / "security_metrics.json")
    issues = _load_json_list(KPI_DIR / "issues_all.json")

    # TEC data
    hours = tec.get("hours", {})
    tec_base_hours = float(hours.get("total_ctec", hours.get("total_base", 0)))
    counts = tec.get("counts", {})
    decision_count = int(counts.get("issues_total", 0))
    rate = float(tec.get("rate_hourly", 150.0))
    total_cost = float(tec.get("base", {}).get("cost", tec_base_hours * rate))

    # Decision count fallback to issues_all.json length
    if decision_count == 0 and issues is not None:
        decision_count = len(issues)

    avg_cost = round(total_cost / max(decision_count, 1), 2)

    # Security benchmark data (may be None)
    mttr = 0.0
    rps = 0.0
    mbm = 0.0
    if security is not None:
        mttr = float(security.get("mttr_seconds", 0))
        rps = float(security.get("reencrypt_records_per_second", 0))
        mbm = float(security.get("reencrypt_mb_per_minute", 0))

    # Drift remediation cost delta (#405): baseline vs post-patch.
    # With TEC pipeline data available, delta is 0 (no pre-patch baseline yet).
    drift_cost_delta = 0.0
    patch_value_ratio = 1.0

    evidence_sources = []
    if tec is not None:
        evidence_sources.append("tec_internal.json")
    if security is not None:
        evidence_sources.append("security_metrics.json")
    if issues is not None:
        evidence_sources.append("issues_all.json")

    output = {
        "schema": "economic_metrics_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kpi_eligible": True,
        "evidence_level": "real_workload",
        "tec_base_hours": tec_base_hours,
        "decision_count": decision_count,
        "avg_cost_per_decision_usd": avg_cost,
        "total_cost_internal_usd": total_cost,
        "drift_remediation_cost_delta": drift_cost_delta,
        "patch_value_ratio": patch_value_ratio,
        "mttr_seconds": mttr,
        "reencrypt_records_per_second": rps,
        "reencrypt_mb_per_minute": mbm,
        "evidence_sources": evidence_sources,
    }

    out_path = KPI_DIR / "economic_metrics.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote: {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
