"""Governance — Drift Recurrence Weighting.

Tracks drift fingerprints per tenant and computes severity multipliers
based on recurrence frequency.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BASE_REGISTRY_DIR = Path(__file__).parent.parent / "data" / "drift_registry"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _registry_path(tenant_id: str) -> Path:
    """Return the drift registry file path for a tenant."""
    d = _BASE_REGISTRY_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{tenant_id}.json"


def _load_registry(tenant_id: str) -> dict[str, Any]:
    """Load the drift registry for a tenant."""
    path = _registry_path(tenant_id)
    if not path.exists():
        return {"tenant_id": tenant_id, "fingerprints": {}, "updated_at": _now_iso()}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_registry(tenant_id: str, registry: dict[str, Any]) -> None:
    """Persist the drift registry."""
    registry["updated_at"] = _now_iso()
    path = _registry_path(tenant_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, default=str)
        f.write("\n")


def update_drift_registry(
    tenant_id: str,
    drift_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Update the drift registry with current events.

    Groups events by fingerprint (or category if no fingerprint) and
    records 24h/7d counts and last_seen timestamps.

    Returns the updated registry.
    """
    registry = _load_registry(tenant_id)
    fingerprints = registry.get("fingerprints", {})

    # Count occurrences by fingerprint
    counts: dict[str, int] = {}
    for event in drift_events:
        fp = event.get("fingerprint") or event.get("category", "unknown")
        counts[fp] = counts.get(fp, 0) + 1

    # Update registry entries
    for fp, count in counts.items():
        entry = fingerprints.get(fp, {
            "count_24h": 0,
            "count_7d": 0,
            "last_seen": None,
            "severity_weight": 1.0,
        })
        entry["count_24h"] = count
        entry["count_7d"] = entry.get("count_7d", 0) + count
        entry["last_seen"] = _now_iso()

        # Compute severity weight from 24h recurrence
        if count > 50:
            entry["severity_weight"] = 3.0
        elif count > 25:
            entry["severity_weight"] = 2.0
        elif count > 10:
            entry["severity_weight"] = 1.5
        else:
            entry["severity_weight"] = 1.0

        fingerprints[fp] = entry

    registry["fingerprints"] = fingerprints
    _save_registry(tenant_id, registry)
    return registry


def get_weighted_drift_summary(
    tenant_id: str,
    drift_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a drift summary with recurrence weighting applied.

    Returns:
        Dict with total_events, weighted_severity, recurrence_multiplier,
        and top_fingerprints.
    """
    registry = _load_registry(tenant_id)
    fingerprints = registry.get("fingerprints", {})

    severity_weights = {"critical": 6, "high": 2, "medium": 0.3, "low": 0}
    base_severity = 0.0
    weighted_severity = 0.0

    for event in drift_events:
        sev = event.get("severity", "low")
        base = severity_weights.get(sev, 0)
        base_severity += base

        fp = event.get("fingerprint") or event.get("category", "unknown")
        multiplier = fingerprints.get(fp, {}).get("severity_weight", 1.0)
        weighted_severity += base * multiplier

    # Top fingerprints by recurrence
    sorted_fps = sorted(
        fingerprints.items(),
        key=lambda x: x[1].get("count_24h", 0),
        reverse=True,
    )
    top_fps = [
        {"fingerprint": fp, **data}
        for fp, data in sorted_fps[:5]
    ]

    recurrence_multiplier = (
        round(weighted_severity / max(base_severity, 1), 2)
    )

    return {
        "total_events": len(drift_events),
        "base_severity": round(base_severity, 2),
        "weighted_severity": round(weighted_severity, 2),
        "recurrence_multiplier": recurrence_multiplier,
        "top_fingerprints": top_fps,
    }
