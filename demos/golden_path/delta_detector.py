"""DeltaDriftDetector — compare baseline vs delta record sets to emit drift events."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _content_hash(record: Dict[str, Any]) -> str:
    """Hash the content portion of a canonical record."""
    content = record.get("content", {})
    raw = json.dumps(content, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class DeltaDriftDetector:
    """Compare two snapshots of canonical records to produce drift events."""

    def detect(
        self,
        baseline: List[Dict[str, Any]],
        delta: List[Dict[str, Any]],
        episode_id: str = "unknown",
    ) -> List[Dict[str, Any]]:
        baseline_index = {r["record_id"]: r for r in baseline}
        delta_index = {r["record_id"]: r for r in delta}

        drift_events: List[Dict[str, Any]] = []
        seq = 0

        # New records in delta
        for rid, record in delta_index.items():
            if rid not in baseline_index:
                seq += 1
                drift_events.append(self._make_drift(
                    seq=seq,
                    episode_id=episode_id,
                    kind="new_evidence",
                    severity="yellow",
                    description=f"New record appeared: {rid[:12]}",
                    fingerprint_key=f"new:{rid[:12]}",
                ))

        # Changed records
        for rid, delta_rec in delta_index.items():
            if rid in baseline_index:
                base_rec = baseline_index[rid]
                base_hash = _content_hash(base_rec)
                delta_hash = _content_hash(delta_rec)

                if base_hash != delta_hash:
                    base_conf = _get_confidence(base_rec)
                    delta_conf = _get_confidence(delta_rec)
                    severity = "red" if delta_conf < base_conf else "yellow"

                    seq += 1
                    drift_events.append(self._make_drift(
                        seq=seq,
                        episode_id=episode_id,
                        kind="evidence_changed",
                        severity=severity,
                        description=f"Record {rid[:12]} content changed"
                            + (f" (confidence {base_conf:.2f}→{delta_conf:.2f})" if delta_conf != base_conf else ""),
                        fingerprint_key=f"changed:{rid[:12]}",
                    ))

        # Removed records
        for rid in baseline_index:
            if rid not in delta_index:
                seq += 1
                drift_events.append(self._make_drift(
                    seq=seq,
                    episode_id=episode_id,
                    kind="evidence_removed",
                    severity="red",
                    description=f"Record removed: {rid[:12]}",
                    fingerprint_key=f"removed:{rid[:12]}",
                ))

        # Freshness violations (TTL expired in delta)
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        for rid, record in delta_index.items():
            ttl = record.get("ttl", 0)
            if ttl <= 0:
                continue
            observed = record.get("observed_at", "")
            if not observed:
                continue
            try:
                clean = observed.replace("Z", "+00:00")
                obs_ms = int(datetime.fromisoformat(clean).timestamp() * 1000)
            except (ValueError, TypeError):
                continue
            age_ms = now_ms - obs_ms
            if age_ms > ttl:
                severity = "red" if age_ms > ttl * 2 else "yellow"
                seq += 1
                drift_events.append(self._make_drift(
                    seq=seq,
                    episode_id=episode_id,
                    kind="freshness",
                    severity=severity,
                    description=f"Record {rid[:12]} past TTL ({age_ms}ms > {ttl}ms)",
                    fingerprint_key=f"freshness:{rid[:12]}",
                ))

        return drift_events

    def _make_drift(
        self,
        seq: int,
        episode_id: str,
        kind: str,
        severity: str,
        description: str,
        fingerprint_key: str,
    ) -> Dict[str, Any]:
        return {
            "driftId": f"drift-gp-{seq:03d}",
            "episodeId": episode_id,
            "detectedAt": _now_iso(),
            "driftType": kind,
            "kind": kind,
            "severity": severity,
            "fingerprint": {"key": fingerprint_key},
            "description": description,
            "recommendedPatchType": _recommend_patch(kind),
        }


def _get_confidence(record: Dict[str, Any]) -> float:
    conf = record.get("confidence", {})
    if isinstance(conf, dict):
        return conf.get("score", 0.5)
    if isinstance(conf, (int, float)):
        return float(conf)
    return 0.5


def _recommend_patch(kind: str) -> str:
    return {
        "new_evidence": "REPLAN",
        "evidence_changed": "RETCON",
        "evidence_removed": "ROLLBACK",
        "freshness": "RETCON",
    }.get(kind, "RETCON")
