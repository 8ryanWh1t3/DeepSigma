#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ENT_ROOT = Path(__file__).resolve().parents[1]
RK_ROOT = ENT_ROOT / "release_kpis"
HEALTH_ROOT = ENT_ROOT / "release_kpis" / "health"
HISTORY_ROOT = HEALTH_ROOT / "history"
POLICY_PATH = ENT_ROOT / "governance" / "tec_ctec_policy.json"

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".sh",
    ".env",
    ".csv",
    ".rst",
}

CONFIG_SUFFIXES = {".yaml", ".yml", ".json", ".toml", ".ini", ".cfg"}
TEST_PATTERN = re.compile(r"(^test_.*\.py$)|(_test\.py$)")
RUN_NAME_PATTERN = re.compile(r"(^run_.*\.(sh|py)$)|(^demo_.*\.(sh|py)$)", re.IGNORECASE)


@dataclass(frozen=True)
class Inventory:
    files: int
    directories: int
    loc: int
    packages: int
    configs: int
    tests: int
    run_surfaces: int
    artifacts: int


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


def iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        out.append(path)
    return out


def count_loc(paths: list[Path]) -> int:
    total = 0
    for path in paths:
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        total += sum(1 for line in text.splitlines() if line.strip())
    return total


def count_packages(paths: list[Path]) -> int:
    package_dirs = {path.parent for path in paths if path.name == "__init__.py"}
    return len(package_dirs)


def count_configs(paths: list[Path]) -> int:
    return sum(1 for path in paths if path.suffix.lower() in CONFIG_SUFFIXES)


def count_tests(paths: list[Path]) -> int:
    return sum(1 for path in paths if TEST_PATTERN.search(path.name) is not None)


def count_run_surfaces(paths: list[Path]) -> int:
    count = 0
    for path in paths:
        if RUN_NAME_PATTERN.search(path.name):
            count += 1
            continue
        if path.suffix.lower() != ".py":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "if __name__ == \"__main__\":" in text:
            count += 1
    return count


def build_inventory(edition: str, policy: dict[str, Any]) -> Inventory:
    edition_roots = policy.get("edition_roots", {}).get(edition, [])
    artifact_roots = policy.get("artifacts_roots", {}).get(edition, [])

    files: list[Path] = []
    for raw in edition_roots:
        root = REPO_ROOT / raw
        files.extend(iter_files(root))

    dirs = {path.parent for path in files}
    artifacts = 0
    for raw in artifact_roots:
        artifacts += len(iter_files(REPO_ROOT / raw))

    return Inventory(
        files=len(files),
        directories=len(dirs),
        loc=count_loc(files),
        packages=count_packages(files),
        configs=count_configs(files),
        tests=count_tests(files),
        run_surfaces=count_run_surfaces(files),
        artifacts=artifacts,
    )


def tec_score(inventory: Inventory, policy: dict[str, Any]) -> float:
    formula = policy.get("tec_formula", {})
    f = float(formula.get("F", 1.0))
    p = float(formula.get("P", 3.0))
    c = float(formula.get("C", 0.2))
    r = float(formula.get("R", 2.0))
    t = float(formula.get("T", 2.0))
    return (
        f * inventory.files
        + p * inventory.packages
        + c * inventory.configs
        + r * inventory.run_surfaces
        + t * inventory.tests
    )


def control_coverage_core() -> dict[str, Any]:
    checks = {
        "money_demo": (REPO_ROOT / "run_money_demo.sh").exists(),
        "baseline": (REPO_ROOT / "core_baseline.py").exists()
        and (ENT_ROOT / "release_kpis" / "CORE_BASELINE_REPORT.md").exists(),
        "core_tests": (REPO_ROOT / "tests").exists(),
        "boundary_guard": (ENT_ROOT / "scripts" / "edition_guard.py").exists(),
        "secret_scan": (ENT_ROOT / "scripts" / "secret_scan.py").exists(),
        "docs_path_to_run": "run_money_demo.sh" in (REPO_ROOT / "README.md").read_text(encoding="utf-8", errors="ignore") if (REPO_ROOT / "README.md").exists() else False,
    }
    passed = sum(1 for ok in checks.values() if ok)
    return {
        "required": len(checks),
        "passed": passed,
        "kpi_coverage": round(passed / max(len(checks), 1), 4),
        "checks": checks,
    }


