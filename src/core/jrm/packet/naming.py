"""Packet naming convention for JRM-X zips."""

from __future__ import annotations

import re


def generate_packet_name(
    environment_id: str,
    window_start: str,
    window_end: str,
    part: int,
) -> str:
    """Generate a JRM-X packet name.

    Format: JRM_X_PACKET_<ENV>_<YYYYMMDDTHHMMSS>_<YYYYMMDDTHHMMSS>_partNN
    """
    ws = _compact_ts(window_start)
    we = _compact_ts(window_end)
    return f"JRM_X_PACKET_{environment_id}_{ws}_{we}_part{part:02d}"


def _compact_ts(ts: str) -> str:
    """Compact an ISO timestamp to YYYYMMDDTHHMMSS."""
    # Strip everything except digits and T
    cleaned = re.sub(r"[^0-9T]", "", ts)
    # Take first 15 chars: YYYYMMDDTHHMMSS
    return cleaned[:15] if len(cleaned) >= 15 else cleaned
