#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ENT_ROOT = Path(__file__).resolve().parents[1]
HEALTH_ROOT = ENT_ROOT / "release_kpis" / "health"
HISTORY_ROOT = HEALTH_ROOT / "history"


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


def _series(prefix: str) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(HISTORY_ROOT.glob(f"{prefix}_*.json")):
        stamp = path.stem.replace(f"{prefix}_", "")
        payload = load_json(path)
        if payload is None:
            continue
        rows.append((stamp, payload))
    return rows[-7:]


def _pick_row(stamp: str, tec: dict[str, Any] | None, icr: dict[str, Any] | None, pcr: dict[str, Any] | None) -> str:
    core_ctec = "-"
    ent_ctec = "-"
    total_ctec = "-"
    icr_status = "-"
    rl_open = "-"
    cl14 = "-"

    if tec:
        core_ctec = str(tec.get("core", {}).get("ctec", "-"))
        ent_ctec = str(tec.get("enterprise", {}).get("ctec", "-"))
        total_ctec = str(tec.get("total", {}).get("ctec", "-"))
    if icr:
        icr_status = str(icr.get("status", "-"))
        rl_open = str(icr.get("metrics", {}).get("rl_open", "-"))
    if pcr:
        cl14 = str(pcr.get("cl14", "-"))

    return f"| {stamp} | {core_ctec} | {ent_ctec} | {total_ctec} | {icr_status} | {rl_open} | {cl14} |"


def build_summary() -> str:
    generated = dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    icr_latest = load_json(HEALTH_ROOT / "icr_latest.json")
    pcr_latest = load_json(HEALTH_ROOT / "pcr_latest.json")
    tec_latest = load_json(HEALTH_ROOT / "tec_ctec_latest.json")

    tec_rows = {stamp: payload for stamp, payload in _series("TEC_SNAPSHOT")}
    icr_rows = {stamp: payload for stamp, payload in _series("ICR_SNAPSHOT")}
    pcr_rows = {stamp: payload for stamp, payload in _series("PCR_SNAPSHOT")}
    stamps = sorted(set(tec_rows) | set(icr_rows) | set(pcr_rows))[-7:]

    lines = [
        "# Health Summary (v2)",
        "",
        f"- Generated: {generated}",
        "- Source: `enterprise/release_kpis/health`",
        "",
        "## Latest",
        "",
    ]

    if tec_latest:
        lines.extend(
            [
                f"- CORE: TEC={tec_latest.get('core', {}).get('tec', '-')} | C-TEC={tec_latest.get('core', {}).get('ctec', '-')} | KPI={tec_latest.get('core', {}).get('controls', {}).get('kpi_coverage', '-')}",
                f"- ENTERPRISE: TEC={tec_latest.get('enterprise', {}).get('tec', '-')} | C-TEC={tec_latest.get('enterprise', {}).get('ctec', '-')} | KPI={tec_latest.get('enterprise', {}).get('controls', {}).get('kpi_coverage', '-')}",
                f"- TOTAL: TEC={tec_latest.get('total', {}).get('tec', '-')} | C-TEC={tec_latest.get('total', {}).get('ctec', '-')} | KPI={tec_latest.get('total', {}).get('controls', {}).get('kpi_coverage', '-')}",
            ]
        )
    else:
        lines.append("- TEC/C-TEC latest not present")

    if icr_latest:
        lines.append(
            f"- ICR: {icr_latest.get('status', '-')} | RL_open={icr_latest.get('metrics', {}).get('rl_open', '-')}"
        )
    else:
        lines.append("- ICR latest not present")

    if pcr_latest:
        lines.append(
            f"- PCR: {pcr_latest.get('load_bucket', '-')} | CL14={pcr_latest.get('cl14', '-')}"
        )
    else:
        lines.append("- PCR latest not present")

    lines.extend(["", "## 7-Day Trend", "", "| Date | CORE C-TEC | ENT C-TEC | TOTAL C-TEC | ICR | RL_open | CL14 |", "|---|---:|---:|---:|---|---:|---:|"])

    if not stamps:
        lines.append("| - | - | - | - | - | - | - |")
    else:
        for stamp in stamps:
            lines.append(
                _pick_row(
                    stamp,
                    tec_rows.get(stamp),
                    icr_rows.get(stamp),
                    pcr_rows.get(stamp),
                )
            )

    lines.extend(
        [
            "",
            "## Enforcement Signal",
            "",
            "- Rule: if C-TEC drops while TEC rises across snapshots, treat as unmanaged complexity drift.",
            "- Action: open drift event + patch plan, freeze net-new capability until control recovers.",
            "",
            "## Accuracy Notes",
            "",
            "- `TOTAL` now measures full-repo scope, while `CORE` and `ENTERPRISE` stay edition-specific for boundary clarity.",
            "- C-TEC is control-adjusted using current governance posture (`ICR -> RCF`) and current change pressure (`PCR/CL14 -> CCF`).",
            "- Snapshot history provides time-series evidence, reducing one-off metric noise and making degradation/recovery explicit.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    HEALTH_ROOT.mkdir(parents=True, exist_ok=True)
    HISTORY_ROOT.mkdir(parents=True, exist_ok=True)

    out_path = HEALTH_ROOT / "HEALTH_SUMMARY.md"
    out_path.write_text(build_summary(), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
