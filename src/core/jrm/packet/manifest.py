"""Packet manifest builder — per-file sha256 hashes."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Dict

from ..types import PacketManifest


def compute_file_hash(content: bytes) -> str:
    """SHA-256 hash of file content in ``sha256:<hex>`` format."""
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def build_manifest(
    packet_name: str,
    files_content: Dict[str, bytes],
    environment_id: str,
    window_start: str,
    window_end: str,
    part: int,
    event_count: int,
) -> PacketManifest:
    """Build a PacketManifest with per-file sha256 hashes."""
    file_hashes: Dict[str, str] = {}
    total_size = 0
    for fname, content in files_content.items():
        file_hashes[fname] = compute_file_hash(content)
        total_size += len(content)

    return PacketManifest(
        packet_name=packet_name,
        environment_id=environment_id,
        window_start=window_start,
        window_end=window_end,
        part=part,
        files=file_hashes,
        event_count=event_count,
        size_bytes=total_size,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
