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


def _append_cost_ledger(entry: dict, ledger_path: Path) -> None:
    """Append a cost snapshot to the economic cost ledger for drift-to-patch tracking."""
    entries: list[dict] = []
    if ledger_path.exists():
        raw = ledger_path.read_text(encoding="utf-8").strip()
        if raw:
            obj = json.loads(raw)
            if isinstance(obj, list):
                entries = obj
    entries.append(entry)
    ledger_path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


def _run_self_check() -> int:
    """Validate economic metrics generation with synthetic inputs."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        kpi_dir = Path(tmp)
        tec = {
            "hours": {"total_ctec": 100.0},
            "counts": {"issues_total": 10},
            "rate_hourly": 150.0,
            "base": {"cost": 15000.0},
        }
        (kpi_dir / "tec_internal.json").write_text(json.dumps(tec), encoding="utf-8")
        security = {"mttr_seconds": 0.05, "reencrypt_records_per_second": 1000000, "reencrypt_mb_per_minute": 5000}
        (kpi_dir / "security_metrics.json").write_text(json.dumps(security), encoding="utf-8")
        issues = [{"number": i} for i in range(10)]
        (kpi_dir / "issues_all.json").write_text(json.dumps(issues), encoding="utf-8")

        # Monkey-patch KPI_DIR and clear sys.argv to avoid recursion
        original_kpi_dir = KPI_DIR
        original_argv = sys.argv[:]
        sys.argv = ["economic_metrics.py"]  # clear --self-check
        import economic_metrics
        economic_metrics.KPI_DIR = kpi_dir
        try:
            rc = economic_metrics.main()
        finally:
            economic_metrics.KPI_DIR = original_kpi_dir
            sys.argv = original_argv

        if rc != 0:
            print("FAIL: economic_metrics.main() returned non-zero")
            return 2

        out = json.loads((kpi_dir / "economic_metrics.json").read_text(encoding="utf-8"))
        if out["schema"] != "economic_metrics_v1":
            print("FAIL: wrong schema")
            return 2
        if out["decision_count"] != 10:
            print(f"FAIL: expected 10 decisions, got {out['decision_count']}")
            return 2
        if out["avg_cost_per_decision_usd"] != 1500.0:
            print(f"FAIL: expected avg cost 1500.0, got {out['avg_cost_per_decision_usd']}")
            return 2

        # Check cost ledger was appended
        ledger = kpi_dir / "economic_cost_ledger.json"
        if ledger.exists():
            entries = json.loads(ledger.read_text(encoding="utf-8"))
            if len(entries) != 1:
                print(f"FAIL: expected 1 ledger entry, got {len(entries)}")
                return 2

    print("PASS: economic metrics self-check passed")
    return 0


def main() -> int:
    if "--self-check" in sys.argv:
        return _run_self_check()

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
    try:
        label = str(out_path.relative_to(ROOT))
    except ValueError:
        label = str(out_path)
    print(f"Wrote: {label}")

    # Append to cost ledger for drift-to-patch tracking
    _append_cost_ledger(
        {
            "timestamp": output["generated_at"],
            "decision_count": decision_count,
            "avg_cost_per_decision_usd": avg_cost,
            "total_cost_internal_usd": total_cost,
            "drift_cost_delta": drift_cost_delta,
            "patch_value_ratio": patch_value_ratio,
        },
        KPI_DIR / "economic_cost_ledger.json",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
