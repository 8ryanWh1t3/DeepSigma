"""Governance — Policy, Audit, Drift Registry, and Telemetry.

Board-grade governance layer for multi-tenant credibility engine.
Policies as data, immutable audit trail, seal chaining, drift recurrence,
and SLO telemetry.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from governance.audit import append_audit, audit_action
from governance.drift_registry import (
    get_weighted_drift_summary,
    update_drift_registry,
)
from governance.telemetry import check_quota, record_metric

__all__ = [
    "append_audit",
    "audit_action",
    "update_drift_registry",
    "get_weighted_drift_summary",
    "record_metric",
    "check_quota",
]
