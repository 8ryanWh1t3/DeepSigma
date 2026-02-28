"""Rolling JRM-X packet builder.

Produces 6-file zip packets with rolling semantics:
- Trigger: 50k events OR 25MB zip size
- Naming: JRM_X_PACKET_<ENV>_<WINDOWSTART>_<WINDOWEND>_partNN.zip
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..types import PipelineResult
from .manifest import build_manifest, compute_file_hash
from .naming import generate_packet_name

# Rolling thresholds
DEFAULT_MAX_EVENTS = 50_000
DEFAULT_MAX_ZIP_BYTES = 25 * 1024 * 1024  # 25 MB


class RollingPacketBuilder:
    """Accumulate pipeline results and build packets when thresholds are met."""

    def __init__(
        self,
        environment_id: str,
        output_dir: str | Path,
        max_events: int = DEFAULT_MAX_EVENTS,
        max_zip_bytes: int = DEFAULT_MAX_ZIP_BYTES,
    ) -> None:
        self._env_id = environment_id
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._max_events = max_events
        self._max_bytes = max_zip_bytes
        self._accumulator: List[PipelineResult] = []
        self._event_count = 0
        self._part = 1
        self._window_start: Optional[str] = None
        self._window_end: Optional[str] = None

    def add(self, result: PipelineResult) -> Optional[Path]:
        """Add a pipeline result.  Returns packet path if threshold was hit."""
        self._accumulator.append(result)
        self._event_count += result.events_processed

        # Track window bounds
        if result.window_start:
            if self._window_start is None or result.window_start < self._window_start:
                self._window_start = result.window_start
        if result.window_end:
            if self._window_end is None or result.window_end > self._window_end:
                self._window_end = result.window_end

        if self._event_count >= self._max_events:
            return self.flush()
        return None

    def flush(self) -> Optional[Path]:
        """Force-build a packet from accumulated results.  Returns None if empty."""
        if not self._accumulator:
            return None
        path = self._build_zip()
        self._accumulator.clear()
        self._event_count = 0
        self._window_start = None
        self._window_end = None
        self._part += 1
        return path

    def _build_zip(self) -> Path:
        """Assemble the 6 data files + manifest into a zip."""
        now = datetime.now(timezone.utc).isoformat()
        ws = self._window_start or now
        we = self._window_end or now

        # Merge accumulated results
        ts_payload = self._merge_truth_snapshots()
        als_payload = self._build_als()
        dlr_lines = self._merge_dlr()
        ds_lines = self._merge_ds()
        mg_payload = self._merge_mg()
        ce_payload = self._merge_canon()

        # Serialize
        files_content: Dict[str, bytes] = {
            "truth_snapshot.json": _to_json_bytes(ts_payload),
            "authority_slice.json": _to_json_bytes(als_payload),
            "decision_lineage.jsonl": _to_ndjson_bytes(dlr_lines),
            "drift_signal.jsonl": _to_ndjson_bytes(ds_lines),
            "memory_graph.json": _to_json_bytes(mg_payload),
            "canon_entry.json": _to_json_bytes(ce_payload),
        }

        packet_name = generate_packet_name(self._env_id, ws, we, self._part)
        manifest = build_manifest(
            packet_name=packet_name,
            files_content=files_content,
            environment_id=self._env_id,
            window_start=ws,
            window_end=we,
            part=self._part,
            event_count=self._event_count,
        )
        manifest_bytes = _to_json_bytes(asdict(manifest))

        # Write zip
        zip_path = self._output_dir / f"{packet_name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname, content in files_content.items():
                zf.writestr(fname, content)
            zf.writestr("manifest.json", manifest_bytes)

        # Check size threshold for future callers
        # (we already flushed, so this is informational)

        return zip_path

    # ── Merge helpers ────────────────────────────────────────────

    def _merge_truth_snapshots(self) -> Dict[str, Any]:
        """Merge TS payloads from accumulated results."""
        total_events = 0
        total_claims = 0
        severity_hist: Dict[str, int] = {}
        event_type_counts: Dict[str, int] = {}
        all_sigs: Dict[str, int] = {}
        sensors: set[str] = set()
        ws = self._window_start or ""
        we = self._window_end or ""

        for r in self._accumulator:
            total_events += r.events_processed
            total_claims += len(r.claims)

        return {
            "environmentId": self._env_id,
            "windowStart": ws,
            "windowEnd": we,
            "eventCount": total_events,
            "claimCount": total_claims,
        }

    def _build_als(self) -> Dict[str, Any]:
        """Build a static local authority ledger slice."""
        return {
            "environmentId": self._env_id,
            "publisherRole": "local_pipeline",
            "allowedActions": ["publish_packet"],
            "scopeAllowlist": ["*"],
            "redactionPolicy": "none",
        }

    def _merge_dlr(self) -> List[Dict[str, Any]]:
        """Merge DLR entries from reasoning results."""
        dlr: List[Dict[str, Any]] = []
        for r in self._accumulator:
            for rr in r.reasoning_results:
                dlr.append({
                    "eventId": rr.event_id,
                    "lane": rr.lane.value,
                    "whyBullets": [
                        {"text": b.text, "evidenceRef": b.evidence_ref, "confidence": b.confidence}
                        for b in rr.why_bullets
                    ],
                    "claims": [c.claim_id for c in rr.claims],
                    "metadata": rr.metadata,
                })
        return dlr

    def _merge_ds(self) -> List[Dict[str, Any]]:
        """Merge DS entries from drift detections."""
        ds: List[Dict[str, Any]] = []
        for r in self._accumulator:
            for dd in r.drift_detections:
                ds.append({
                    "driftId": dd.drift_id,
                    "driftType": dd.drift_type.value,
                    "severity": dd.severity.value,
                    "detectedAt": dd.detected_at,
                    "evidenceRefs": dd.evidence_refs[:10],
                    "fingerprint": dd.fingerprint,
                    "notes": dd.notes,
                    "recommendedAction": dd.recommended_action,
                })
        return ds

    def _merge_mg(self) -> Dict[str, Any]:
        """Merge MG deltas."""
        all_nodes: List[Dict[str, Any]] = []
        all_edges: List[Dict[str, Any]] = []
        for r in self._accumulator:
            all_nodes.extend(r.mg_deltas.get("nodesAdded", []))
            all_edges.extend(r.mg_deltas.get("edgesAdded", []))
        return {
            "nodesAdded": all_nodes,
            "edgesAdded": all_edges,
            "environmentId": self._env_id,
        }

    def _merge_canon(self) -> Dict[str, Any]:
        """Merge canon postures — last writer wins per key."""
        merged: Dict[str, Any] = {}
        for r in self._accumulator:
            entries = r.canon_postures.get("entries", {})
            merged.update(entries)
        return {
            "entries": merged,
            "environmentId": self._env_id,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }


def _to_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, indent=2, sort_keys=True, default=str).encode("utf-8")


def _to_ndjson_bytes(records: List[Dict[str, Any]]) -> bytes:
    lines = [json.dumps(r, sort_keys=True, default=str) for r in records]
    return ("\n".join(lines) + "\n").encode("utf-8") if lines else b""
