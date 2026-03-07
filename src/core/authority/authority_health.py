"""Authority Health -- severity classification and health summary.

Aggregates drift signals from authority_drift.py into an overall
health assessment with the 4-level authority severity model.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List


# 4-level authority drift severity (adds ORANGE between YELLOW and RED)
AUTHORITY_SEVERITY_ORDER = {"green": 0, "yellow": 1, "orange": 2, "red": 3}


def classify_authority_severity(signals: List[Dict[str, Any]]) -> str:
    """Return the worst severity from a list of drift signals.

    Severity model:
        GREEN  = valid authority chain
        YELLOW = near expiry / stale policy / weak custody
        ORANGE = broken delegation / scope mismatch
        RED    = unauthorized execution path / invalid signer / orphaned authority
    """
    if not signals:
        return "green"

    worst = "green"
    for sig in signals:
        sev = sig.get("severity", "green")
        if AUTHORITY_SEVERITY_ORDER.get(sev, 0) > AUTHORITY_SEVERITY_ORDER.get(worst, 0):
            worst = sev
    return worst


def build_health_summary(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a structured health summary from drift signals.

    Returns:
        Dict with overallSeverity, signalCount, bySubtype, bySeverity,
        worstSignals (top 3), and scannedAt.
    """
    by_subtype: Dict[str, int] = defaultdict(int)
    by_severity: Dict[str, int] = defaultdict(int)

    for sig in signals:
        by_subtype[sig.get("driftType", "unknown")] += 1
        by_severity[sig.get("severity", "green")] += 1

    # Sort signals by severity (worst first)
    sorted_signals = sorted(
        signals,
        key=lambda s: AUTHORITY_SEVERITY_ORDER.get(s.get("severity", "green"), 0),
        reverse=True,
    )

    return {
        "overallSeverity": classify_authority_severity(signals),
        "signalCount": len(signals),
        "bySubtype": dict(by_subtype),
        "bySeverity": dict(by_severity),
        "worstSignals": sorted_signals[:3],
        "scannedAt": datetime.now(timezone.utc).isoformat(),
    }
