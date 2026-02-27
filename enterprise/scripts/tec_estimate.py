#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
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


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _extract_issue_refs(text: str) -> set[int]:
    return {int(match.group(1)) for match in re.finditer(r"#(\d+)", text)}


def _subsystems_for_issue(issue: dict, issue_labels: list[str]) -> set[str]:
    text = f"{issue.get('title', '')}\n{issue.get('body', '')}".lower()
    subsystems: set[str] = set()
    if _is_security(issue_labels) or "security" in text or "crypto" in text:
        subsystems.add("security")
    if "authority" in text:
        subsystems.add("authority")
    if "kpi" in text or any(label.startswith("kpi:") for label in issue_labels):
        subsystems.add("kpi")
    if "workflow" in text or "ci" in text or ".github/workflows" in text:
        subsystems.add("ci")
    return subsystems


def _pr_complexity_score(pr: dict, cfg: dict) -> float:
    loc_delta = float(pr.get("additions", 0)) + float(pr.get("deletions", 0))
    changed_files = float(pr.get("changedFiles", 0))
    loc_component = min(loc_delta / float(cfg["pr_loc_scale"]), float(cfg["pr_loc_cap"]))
    files_component = min(changed_files / float(cfg["pr_files_scale"]), float(cfg["pr_files_cap"]))
    return loc_component + files_component


def _sum_repo_tree() -> tuple[int, int, int]:
    workflow_dir = REPO_ROOT / ".github" / "workflows"
    workflow_count = len(list(workflow_dir.glob("*.yml"))) if workflow_dir.exists() else 0
    test_file_count = sum(
        len(list(d.rglob("test_*.py")))
        for d in (REPO_ROOT / "tests", REPO_ROOT / "tests-enterprise", ROOT / "tests")
        if d.exists()
    )
    doc_file_count = len(list((ROOT / "docs").rglob("*.md"))) if (ROOT / "docs").exists() else 0
    return workflow_count, test_file_count, doc_file_count


