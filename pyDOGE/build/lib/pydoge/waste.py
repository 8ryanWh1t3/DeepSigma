from __future__ import annotations

import re
from difflib import SequenceMatcher
from itertools import combinations
from typing import Any


def _norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return " ".join(text.split())


def duplicate_candidates(work: list[Any], threshold: float = 0.78) -> list[dict]:
    active = [w for w in work if w.active]
    findings: list[dict] = []
    for a, b in combinations(active, 2):
        # Duplicates are only meaningful when they support the same mission or have overlapping outputs.
        output_overlap = bool(set(map(_norm, a.outputs)) & set(map(_norm, b.outputs)))
        same_mission = a.mission_id and a.mission_id == b.mission_id
        if not (same_mission or output_overlap):
            continue
        name_score = SequenceMatcher(None, _norm(a.name), _norm(b.name)).ratio()
        combined_score = SequenceMatcher(None, _norm(a.name + " " + " ".join(a.outputs)), _norm(b.name + " " + " ".join(b.outputs))).ratio()
        # Exact/near-exact output overlap is strong architectural evidence that two work items
        # deserve duplicate-work review, even when their labels differ.
        output_score = 0.85 if output_overlap else 0.0
        score = max(name_score, combined_score, output_score)
        if score >= threshold:
            findings.append({
                "type": "DUPLICATE_CANDIDATE",
                "work_a": a.id,
                "work_b": b.id,
                "similarity": round(score, 3),
                "reason": "Similar work/output within the same mission context; human review required before consolidation.",
            })
    return sorted(findings, key=lambda x: x["similarity"], reverse=True)


def rework_findings(work: list[Any], threshold: float = 0.15) -> list[dict]:
    out = []
    for w in work:
        if w.active and w.rework_rate >= threshold:
            out.append({
                "type": "REWORK",
                "work_id": w.id,
                "rework_rate": w.rework_rate,
                "monthly_rework_hours": round(w.volume_per_month * w.touch_time_hours * w.rework_rate, 2),
            })
    return sorted(out, key=lambda x: x["monthly_rework_hours"], reverse=True)


def orphan_findings(work: list[Any]) -> list[dict]:
    out = []
    for w in work:
        if not w.active:
            continue
        reasons = []
        if not w.mission_id:
            reasons.append("no mission binding")
        if not w.policy_ids:
            reasons.append("no policy/requirement binding")
        if reasons:
            out.append({"type": "ORPHAN_WORK", "work_id": w.id, "reasons": reasons})
    return out


def handoff_findings(work: list[Any], min_wait_ratio: float = 0.50) -> list[dict]:
    out = []
    for w in work:
        if not w.active or w.cycle_time_hours <= 0:
            continue
        wait = max(0.0, w.cycle_time_hours - w.touch_time_hours)
        ratio = wait / w.cycle_time_hours
        if ratio >= min_wait_ratio or w.approval_steps >= 3:
            out.append({
                "type": "HANDOFF_LATENCY",
                "work_id": w.id,
                "cycle_time_hours": w.cycle_time_hours,
                "touch_time_hours": w.touch_time_hours,
                "wait_time_hours": round(wait, 2),
                "wait_ratio": round(ratio, 3),
                "approval_steps": w.approval_steps,
            })
    return sorted(out, key=lambda x: (x["wait_ratio"], x["approval_steps"]), reverse=True)
