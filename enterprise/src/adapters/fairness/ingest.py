"""Ingest fairness audit results from external tools into DeepSigma drift signals.

Converts output from external fairness libraries (AIF360, Fairlearn, or custom
JSON reports) into DriftSignal objects that integrate with the existing drift
detection and patch pipeline.

Usage:

    from adapters.fairness.ingest import ingest_fairness_report

    # From a JSON report file produced by an external fairness audit
    signals = ingest_fairness_report({
        "tool": "aif360",
        "model_id": "loan-approval-v3",
        "timestamp": "2026-02-27T12:00:00Z",
        "metrics": [
            {
                "metric": "disparate_impact",
                "protected_attribute": "gender",
                "value": 0.72,
                "threshold": 0.80,
                "passed": False,
            },
            {
                "metric": "demographic_parity_difference",
                "protected_attribute": "race",
                "value": 0.05,
                "threshold": 0.10,
                "passed": True,
            }
        ]
    })
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from dashboard.server.models_exhaust import DriftSeverity, DriftSignal, DriftType

# Map external metric names to DriftType
_METRIC_TO_DRIFT_TYPE: Dict[str, DriftType] = {
    "disparate_impact": DriftType.disparate_impact,
    "disparate_impact_ratio": DriftType.disparate_impact,
    "demographic_parity": DriftType.demographic_parity_violation,
    "demographic_parity_difference": DriftType.demographic_parity_violation,
    "equal_opportunity": DriftType.fairness_metric_degradation,
    "equalized_odds": DriftType.fairness_metric_degradation,
    "calibration": DriftType.fairness_metric_degradation,
    "predictive_parity": DriftType.fairness_metric_degradation,
}


def _fingerprint(metric: Dict[str, Any], tool: str, model_id: str) -> str:
    """Deterministic fingerprint for deduplication."""
    key = f"{tool}:{model_id}:{metric.get('metric', '')}:{metric.get('protected_attribute', '')}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def ingest_fairness_report(report: Dict[str, Any]) -> List[DriftSignal]:
    """Convert an external fairness audit report to DriftSignal list.

    Args:
        report: Dict with keys:
            - tool: str (e.g. "aif360", "fairlearn", "custom")
            - model_id: str
            - timestamp: str (ISO 8601)
            - metrics: list of metric dicts, each with:
                - metric: str (metric name)
                - protected_attribute: str
                - value: float
                - threshold: float
                - passed: bool

    Returns:
        List of DriftSignal for metrics that failed their threshold.
    """
    tool = report.get("tool", "unknown")
    model_id = report.get("model_id", "unknown")
    metrics = report.get("metrics", [])

    signals: List[DriftSignal] = []
    for m in metrics:
        if m.get("passed", True):
            continue

        metric_name = m.get("metric", "unknown")
        drift_type = _METRIC_TO_DRIFT_TYPE.get(metric_name, DriftType.fairness_metric_degradation)
        attr = m.get("protected_attribute", "unknown")
        value = m.get("value", 0.0)
        threshold = m.get("threshold", 0.0)

        signals.append(DriftSignal(
            drift_id=f"fairness-{_fingerprint(m, tool, model_id)}",
            drift_type=drift_type,
            severity=DriftSeverity.red if abs(value - threshold) > 0.15 else DriftSeverity.yellow,
            fingerprint=_fingerprint(m, tool, model_id),
            description=(
                f"Fairness violation ({tool}): {metric_name} on '{attr}' "
                f"= {value:.3f} (threshold {threshold:.3f}) for model {model_id}"
            ),
            entity=model_id,
            property_name=f"fairness.{metric_name}.{attr}",
            expected_value=str(threshold),
            actual_value=str(value),
        ))

    return signals


def ingest_aif360(dataset_metrics: Dict[str, Any], model_id: str = "unknown") -> List[DriftSignal]:
    """Convenience wrapper for AIF360 ClassificationMetric output.

    Converts AIF360's metric dict into the standard report format and ingests it.
    """
    metrics = []
    for name in ("disparate_impact", "statistical_parity_difference", "equal_opportunity_difference"):
        val = dataset_metrics.get(name)
        if val is not None:
            threshold = 0.80 if name == "disparate_impact" else 0.10
            metrics.append({
                "metric": name,
                "protected_attribute": dataset_metrics.get("protected_attribute", "unknown"),
                "value": val,
                "threshold": threshold,
                "passed": (val >= threshold) if name == "disparate_impact" else (abs(val) <= threshold),
            })

    return ingest_fairness_report({
        "tool": "aif360",
        "model_id": model_id,
        "metrics": metrics,
    })


def ingest_fairlearn(metrics_frame: Any, model_id: str = "unknown") -> List[DriftSignal]:
    """Convenience wrapper for Fairlearn MetricFrame output.

    Accepts a MetricFrame-like dict (or the .overall / .by_group output)
    and converts to the standard report format.
    """
    metrics = []
    if isinstance(metrics_frame, dict):
        for metric_name, groups in metrics_frame.items():
            if isinstance(groups, dict):
                values = list(groups.values())
                if values:
                    ratio = min(values) / max(values) if max(values) > 0 else 0
                    metrics.append({
                        "metric": f"group_ratio_{metric_name}",
                        "protected_attribute": "group",
                        "value": ratio,
                        "threshold": 0.80,
                        "passed": ratio >= 0.80,
                    })

    return ingest_fairness_report({
        "tool": "fairlearn",
        "model_id": model_id,
        "metrics": metrics,
    })
