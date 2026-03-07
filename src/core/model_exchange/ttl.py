"""TTL helpers — extract or compute time-to-live from packets."""

from __future__ import annotations

from typing import Any, Dict, Optional


def ttl_from_packet(packet: Dict[str, Any]) -> Optional[str]:
    """Extract a TTL string from a packet if present."""
    ttl = packet.get("ttl")
    if ttl is not None:
        return str(ttl)
    return None


def compute_claim_ttl_seconds(packet: Dict[str, Any]) -> Optional[int]:
    """Compute a TTL in seconds from the packet, or None if unspecified.

    Prefers packet-level ``ttl`` (int seconds).  If absent, returns None
    instead of inventing policy.
    """
    ttl = packet.get("ttl")
    if isinstance(ttl, int) and ttl > 0:
        return ttl
    if isinstance(ttl, str):
        try:
            val = int(ttl)
            if val > 0:
                return val
        except ValueError:
            pass
    return None