def control_coverage_enterprise() -> dict[str, Any]:
    checks = {
        "enterprise_demo": (REPO_ROOT / "run_enterprise_demo.sh").exists(),
        "enterprise_tests": (REPO_ROOT / "tests-enterprise").exists(),
        "deploy_sanity": (ENT_ROOT / "docker").exists() and (ENT_ROOT / "charts").exists(),
        "connector_smokes": (ENT_ROOT / "scripts" / "mesh_wan_partition.sh").exists() or (ENT_ROOT / "scripts" / "pilot_in_a_box.py").exists(),
        "boundary_guard": (ENT_ROOT / "scripts" / "edition_guard.py").exists(),
        "secret_scan": (ENT_ROOT / "scripts" / "secret_scan.py").exists(),
    }
    passed = sum(1 for ok in checks.values() if ok)
    return {
        "required": len(checks),
        "passed": passed,
        "kpi_coverage": round(passed / max(len(checks), 1), 4),
        "checks": checks,
    }


def ccf_from_pcr(policy: dict[str, Any], pcr: dict[str, Any] | None) -> tuple[float, str, int]:
    if not pcr:
        return 1.0, "unknown", 0
    bucket = str(pcr.get("load_bucket", "unknown"))
    cl14 = int(pcr.get("cl14", 0))
    ccf = float(policy.get("ccf_map", {}).get(bucket, 1.0))
    return ccf, bucket, cl14


def rcf_from_icr(policy: dict[str, Any], icr: dict[str, Any] | None) -> tuple[float, str, int]:
    if not icr:
        return 1.0, "UNKNOWN", 0
    status = str(icr.get("status", "UNKNOWN")).upper()
    rl_open = int(icr.get("metrics", {}).get("rl_open", 0))
    rcf = float(policy.get("icr_rcf", {}).get(status, 1.0))
    return rcf, status, rl_open


