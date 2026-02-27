"""Per-topic payload extractors for FEEDS ingest.

Each function takes a packet manifest dict and the packet directory,
returning a schema-valid payload dict for its topic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def extract_truth_snapshot(packet_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Extract truth snapshot payload from packet artifacts."""
    ts_file = packet_dir / "truth_snapshot.json"
    if ts_file.exists():
        return json.loads(ts_file.read_text(encoding="utf-8"))
    return manifest.get("truthSnapshot", {})


def extract_authority_slice(packet_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Extract authority slice payload from packet artifacts."""
    als_file = packet_dir / "authority_slice.json"
    if als_file.exists():
        return json.loads(als_file.read_text(encoding="utf-8"))
    return manifest.get("authoritySlice", {})


def extract_decision_lineage(packet_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Extract decision lineage payload from packet artifacts."""
    dlr_file = packet_dir / "decision_lineage.json"
    if dlr_file.exists():
        return json.loads(dlr_file.read_text(encoding="utf-8"))
    return manifest.get("decisionLineage", {})


def extract_drift_signal(packet_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Extract drift signal payload from packet artifacts."""
    ds_file = packet_dir / "drift_signal.json"
    if ds_file.exists():
        return json.loads(ds_file.read_text(encoding="utf-8"))
    return manifest.get("driftSignal", {})


def extract_canon_entry(packet_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Extract canon entry payload from packet artifacts."""
    ce_file = packet_dir / "canon_entry.json"
    if ce_file.exists():
        return json.loads(ce_file.read_text(encoding="utf-8"))
    return manifest.get("canonEntry", {})


def extract_packet_index(packet_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Extract packet index payload — typically the manifest itself."""
    return manifest.get("packetIndex", manifest)


# Topic -> extractor function mapping
EXTRACTORS: Dict[str, Any] = {
    "truth_snapshot": extract_truth_snapshot,
    "authority_slice": extract_authority_slice,
    "decision_lineage": extract_decision_lineage,
    "drift_signal": extract_drift_signal,
    "canon_entry": extract_canon_entry,
    "packet_index": extract_packet_index,
}
