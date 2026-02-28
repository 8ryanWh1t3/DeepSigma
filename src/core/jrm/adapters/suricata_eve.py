"""Suricata EVE JSON adapter — parse EVE JSONL into JRM events."""

from __future__ import annotations

import json
from typing import Any, Dict

from ..types import EventType, JRMEvent, Severity
from .base import AdapterBase

# Map Suricata event_type to JRM EventType
_EVE_TYPE_MAP: Dict[str, EventType] = {
    "alert": EventType.SURICATA_ALERT,
    "dns": EventType.SURICATA_DNS,
    "http": EventType.SURICATA_HTTP,
    "flow": EventType.SURICATA_FLOW,
}

# Map Suricata severity (1=highest) to JRM Severity
_SEVERITY_MAP: Dict[int, Severity] = {
    1: Severity.CRITICAL,
    2: Severity.HIGH,
    3: Severity.MEDIUM,
    4: Severity.LOW,
}


class SuricataEVEAdapter(AdapterBase):
    """Parse Suricata EVE JSON lines into normalized JRM events."""

    source_system = "suricata"

    def parse_line(self, line: str, line_number: int = 0) -> JRMEvent | None:
        if not line.strip():
            return None

        try:
            record: Dict[str, Any] = json.loads(line)
        except (json.JSONDecodeError, ValueError) as exc:
            return self._make_malformed(line, line_number, str(exc))

        eve_type = record.get("event_type", "generic")
        event_type = _EVE_TYPE_MAP.get(eve_type, EventType.GENERIC)

        # Extract alert-specific fields
        alert = record.get("alert", {})
        sig_id = alert.get("signature_id", "")
        sig_rev = alert.get("rev", "")
        sig_severity = alert.get("severity", 4)
        signature = alert.get("signature", "")

        severity = _SEVERITY_MAP.get(sig_severity, Severity.INFO)
        if event_type != EventType.SURICATA_ALERT:
            severity = Severity.INFO

        # Build actor/object from src/dest
        src_ip = record.get("src_ip", "unknown")
        dest_ip = record.get("dest_ip", "unknown")
        src_port = record.get("src_port")
        dest_port = record.get("dest_port")

        actor: Dict[str, Any] = {"type": "host", "id": src_ip, "ip": src_ip}
        if src_port is not None:
            actor["port"] = src_port

        obj: Dict[str, Any] = {"type": "host", "id": dest_ip, "ip": dest_ip}
        if dest_port is not None:
            obj["port"] = dest_port

        # Confidence heuristic: higher severity = higher confidence
        confidence = {
            Severity.CRITICAL: 0.95,
            Severity.HIGH: 0.85,
            Severity.MEDIUM: 0.65,
            Severity.LOW: 0.40,
            Severity.INFO: 0.20,
        }.get(severity, 0.5)

        raw_hash = self.hash_raw(line)
        timestamp = record.get("timestamp", "")

        # Build action string
        if event_type == EventType.SURICATA_ALERT:
            action = f"alert:sid={sig_id}:rev={sig_rev}"
        else:
            action = f"{eve_type}"

        # Collect metadata
        metadata: Dict[str, Any] = {}
        if sig_id:
            metadata["signature_id"] = sig_id
        if sig_rev:
            metadata["rev"] = sig_rev
        if signature:
            metadata["signature"] = signature
        flow_id = record.get("flow_id")
        if flow_id is not None:
            metadata["flow_id"] = flow_id
        proto = record.get("proto")
        if proto:
            metadata["proto"] = proto
        # Preserve additional fields
        for key in ("dns", "http", "tls", "fileinfo", "app_proto"):
            if key in record:
                metadata[key] = record[key]

        return JRMEvent(
            event_id=self._generate_event_id("SURI"),
            source_system=self.source_system,
            event_type=event_type,
            timestamp=timestamp,
            severity=severity,
            actor=actor,
            object=obj,
            action=action,
            confidence=confidence,
            evidence_hash=raw_hash,
            raw_pointer=f"inline:{raw_hash}",
            environment_id=self.default_environment_id,
            assumptions=[],
            raw_bytes=line.encode("utf-8", errors="replace"),
            metadata=metadata,
        )
