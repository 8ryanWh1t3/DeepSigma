"""Governance — Quotas and SLO Telemetry.

Tracks per-tenant operational metrics and enforces quota limits.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BASE_TELEMETRY_DIR = Path(__file__).parent.parent / "data" / "telemetry"
_telemetry_lock = threading.Lock()
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")

# In-memory counters for quota enforcement (reset on process restart)
_quota_counters: dict[str, dict[str, list[float]]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validated_tenant_id(tenant_id: str) -> str:
    if os.path.basename(tenant_id) != tenant_id:
        raise ValueError("Invalid tenant_id")
    if not _SAFE_ID_RE.fullmatch(tenant_id):
        raise ValueError("Invalid tenant_id")
    return tenant_id


def _tenant_slug(tenant_id: str) -> str:
    tid = _validated_tenant_id(tenant_id)
    return hashlib.sha256(tid.encode("utf-8")).hexdigest()[:16]


def _telemetry_path(tenant_id: str) -> Path:
    """Return the telemetry log path for a tenant."""
    base = _BASE_TELEMETRY_DIR.resolve()
    d = (base / _tenant_slug(tenant_id)).resolve()
    if os.path.commonpath([str(base), str(d)]) != str(base):
        raise ValueError("Invalid tenant_id path")
    d.mkdir(parents=True, exist_ok=True)
    path = (d / "telemetry.jsonl").resolve()
    if os.path.commonpath([str(d), str(path)]) != str(d):
        raise ValueError("Invalid telemetry file path")
    return path


def record_metric(
    tenant_id: str,
    metric_name: str,
    value: float,
    actor: str = "system",
) -> dict[str, Any]:
    """Record a telemetry metric for a tenant."""
    record = {
        "tenant_id": tenant_id,
        "metric_name": metric_name,
        "value": value,
        "actor": actor,
        "timestamp": _now_iso(),
    }
    filepath = _telemetry_path(tenant_id)
    with _telemetry_lock:
        with open(filepath, "a", encoding="utf-8") as f:  # lgtm [py/path-injection]
            f.write(json.dumps(record, default=str) + "\n")
    return record


def check_quota(
    tenant_id: str,
    action: str,
    policy: dict[str, Any] | None = None,
) -> bool:
    """Check if a quota allows the action. Returns True if allowed.

    Tracks in-memory counters per tenant/action with 1-hour window.
    """
    if policy is None:
        return True

    quota_policy = policy.get("quota_policy", {})

    # Map action to quota key
    quota_map = {
        "packet_generate": "packets_per_hour",
        "packet_seal": "packets_per_hour",
        "export": "exports_per_day",
    }
    quota_key = quota_map.get(action)
    if not quota_key or quota_key not in quota_policy:
        return True

    limit = quota_policy[quota_key]
    now = time.time()

    # Window: 1 hour for per_hour, 24 hours for per_day
    window = 3600 if "hour" in quota_key else 86400

    # Initialize counters
    if tenant_id not in _quota_counters:
        _quota_counters[tenant_id] = {}
    if action not in _quota_counters[tenant_id]:
        _quota_counters[tenant_id][action] = []

    # Prune old entries
    timestamps = _quota_counters[tenant_id][action]
    _quota_counters[tenant_id][action] = [
        t for t in timestamps if now - t < window
    ]

    # Check
    if len(_quota_counters[tenant_id][action]) >= limit:
        return False

    # Record this action
    _quota_counters[tenant_id][action].append(now)
    return True


def load_recent_telemetry(
    tenant_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Load the most recent telemetry records for a tenant."""
    filepath = _telemetry_path(tenant_id)
    if not filepath.exists():
        return []
    lines: list[str] = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
    return [json.loads(line) for line in lines[-limit:]]
