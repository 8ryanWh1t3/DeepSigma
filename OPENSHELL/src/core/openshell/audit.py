"""Normalize OpenShell OCSF/log events for CERPA and VINCULUM replay."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from core.cerpa.models import Event

from .models import OpenShellAuditEvent


def normalize_ocsf_event(raw: Dict[str, Any], *, sandbox_name: str = "") -> OpenShellAuditEvent:
    """Best-effort normalization of an OpenShell OCSF JSON record.

    OpenShell's OCSF export is richer than this projection.  The raw record is
    always preserved so no evidence is lost if upstream field names evolve.
    """
    ts = _first(raw, "time", "timestamp", "event_time", "metadata.logged_time")
    if ts is None:
        ts = datetime.now(timezone.utc).isoformat()
    else:
        ts = str(ts)

    decision = str(_first(raw, "decision", "disposition", "status", "policy.decision") or "UNKNOWN")
    action = str(_first(raw, "activity_name", "activity", "action", "event_name", "message") or "runtime_event")
    binary = str(_first(raw, "process.file.path", "process.executable", "binary", "process.name") or "")
    host = str(_first(raw, "dst_endpoint.hostname", "destination.hostname", "host", "http_request.url.hostname") or "")
    port_raw = _first(raw, "dst_endpoint.port", "destination.port", "port")
    try:
        port = int(port_raw) if port_raw is not None else None
    except (TypeError, ValueError):
        port = None
    method = str(_first(raw, "http_request.http_method", "http.method", "method") or "")
    path = str(_first(raw, "http_request.url.path", "http.path", "path") or "")
    rule = str(_first(raw, "policy.rule", "policy_name", "rule") or "")
    reason = str(_first(raw, "status_detail", "policy.reason", "reason", "message") or "")
    sandbox = sandbox_name or str(_first(raw, "sandbox", "sandbox_name", "metadata.sandbox") or "")

    return OpenShellAuditEvent(
        event_id=f"OSEVT-{uuid.uuid4().hex[:12]}",
        timestamp=ts,
        sandbox_name=sandbox,
        decision=decision,
        action=action,
        binary=binary,
        host=host,
        port=port,
        method=method,
        path=path,
        rule=rule,
        reason=reason,
        raw=dict(raw),
    )


def to_cerpa_event(event: OpenShellAuditEvent, *, contract_id: str = "", episode_id: str = "") -> Event:
    """Project an OpenShell runtime event into the CERPA Event primitive."""
    target = event.host
    if event.port:
        target = f"{target}:{event.port}" if target else str(event.port)
    request = " ".join(x for x in [event.method, event.path] if x)
    text = f"OpenShell {event.decision}: {event.action}"
    if target:
        text += f" -> {target}"
    if request:
        text += f" ({request})"

    return Event(
        id=event.event_id,
        text=text,
        domain="authorityops",
        source="openshell",
        timestamp=event.timestamp,
        observed_state={
            "status": "violated" if event.denied else "observed",
            "decision": event.decision,
            "sandbox": event.sandbox_name,
            "host": event.host,
            "port": event.port,
            "method": event.method,
            "path": event.path,
            "binary": event.binary,
            "rule": event.rule,
        },
        related_ids=[x for x in [contract_id, episode_id] if x],
        metadata={
            "violation": event.denied,
            "violation_detail": event.reason if event.denied else "",
            "raw_ocsf": event.raw,
        },
    )


def to_vinculum_event(event: OpenShellAuditEvent, *, contract_hash: str = "", policy_hash: str = "") -> Dict[str, Any]:
    """Produce a replay-safe VINCULUM event projection."""
    return {
        "kind": "openshell_runtime_event",
        "event_id": event.event_id,
        "timestamp": event.timestamp,
        "sandbox": event.sandbox_name,
        "decision": event.decision,
        "action": event.action,
        "resource": {
            "host": event.host,
            "port": event.port,
            "method": event.method,
            "path": event.path,
        },
        "binary": event.binary,
        "rule": event.rule,
        "reason": event.reason,
        "contract_hash": contract_hash,
        "policy_hash": policy_hash,
        "source": "openshell",
    }


def normalize_ocsf_stream(records: Iterable[Dict[str, Any]], *, sandbox_name: str = "") -> List[OpenShellAuditEvent]:
    return [normalize_ocsf_event(r, sandbox_name=sandbox_name) for r in records]


def _first(data: Dict[str, Any], *paths: str) -> Any:
    for path in paths:
        current: Any = data
        ok = True
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                ok = False
                break
            current = current[part]
        if ok and current is not None:
            return current
    return None


__all__ = [
    "normalize_ocsf_event",
    "normalize_ocsf_stream",
    "to_cerpa_event",
    "to_vinculum_event",
]
