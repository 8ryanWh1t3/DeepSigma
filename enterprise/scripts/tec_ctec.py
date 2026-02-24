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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", action="store_true", help="Write daily dated snapshot JSON.")
    args = parser.parse_args()

    payload = compute(snapshot=args.snapshot)
    print(f"Wrote: {HEALTH_ROOT / 'tec_ctec_latest.json'}")
    print(f"Wrote: {HEALTH_ROOT / 'tec_ctec_latest.md'}")
    print(f"Wrote: {HEALTH_ROOT / 'xray_health_block.md'}")
    if args.snapshot:
        print("Wrote: daily TEC snapshot")

    if payload.get("mode") != "report_only":
        print("WARN: non-report mode configured. Enforcement is not implemented in this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