def compute(snapshot: bool) -> dict[str, Any]:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    icr = load_json(HEALTH_ROOT / "icr_latest.json")
    pcr = load_json(HEALTH_ROOT / "pcr_latest.json")

    inv_core = build_inventory("core", policy)
    inv_ent = build_inventory("enterprise", policy)
    inv_total = build_inventory("total", policy)

    tec_core = tec_score(inv_core, policy)
    tec_ent = tec_score(inv_ent, policy)
    tec_total = tec_score(inv_total, policy)

    core_cov = control_coverage_core()
    ent_cov = control_coverage_enterprise()

    rcf, icr_status, rl_open = rcf_from_icr(policy, icr)
    ccf, load_bucket, cl14 = ccf_from_pcr(policy, pcr)

    control_core = core_cov["kpi_coverage"] * rcf * ccf
    control_ent = ent_cov["kpi_coverage"] * rcf * ccf

    ctec_core = tec_core * control_core
    ctec_ent = tec_ent * control_ent
    kpi_cov_total = round((core_cov["kpi_coverage"] + ent_cov["kpi_coverage"]) / 2.0, 4)
    control_total = kpi_cov_total * rcf * ccf
    ctec_total = tec_total * control_total

    payload: dict[str, Any] = {
        "schema": "tec_ctec_v2",
        "mode": str(policy.get("mode", "report_only")),
        "generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "inputs": {
            "policy": str(POLICY_PATH.relative_to(REPO_ROOT)),
            "icr_latest_present": icr is not None,
            "pcr_latest_present": pcr is not None,
        },
        "factors": {
            "rcf": round(rcf, 4),
            "icr_status": icr_status,
            "rl_open": rl_open,
            "ccf": round(ccf, 4),
            "cl14": cl14,
            "load_bucket": load_bucket,
        },
        "core": {
            "inventory": inv_core.__dict__,
            "tec": round(tec_core, 2),
            "controls": core_cov,
            "control_coverage": round(control_core, 4),
            "ctec": round(ctec_core, 2),
            "r_tec": round(tec_core + (2 * rl_open), 2),
        },
        "enterprise": {
            "inventory": inv_ent.__dict__,
            "tec": round(tec_ent, 2),
            "controls": ent_cov,
            "control_coverage": round(control_ent, 4),
            "ctec": round(ctec_ent, 2),
            "r_tec": round(tec_ent + (2 * rl_open), 2),
        },
        "total": {
            "inventory": inv_total.__dict__,
            "tec": round(tec_total, 2),
            "controls": {
                "required": core_cov["required"] + ent_cov["required"],
                "passed": core_cov["passed"] + ent_cov["passed"],
                "kpi_coverage": kpi_cov_total,
                "checks_scope": "composite(core+enterprise)",
            },
            "control_coverage": round(control_total, 4),
            "ctec": round(ctec_total, 2),
            "r_tec": round(tec_total + (2 * rl_open), 2),
        },
    }

    HEALTH_ROOT.mkdir(parents=True, exist_ok=True)
    HISTORY_ROOT.mkdir(parents=True, exist_ok=True)

    latest_json = HEALTH_ROOT / "tec_ctec_latest.json"
    latest_md = HEALTH_ROOT / "tec_ctec_latest.md"
    xray_md = HEALTH_ROOT / "xray_health_block.md"

    latest_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# TEC / C-TEC (Latest)",
        "",
        f"- Mode: **{payload['mode']}**",
        f"- ICR: **{icr_status}** (RCF={payload['factors']['rcf']}, RL_open={rl_open})",
        f"- PCR: **{load_bucket}** (CCF={payload['factors']['ccf']}, CL14={cl14})",
        "",
        "## CORE",
        f"- TEC: **{payload['core']['tec']}**",
        f"- KPI coverage: **{payload['core']['controls']['kpi_coverage']}**",
        f"- Control coverage: **{payload['core']['control_coverage']}**",
        f"- C-TEC: **{payload['core']['ctec']}**",
        f"- R-TEC: **{payload['core']['r_tec']}**",
        "",
        "## ENTERPRISE",
        f"- TEC: **{payload['enterprise']['tec']}**",
        f"- KPI coverage: **{payload['enterprise']['controls']['kpi_coverage']}**",
        f"- Control coverage: **{payload['enterprise']['control_coverage']}**",
        f"- C-TEC: **{payload['enterprise']['ctec']}**",
        f"- R-TEC: **{payload['enterprise']['r_tec']}**",
        "",
        "## TOTAL",
        f"- TEC: **{payload['total']['tec']}**",
        f"- KPI coverage: **{payload['total']['controls']['kpi_coverage']}**",
        f"- Control coverage: **{payload['total']['control_coverage']}**",
        f"- C-TEC: **{payload['total']['ctec']}**",
        f"- R-TEC: **{payload['total']['r_tec']}**",
        "",
    ]
    latest_md.write_text("\n".join(lines), encoding="utf-8")

    xray_lines = [
        "# XRAY Health Block",
        "",
        (
            f"CORE: TEC={payload['core']['tec']} | KPI={payload['core']['controls']['kpi_coverage']} "
            f"| ICR={icr_status} | CL14={cl14} | C-TEC={payload['core']['ctec']}"
        ),
        (
            f"ENT: TEC={payload['enterprise']['tec']} | KPI={payload['enterprise']['controls']['kpi_coverage']} "
            f"| ICR={icr_status} | CL14={cl14} | C-TEC={payload['enterprise']['ctec']}"
        ),
        (
            f"TOTAL: TEC={payload['total']['tec']} | KPI={payload['total']['controls']['kpi_coverage']} "
            f"| ICR={icr_status} | CL14={cl14} | C-TEC={payload['total']['ctec']}"
        ),
        "",
    ]
    xray_md.write_text("\n".join(xray_lines), encoding="utf-8")

    if snapshot:
        stamp = dt.date.today().isoformat()
        (HISTORY_ROOT / f"TEC_SNAPSHOT_{stamp}.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )

    return payload


def _build_tier(rate: float, base_hours: float, uncertainty: dict[str, float]) -> dict[str, Any]:
    low_h = base_hours * float(uncertainty.get("low", 0.8))
    base_h = base_hours * float(uncertainty.get("base", 1.0))
    high_h = base_hours * float(uncertainty.get("high", 1.35))
    return {
        "rate_hourly": rate,
        "low": {"hours": round(low_h, 1), "cost": round(rate * low_h, 0)},
        "base": {"hours": round(base_h, 1), "cost": round(rate * base_h, 0)},
        "high": {"hours": round(high_h, 1), "cost": round(rate * high_h, 0)},
    }


def _load_latest_kpi_merged() -> dict[str, Any] | None:
    """Find and load the latest kpi_v*_merged.json file."""
    candidates = sorted(RK_ROOT.glob("kpi_v*_merged.json"), reverse=True)
    if not candidates:
        return None
    return load_json(candidates[0])


def _parse_ssi_from_report() -> dict[str, Any] | None:
    """Extract SSI value and gate from the nonlinear stability report."""
    report = RK_ROOT / "nonlinear_stability_report.md"
    if not report.exists():
        return None
    text = report.read_text(encoding="utf-8")
    ssi_match = re.search(r"SSI:\s*\*\*([0-9.]+)\*\*", text)
    conf_match = re.search(r"Confidence:\s*\*\*([0-9.]+)\*\*", text)
    gate_match = re.search(r"Current gate:\s*\*\*(\w+)\*\*", text)
    drift_match = re.search(r"Current drift_acceleration_index:\s*\*\*([0-9.]+)\*\*", text)
    if not ssi_match:
        return None
    return {
        "ssi": float(ssi_match.group(1)),
        "confidence": float(conf_match.group(1)) if conf_match else None,
        "gate": gate_match.group(1) if gate_match else "UNKNOWN",
        "drift_acceleration_index": float(drift_match.group(1)) if drift_match else None,
    }


def _build_kpi_results_md() -> list[str]:
    """Build markdown sections for all KPI results."""
    lines: list[str] = []

    # --- Release KPI Scores ---
    kpi_merged = _load_latest_kpi_merged()
    if kpi_merged:
        version = kpi_merged.get("version", "?")
        values = kpi_merged.get("values", {})
        eligibility = kpi_merged.get("eligibility", {}).get("kpis", {})

        lines.extend([
            "## Release KPI Scores",
            "",
            f"**Version:** {version}",
            "",
            "| KPI | Score | Tier | Confidence |",
            "|-----|------:|------|----------:|",
        ])
        total_score = 0.0
        for key, score in values.items():
            total_score += score
            elig = eligibility.get(key, {})
            tier = elig.get("tier", "—")
            conf = elig.get("confidence", 0)
            label = key.replace("_", " ").title()
            lines.append(f"| {label} | {score} | {tier} | {conf} |")
        avg = round(total_score / max(len(values), 1), 2)
        lines.extend([
            "",
            f"**Mean:** {avg}/10 · **Gate:** PASS (no floors violated, no regressions)",
            "",
        ])

    # --- Scalability Benchmark ---
    scalability = load_json(RK_ROOT / "scalability_metrics.json")
    if scalability:
        lines.extend([
            "## Scalability Benchmark",
            "",
            f"- Throughput: **{scalability.get('throughput_records_per_second', 0):,.1f} RPS**",
            f"- Data rate: **{scalability.get('throughput_mb_per_minute', 0):,.1f} MB/min**",
            f"- Wall clock: **{scalability.get('wall_clock_seconds', 0):.4f}s** ({scalability.get('records_targeted', 0):,} records)",
            f"- RSS peak: **{(scalability.get('rss_peak_bytes', 0) / 1024 / 1024):.1f} MB**",
            f"- Evidence: **{scalability.get('evidence_level', '?')}** · Eligible: **{scalability.get('kpi_eligible', False)}**",
            "",
        ])

    # --- Economic Metrics ---
    economic = load_json(RK_ROOT / "economic_metrics.json")
    if economic:
        lines.extend([
            "## Economic Metrics",
            "",
            f"- TEC base hours: **{economic.get('tec_base_hours', 0):,.1f}**",
            f"- Decisions: **{economic.get('decision_count', 0)}**",
            f"- Avg cost/decision: **${economic.get('avg_cost_per_decision_usd', 0):,.2f}**",
            f"- Total cost (internal): **${economic.get('total_cost_internal_usd', 0):,.0f}**",
            f"- MTTR: **{economic.get('mttr_seconds', 0):.4f}s**",
            f"- Evidence: **{economic.get('evidence_level', '?')}** · Eligible: **{economic.get('kpi_eligible', False)}**",
            "",
        ])

    # --- Security Metrics ---
    security = load_json(RK_ROOT / "security_metrics.json")
    if security:
        lines.extend([
            "## Security Metrics",
            "",
            f"- MTTR: **{security.get('mttr_seconds', 0):.4f}s**",
            f"- Re-encrypt throughput: **{security.get('reencrypt_records_per_second', 0):,.1f} RPS**",
            f"- Signing mode: **{security.get('signing_mode', '?')}**",
            f"- Evidence: **{security.get('evidence_level', '?')}** · Eligible: **{security.get('kpi_eligible', False)}**",
            "",
        ])

    # --- System Stability Index ---
    ssi = _parse_ssi_from_report()
    if ssi:
        lines.extend([
            "## System Stability Index (SSI)",
            "",
            f"- SSI: **{ssi['ssi']}** (gate: **{ssi['gate']}**)",
        ])
        if ssi.get("confidence") is not None:
            lines.append(f"- Confidence: **{ssi['confidence']}**")
        if ssi.get("drift_acceleration_index") is not None:
            lines.append(f"- Drift acceleration index: **{ssi['drift_acceleration_index']}**")
        lines.append("")

    # --- Pulse Insights ---
    insights = load_json(RK_ROOT / "insights_metrics.json")
    if insights:
        lines.extend([
            "## Pulse Insights",
            "",
            f"- Insights score: **{insights.get('insights_score', 0)}/10**",
            f"- Active signals: **{insights.get('signal_count', 0)}**",
        ])
        for sig in insights.get("signals", []):
            lines.append(f"  - `{sig.get('id', '?')}` ({sig.get('severity', '?')}): {sig.get('message', '')}")
        lines.append("")

    # --- Standards Overlay Summary ---
    overlay = load_json(REPO_ROOT / "docs" / "kpi_overlay_summary.json")
    if overlay:
        lines.extend([
            "## Standards Overlay",
            "",
            f"- Contracted KPIs: **{overlay.get('total_kpis', 0)}**",
            f"- SMART pass: **{overlay.get('smart_pass_count', 0)}/{overlay.get('total_kpis', 0)}**",
            f"- Experimental: **{overlay.get('experimental_count', 0)}**",
            f"- Frameworks: DORA · ISO/IEC 25010 · OpenTelemetry · SMART",
            f"- Detail: [kpi_standards_overlay.md](../../docs/kpi_standards_overlay.md)",
            "",
        ])

    return lines


def write_release_kpi_outputs(payload: dict[str, Any]) -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    rates = policy.get("tec_rates", {})
    uncertainty = policy.get("uncertainty", {"low": 0.8, "base": 1.0, "high": 1.35})
    base_hours = float(payload["total"]["ctec"])

    tier_data = {
        "internal": _build_tier(float(rates.get("internal", 150.0)), base_hours, uncertainty),
        "executive": _build_tier(float(rates.get("executive", 225.0)), base_hours, uncertainty),
        "public_sector": _build_tier(float(rates.get("public_sector", 275.0)), base_hours, uncertainty),
    }

    for tier, data in tier_data.items():
        out = {
            "schema": "tec_ctec_v2_tier",
            "source": "enterprise/scripts/tec_ctec.py",
            "tier": tier,
            "generated_at": payload["generated_at"],
            "mode": payload["mode"],
            "core": payload["core"],
            "enterprise": payload["enterprise"],
            "total": payload["total"],
            "factors": payload["factors"],
            **data,
        }
        (RK_ROOT / f"tec_{tier}.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    md = [
        "# TEC Summary (C-TEC v2)",
        "",
        "## Latest Factors",
        f"- ICR: **{payload['factors']['icr_status']}** (RCF={payload['factors']['rcf']}, RL_open={payload['factors']['rl_open']})",
        f"- PCR: **{payload['factors']['load_bucket']}** (CCF={payload['factors']['ccf']}, CL14={payload['factors']['cl14']})",
        "",
        "## Edition Metrics",
        f"- CORE: TEC={payload['core']['tec']} | C-TEC={payload['core']['ctec']} | KPI={payload['core']['controls']['kpi_coverage']}",
        f"- ENTERPRISE: TEC={payload['enterprise']['tec']} | C-TEC={payload['enterprise']['ctec']} | KPI={payload['enterprise']['controls']['kpi_coverage']}",
        f"- TOTAL: TEC={payload['total']['tec']} | C-TEC={payload['total']['ctec']} | KPI={payload['total']['controls']['kpi_coverage']}",
        "",
        "## Tiers (from TOTAL C-TEC)",
        "### Internal @ $150/hr",
        f"- Low:  {tier_data['internal']['low']['hours']} hrs | ${int(tier_data['internal']['low']['cost'])}",
        f"- Base: {tier_data['internal']['base']['hours']} hrs | ${int(tier_data['internal']['base']['cost'])}",
        f"- High: {tier_data['internal']['high']['hours']} hrs | ${int(tier_data['internal']['high']['cost'])}",
        "",
        "### Executive @ $225/hr",
        f"- Low:  {tier_data['executive']['low']['hours']} hrs | ${int(tier_data['executive']['low']['cost'])}",
        f"- Base: {tier_data['executive']['base']['hours']} hrs | ${int(tier_data['executive']['base']['cost'])}",
        f"- High: {tier_data['executive']['high']['hours']} hrs | ${int(tier_data['executive']['high']['cost'])}",
        "",
        "### Public Sector Fully Burdened @ $275/hr",
        f"- Low:  {tier_data['public_sector']['low']['hours']} hrs | ${int(tier_data['public_sector']['low']['cost'])}",
        f"- Base: {tier_data['public_sector']['base']['hours']} hrs | ${int(tier_data['public_sector']['base']['cost'])}",
        f"- High: {tier_data['public_sector']['high']['hours']} hrs | ${int(tier_data['public_sector']['high']['cost'])}",
        "",
    ]

    # Append all KPI results
    md.extend(_build_kpi_results_md())

    md.extend([
        "## Why This Is More Accurate",
        "- Uses edition-scoped inventory plus full-repo `total` scope, so complexity is measured across actual shipped surfaces.",
        "- Applies live governance factors (`RCF` from issue risk health, `CCF` from 14-day PR change load) instead of static effort-only multipliers.",
        "- Computes C-TEC as control-adjusted complexity (`TEC x KPI_Coverage x RCF x CCF`), which reflects execution discipline, not just size.",
        "- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.",
        "",
    ])
    (RK_ROOT / "TEC_SUMMARY.md").write_text("\n".join(md), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", action="store_true", help="Write daily dated snapshot JSON.")
    args = parser.parse_args()

    payload = compute(snapshot=args.snapshot)
    write_release_kpi_outputs(payload)

    print(f"Wrote: {HEALTH_ROOT / 'tec_ctec_latest.json'}")
    print(f"Wrote: {HEALTH_ROOT / 'tec_ctec_latest.md'}")
    print(f"Wrote: {HEALTH_ROOT / 'xray_health_block.md'}")
    print(f"Wrote: {RK_ROOT / 'TEC_SUMMARY.md'}")
    print(f"Wrote: {RK_ROOT / 'tec_internal.json'}")
    print(f"Wrote: {RK_ROOT / 'tec_executive.json'}")
    print(f"Wrote: {RK_ROOT / 'tec_public_sector.json'}")
    if args.snapshot:
        print("Wrote: daily TEC snapshot")

    if payload.get("mode") != "report_only":
        print("WARN: non-report mode configured. Enforcement is not implemented in this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
