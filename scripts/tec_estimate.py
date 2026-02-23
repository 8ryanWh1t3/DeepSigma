#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "release_kpis"
WEIGHTS = yaml.safe_load((ROOT / "governance" / "tec_weights.yaml").read_text(encoding="utf-8"))


def _labels(item: dict) -> list[str]:
    return [label.get("name", "") for label in item.get("labels", [])]


def _pick(prefix: str, labels: list[str]) -> str:
    for label in labels:
        if label.startswith(prefix):
            return label
    return ""


def _is_security(labels: list[str]) -> bool:
    return (
        "security" in labels
        or any(label.startswith("sec:") for label in labels)
        or any("crypto" in label for label in labels)
    )


def _is_committee_cycle(labels: list[str]) -> bool:
    return (
        any(label.startswith("committee:") for label in labels)
        or "design-review" in labels
        or "security-review" in labels
        or "needs-approval" in labels
    )


def _issue_base_hours(labels: list[str]) -> float:
    issue_type = _pick("type:", labels) or "type:feature"
    severity = _pick("sev:", labels) or "sev:P2"
    base = float(
        WEIGHTS["issue_hours"].get(
            issue_type,
            WEIGHTS["issue_hours"]["type:feature"],
        )
    )
    if _is_security(labels):
        base = max(base, float(WEIGHTS["issue_hours"]["security_default"]))
    multiplier = float(WEIGHTS["severity_multiplier"].get(severity, 1.0))
    return base * multiplier


def _sum_repo_tree() -> tuple[int, int, int]:
    workflow_count = (
        len(list((ROOT / ".github" / "workflows").glob("*.yml")))
        if (ROOT / ".github" / "workflows").exists()
        else 0
    )
    test_file_count = len(list((ROOT / "tests").rglob("test_*.py"))) if (ROOT / "tests").exists() else 0
    doc_file_count = len(list((ROOT / "docs").rglob("*.md"))) if (ROOT / "docs").exists() else 0
    return workflow_count, test_file_count, doc_file_count


def compute() -> dict:
    issues = json.loads((OUT / "issues_all.json").read_text(encoding="utf-8"))
    prs = json.loads((OUT / "prs_merged.json").read_text(encoding="utf-8"))

    issue_hours = 0.0
    security_issues = 0
    committee_cycles = 0

    for issue in issues:
        issue_labels = _labels(issue)
        issue_hours += _issue_base_hours(issue_labels)
        if _is_security(issue_labels):
            security_issues += 1
        if _is_committee_cycle(issue_labels):
            committee_cycles += 1

    pr_overhead = len(prs) * float(WEIGHTS.get("pr_overhead_hours", 1.5))
    workflow_count, test_file_count, doc_file_count = _sum_repo_tree()
    workflow_hours = workflow_count * float(WEIGHTS.get("workflow_hours", 5))
    test_hours = test_file_count * float(WEIGHTS.get("test_file_hours", 2))
    doc_hours = doc_file_count * float(WEIGHTS.get("doc_file_hours", 1.5))
    committee_hours = committee_cycles * float(WEIGHTS["issue_hours"].get("committee_cycle", 8))
    base_hours = issue_hours + pr_overhead + workflow_hours + test_hours + doc_hours + committee_hours

    return {
        "counts": {
            "issues_total": len(issues),
            "prs_merged": len(prs),
            "workflows": workflow_count,
            "test_files": test_file_count,
            "doc_files": doc_file_count,
            "security_issues_tagged": security_issues,
            "committee_cycles_est": committee_cycles,
        },
        "hours": {
            "issues_weighted": round(issue_hours, 1),
            "pr_overhead": round(pr_overhead, 1),
            "workflows": round(workflow_hours, 1),
            "tests": round(test_hours, 1),
            "docs": round(doc_hours, 1),
            "committee": round(committee_hours, 1),
            "total_base": round(base_hours, 1),
        },
    }


def _build_tier(rate: float, base_hours: float, uncertainty: dict) -> dict:
    low = base_hours * float(uncertainty["low"])
    base = base_hours * float(uncertainty["base"])
    high = base_hours * float(uncertainty["high"])
    return {
        "rate_hourly": rate,
        "low": {"hours": round(low, 1), "cost": round(rate * low, 0)},
        "base": {"hours": round(base, 1), "cost": round(rate * base, 0)},
        "high": {"hours": round(high, 1), "cost": round(rate * high, 0)},
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    data = compute()
    base_hours = float(data["hours"]["total_base"])
    uncertainty = WEIGHTS["uncertainty"]

    internal_rate = float(WEIGHTS["rates"]["internal_hourly"])
    executive_rate = float(WEIGHTS["rates"]["exec_hourly"])
    dod_rate = float(WEIGHTS["rates"]["dod_fully_burdened_hourly"])

    OUT.mkdir(parents=True, exist_ok=True)
    _write_json(
        OUT / "tec_internal.json",
        {"tier": "internal", **data, **_build_tier(internal_rate, base_hours, uncertainty)},
    )
    _write_json(
        OUT / "tec_executive.json",
        {"tier": "executive", **data, **_build_tier(executive_rate, base_hours, uncertainty)},
    )
    _write_json(
        OUT / "tec_dod.json",
        {"tier": "dod", **data, **_build_tier(dod_rate, base_hours, uncertainty)},
    )

    md_lines = ["# TEC Summary (ROM)", "", "## Counts"]
    for key, value in data["counts"].items():
        md_lines.append(f"- {key}: **{value}**")
    md_lines.extend(["", "## Effort (Base hours breakdown)"])
    for key, value in data["hours"].items():
        md_lines.append(f"- {key}: **{value}**")

    md_lines.append("")
    md_lines.append("## Tiers (Low / Base / High)")
    for name, rate in (
        ("Internal", internal_rate),
        ("Executive", executive_rate),
        ("DoD Fully Burdened", dod_rate),
    ):
        low = base_hours * float(uncertainty["low"])
        base = base_hours * float(uncertainty["base"])
        high = base_hours * float(uncertainty["high"])
        md_lines.append(f"### {name} @ ${int(rate)}/hr")
        md_lines.append(f"- Low:  {round(low, 1)} hrs | ${round(rate * low, 0)}")
        md_lines.append(f"- Base: {round(base, 1)} hrs | ${round(rate * base, 0)}")
        md_lines.append(f"- High: {round(high, 1)} hrs | ${round(rate * high, 0)}")
        md_lines.append("")

    (OUT / "TEC_SUMMARY.md").write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")
    print("Wrote TEC artifacts to release_kpis/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
