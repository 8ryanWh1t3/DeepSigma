"""Snort fast.log adapter — best-effort parse common fast.log variants."""

from __future__ import annotations

import re
from typing import Any, Dict

from ..types import EventType, JRMEvent, Severity
from .base import AdapterBase

# Common Snort fast.log pattern:
# MM/DD-HH:MM:SS.USEC  [**] [GID:SID:REV] MESSAGE [**] [Classification: ...] [Priority: N] {PROTO} SRC:PORT -> DST:PORT
_FAST_LOG_RE = re.compile(
    r"^(?P<ts>\d{2}/\d{2}-\d{2}:\d{2}:\d{2}\.\d+)\s+"
    r"\[\*\*\]\s+"
    r"\[(?P<gid>\d+):(?P<sid>\d+):(?P<rev>\d+)\]\s+"
    r"(?P<msg>.+?)\s+"
    r"\[\*\*\]"
    r"(?:\s+\[Classification:\s*(?P<classtype>[^\]]*)\])?"
    r"(?:\s+\[Priority:\s*(?P<priority>\d+)\])?"
    r"(?:\s+\{(?P<proto>[^}]+)\})?"
    r"(?:\s+(?P<src>[^\s]+)\s*->\s*(?P<dst>[^\s]+))?"
)

# Map Snort priority to JRM Severity
_PRIORITY_MAP: Dict[int, Severity] = {
    1: Severity.CRITICAL,
    2: Severity.HIGH,
    3: Severity.MEDIUM,
    4: Severity.LOW,
}


def _parse_host_port(addr: str) -> tuple[str, int | None]:
    """Split 'IP:PORT' or just 'IP' into (ip, port|None)."""
    if not addr:
        return ("unknown", None)
    if ":" in addr:
        parts = addr.rsplit(":", 1)
        try:
            return (parts[0], int(parts[1]))
        except ValueError:
            return (addr, None)
    return (addr, None)


class SnortFastlogAdapter(AdapterBase):
    """Parse Snort fast.log lines into normalized JRM events."""

    source_system = "snort"

    def parse_line(self, line: str, line_number: int = 0) -> JRMEvent | None:
        if not line.strip():
            return None

        match = _FAST_LOG_RE.match(line)
        if not match:
            return self._make_malformed(line, line_number, "no regex match")

        ts_raw = match.group("ts")
        gid = match.group("gid")
        sid = match.group("sid")
        rev = match.group("rev")
        msg = match.group("msg").strip()
        classtype = (match.group("classtype") or "").strip()
        priority = int(match.group("priority") or "4")
        proto = (match.group("proto") or "").strip()
        src_raw = (match.group("src") or "").strip()
        dst_raw = (match.group("dst") or "").strip()

        severity = _PRIORITY_MAP.get(priority, Severity.LOW)

        src_ip, src_port = _parse_host_port(src_raw)
        dst_ip, dst_port = _parse_host_port(dst_raw)

        actor: Dict[str, Any] = {"type": "host", "id": src_ip, "ip": src_ip}
        if src_port is not None:
            actor["port"] = src_port

        obj: Dict[str, Any] = {"type": "host", "id": dst_ip, "ip": dst_ip}
        if dst_port is not None:
            obj["port"] = dst_port

        confidence = {
            Severity.CRITICAL: 0.95,
            Severity.HIGH: 0.85,
            Severity.MEDIUM: 0.65,
            Severity.LOW: 0.40,
        }.get(severity, 0.5)

        raw_hash = self.hash_raw(line)

        metadata: Dict[str, Any] = {
            "gid": gid,
            "sid": sid,
            "rev": rev,
            "message": msg,
        }
        if classtype:
            metadata["classtype"] = classtype
        if proto:
            metadata["proto"] = proto

        return JRMEvent(
            event_id=self._generate_event_id("SNRT"),
            source_system=self.source_system,
            event_type=EventType.SNORT_ALERT,
            timestamp=ts_raw,
            severity=severity,
            actor=actor,
            object=obj,
            action=f"alert:sid={sid}:rev={rev}",
            confidence=confidence,
            evidence_hash=raw_hash,
            raw_pointer=f"inline:{raw_hash}",
            environment_id=self.default_environment_id,
            assumptions=[],
            raw_bytes=line.encode("utf-8", errors="replace"),
            metadata=metadata,
        )
