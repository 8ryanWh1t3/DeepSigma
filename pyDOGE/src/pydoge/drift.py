from __future__ import annotations

from typing import Any


def detect_outcome_drift(outcomes: list[Any], variance_threshold: float = 0.20) -> list[dict]:
    findings = []
    for o in outcomes:
        if o.variance is None:
            if o.expected.strip() != o.observed.strip():
                findings.append({
                    "type": "QUALITATIVE_OUTCOME_DRIFT",
                    "work_id": o.work_id,
                    "period": o.period,
                    "expected": o.expected,
                    "observed": o.observed,
                })
        elif abs(o.variance) >= variance_threshold:
            findings.append({
                "type": "OUTCOME_DRIFT",
                "work_id": o.work_id,
                "period": o.period,
                "variance": o.variance,
                "expected": o.expected,
                "observed": o.observed,
            })
    return findings