def compute() -> dict:
    issues = json.loads((OUT / "issues_all.json").read_text(encoding="utf-8"))
    prs = json.loads((OUT / "prs_merged.json").read_text(encoding="utf-8"))
    complexity_cfg = WEIGHTS["complexity"]
    now = datetime.now(UTC)

    issue_hours = 0.0
    security_issues = 0
    committee_cycles = 0
    complexity_hours = 0.0
    complexity_indices: list[float] = []

    issue_map = {int(issue["number"]): issue for issue in issues if "number" in issue}
    issue_to_pr_scores: dict[int, list[float]] = {}
    for pr in prs:
        score = _pr_complexity_score(pr, complexity_cfg)
        pr_text = f"{pr.get('title', '')}\n{pr.get('body', '')}"
        refs = _extract_issue_refs(pr_text)
        for ref in refs:
            if ref in issue_map:
                issue_to_pr_scores.setdefault(ref, []).append(score)

    for issue in issues:
        issue_labels = _labels(issue)
        number = int(issue.get("number", -1))
        base_issue_hours = _issue_base_hours(issue_labels)
        issue_hours += base_issue_hours

        # Complexity from associated PR churn.
        pr_scores = issue_to_pr_scores.get(number, [])
        pr_score_total = sum(pr_scores)
        pr_mult = 1.0 + min(
            pr_score_total * float(complexity_cfg["pr_score_weight"]),
            float(complexity_cfg["pr_multiplier_cap"]),
        )

        # Complexity from cross-subsystem touch points.
        subsystem_count = len(_subsystems_for_issue(issue, issue_labels))
        subsystem_mult = 1.0 + min(
            max(subsystem_count - 1, 0) * float(complexity_cfg["subsystem_step"]),
            float(complexity_cfg["subsystem_cap"]),
        )

        # Complexity from open-close duration.
        created = _parse_iso(issue.get("createdAt"))
        closed = _parse_iso(issue.get("closedAt")) or now
        duration_days = max((closed - created).days, 0) if created else 0
        duration_over = max(duration_days - int(complexity_cfg["duration_threshold_days"]), 0)
        duration_mult = 1.0 + min(
            duration_over / float(complexity_cfg["duration_window_days"]),
            float(complexity_cfg["duration_cap"]),
        )

        # Coordination complexity from explicit dependency references.
        dependency_refs = _extract_issue_refs(issue.get("body", ""))
        dependency_refs.discard(number)
        dependency_mult = 1.0 + min(
            len(dependency_refs) * float(complexity_cfg["dependency_ref_step"]),
            float(complexity_cfg["dependency_ref_cap"]),
        )

        complexity_index = pr_mult * subsystem_mult * duration_mult * dependency_mult
        complexity_indices.append(complexity_index)
        complexity_hours += base_issue_hours * complexity_index

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
    ctec_hours = complexity_hours + pr_overhead + workflow_hours + test_hours + doc_hours + committee_hours

    return {
        "counts": {
            "issues_total": len(issues),
            "prs_merged": len(prs),
            "workflows": workflow_count,
            "test_files": test_file_count,
            "doc_files": doc_file_count,
            "security_issues_tagged": security_issues,
            "committee_cycles_est": committee_cycles,
            "issues_with_pr_link_est": len(issue_to_pr_scores),
        },
        "hours": {
            "issues_weighted": round(issue_hours, 1),
            "issues_complexity_weighted": round(complexity_hours, 1),
            "pr_overhead": round(pr_overhead, 1),
            "workflows": round(workflow_hours, 1),
            "tests": round(test_hours, 1),
            "docs": round(doc_hours, 1),
            "committee": round(committee_hours, 1),
            "total_base": round(base_hours, 1),
            "total_ctec": round(ctec_hours, 1),
        },
        "complexity": {
            "avg_index": round(sum(complexity_indices) / max(len(complexity_indices), 1), 3),
            "max_index": round(max(complexity_indices) if complexity_indices else 1.0, 3),
            "config": complexity_cfg,
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


def _load_insights_metrics() -> dict | None:
    path = OUT / "insights_metrics.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _insights_adjustment(hours: float, insights: dict | None) -> tuple[float, dict]:
    cfg = WEIGHTS.get("insights", {})
    enabled = bool(cfg.get("enabled", False))
    details = {
        "enabled": enabled,
        "source": "release_kpis/insights_metrics.json",
        "present": insights is not None,
        "score": None,
        "signal_count": 0,
        "factor": 1.0,
        "hours_delta": 0.0,
    }
    if not enabled or insights is None:
        return hours, details

    raw_score = insights.get("insights_score")
    score = float(raw_score) if isinstance(raw_score, (int, float)) else float(cfg.get("neutral_score", 5.0))
    score = max(0.0, min(10.0, score))
    neutral = float(cfg.get("neutral_score", 5.0))
    score_sensitivity = float(cfg.get("score_sensitivity", 0.02))
    max_reduction = float(cfg.get("max_reduction", 0.12))
    max_increase = float(cfg.get("max_increase", 0.18))
    signal_step = float(cfg.get("signal_step", 0.015))
    signal_cap = float(cfg.get("signal_cap", 0.12))

    signals = insights.get("signals")
    if isinstance(signals, list):
        signal_count = len(signals)
    elif isinstance(signals, dict):
        signal_count = len(signals)
    else:
        raw_signal_count = insights.get("signal_count")
        signal_count = int(raw_signal_count) if isinstance(raw_signal_count, int) else 0

    # Better insight score reduces effort; lower score increases effort.
    score_component = (neutral - score) * score_sensitivity
    score_component = max(-max_reduction, min(max_increase, score_component))

    # More active signals add complexity.
    signal_component = min(signal_count * signal_step, signal_cap)

    factor = max(1.0 - max_reduction, min(1.0 + max_increase + signal_cap, 1.0 + score_component + signal_component))
    adjusted_hours = hours * factor

    details.update(
        {
            "score": round(score, 3),
            "signal_count": signal_count,
            "factor": round(factor, 4),
            "hours_delta": round(adjusted_hours - hours, 1),
        }
    )
    return adjusted_hours, details


def main() -> int:
    data = compute()
    raw_ctec_hours = float(data["hours"]["total_ctec"])
    insights = _load_insights_metrics()
    ctec_hours, insights_details = _insights_adjustment(raw_ctec_hours, insights)
    data["hours"]["total_ctec_unadjusted"] = round(raw_ctec_hours, 1)
    data["hours"]["insights_adjustment_hours"] = round(ctec_hours - raw_ctec_hours, 1)
    data["hours"]["total_ctec"] = round(ctec_hours, 1)
    data["insights"] = insights_details
    uncertainty = WEIGHTS["uncertainty"]

    internal_rate = float(WEIGHTS["rates"]["internal_hourly"])
    executive_rate = float(WEIGHTS["rates"]["exec_hourly"])
    ps_rate = float(WEIGHTS["rates"]["public_sector_fully_burdened_hourly"])

    OUT.mkdir(parents=True, exist_ok=True)
    _write_json(
        OUT / "tec_internal.json",
        {"tier": "internal", **data, **_build_tier(internal_rate, ctec_hours, uncertainty)},
    )
    _write_json(
        OUT / "tec_executive.json",
        {"tier": "executive", **data, **_build_tier(executive_rate, ctec_hours, uncertainty)},
    )
    _write_json(
        OUT / "tec_public_sector.json",
        {"tier": "public_sector", **data, **_build_tier(ps_rate, ctec_hours, uncertainty)},
    )

    md_lines = ["# TEC Summary (ROM)", "", "## Counts"]
    for key, value in data["counts"].items():
        md_lines.append(f"- {key}: **{value}**")
    md_lines.extend(["", "## Effort (Base hours breakdown)"])
    for key, value in data["hours"].items():
        md_lines.append(f"- {key}: **{value}**")
    md_lines.extend(
        [
            "",
            "## Complexity (C-TEC v1.0)",
            f"- avg_index: **{data['complexity']['avg_index']}**",
            f"- max_index: **{data['complexity']['max_index']}**",
            "- signals: PR diff size, changed files, cross-subsystem touch, issue duration, dependency refs",
            "",
            "## Pulse Insights Adjustment",
            f"- insights_present: **{data['insights']['present']}**",
            f"- insights_score: **{data['insights']['score']}**",
            f"- signal_count: **{data['insights']['signal_count']}**",
            f"- adjustment_factor: **{data['insights']['factor']}x**",
            f"- adjustment_hours: **{data['insights']['hours_delta']}**",
        ]
    )

    md_lines.append("")
    md_lines.append("## Tiers (Low / Base / High)")
    for name, rate in (
        ("Internal", internal_rate),
        ("Executive", executive_rate),
        ("Public Sector Fully Burdened", ps_rate),
    ):
        low = ctec_hours * float(uncertainty["low"])
        base = ctec_hours * float(uncertainty["base"])
        high = ctec_hours * float(uncertainty["high"])
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
