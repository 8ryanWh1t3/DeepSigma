"""JRM Hub — merge packets from multiple environments, detect cross-env drift."""

from __future__ import annotations

import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ..types import CrossEnvDrift, CrossEnvDriftType


class JRMHub:
    """Ingest multiple JRM-X packets and detect cross-environment drift."""

    def __init__(self) -> None:
        self._packets: Dict[str, Dict[str, Any]] = {}  # env -> merged state
        self._all_manifests: List[Dict[str, Any]] = []

    def ingest(self, packets: List[str | Path]) -> None:
        """Load and parse packets, grouped by environment."""
        for p in packets:
            p = Path(p)
            try:
                with zipfile.ZipFile(p, "r") as zf:
                    manifest = json.loads(zf.read("manifest.json"))
                    env = manifest.get("environmentId", "unknown")
                    self._all_manifests.append(manifest)

                    ce = json.loads(zf.read("canon_entry.json"))
                    mg = json.loads(zf.read("memory_graph.json"))
                    ds_raw = zf.read("drift_signal.jsonl").decode("utf-8")
                    ds = [json.loads(l) for l in ds_raw.strip().split("\n") if l.strip()]

                    if env not in self._packets:
                        self._packets[env] = {
                            "canon_entries": {},
                            "mg_nodes": [],
                            "mg_edges": [],
                            "drift_signals": [],
                            "manifests": [],
                        }

                    state = self._packets[env]
                    state["canon_entries"].update(ce.get("entries", {}))
                    state["mg_nodes"].extend(mg.get("nodesAdded", []))
                    state["mg_edges"].extend(mg.get("edgesAdded", []))
                    state["drift_signals"].extend(ds)
                    state["manifests"].append(manifest)

            except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as e:
                pass  # Skip invalid packets silently

    def detect_drift(self) -> List[CrossEnvDrift]:
        """Detect cross-environment drift across ingested packets."""
        drifts: List[CrossEnvDrift] = []
        envs = list(self._packets.keys())
        if len(envs) < 2:
            return drifts

        drifts.extend(self._detect_version_skew(envs))
        drifts.extend(self._detect_posture_divergence(envs))
        return drifts

    def merge_memory_graphs(self) -> Dict[str, Any]:
        """Merge MG deltas from all environments into global state."""
        all_nodes: List[Dict[str, Any]] = []
        all_edges: List[Dict[str, Any]] = []
        for env, state in self._packets.items():
            for node in state["mg_nodes"]:
                node["environmentId"] = env
                all_nodes.append(node)
            for edge in state["mg_edges"]:
                edge["environmentId"] = env
                all_edges.append(edge)
        return {
            "globalNodes": all_nodes,
            "globalEdges": all_edges,
            "environments": list(self._packets.keys()),
            "mergedAt": datetime.now(timezone.utc).isoformat(),
        }

    def produce_report(self) -> Dict[str, Any]:
        """Produce a federation report."""
        drifts = self.detect_drift()
        mg = self.merge_memory_graphs()
        return {
            "environments": list(self._packets.keys()),
            "packetsIngested": len(self._all_manifests),
            "crossEnvDrifts": [
                {
                    "driftId": d.drift_id,
                    "driftType": d.drift_type.value,
                    "severity": d.severity,
                    "environments": d.environments,
                    "signatureId": d.signature_id,
                    "detail": d.detail,
                }
                for d in drifts
            ],
            "mergedGraph": mg,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }

    # ── Drift detectors ──────────────────────────────────────────

    def _detect_version_skew(self, envs: List[str]) -> List[CrossEnvDrift]:
        """Same signature, different active rev across environments."""
        # Collect rev per signature per env from patches in canon entries
        sig_revs: Dict[str, Dict[str, set]] = {}  # sig -> {env -> {revs}}

        for env in envs:
            state = self._packets[env]
            for key, entry in state["canon_entries"].items():
                rev = entry.get("rev")
                if rev is not None:
                    # Try to extract signature from patch detail or key
                    sig = str(key)
                    sig_revs.setdefault(sig, {}).setdefault(env, set()).add(str(rev))

        results: List[CrossEnvDrift] = []
        for sig, env_revs in sig_revs.items():
            if len(env_revs) >= 2:
                all_revs = set()
                for revs in env_revs.values():
                    all_revs.update(revs)
                if len(all_revs) > 1:
                    results.append(CrossEnvDrift(
                        drift_id=f"XDS-{uuid.uuid4().hex[:12]}",
                        drift_type=CrossEnvDriftType.VERSION_SKEW,
                        severity="medium",
                        environments=list(env_revs.keys()),
                        signature_id=sig,
                        detail=f"Revisions: {dict((e, sorted(r)) for e, r in env_revs.items())}",
                    ))
        return results

    def _detect_posture_divergence(self, envs: List[str]) -> List[CrossEnvDrift]:
        """Same key, different posture/confidence across environments."""
        key_values: Dict[str, Dict[str, Any]] = {}  # key -> {env -> value}

        for env in envs:
            state = self._packets[env]
            for key, entry in state["canon_entries"].items():
                conf = entry.get("confidence")
                if conf is not None:
                    key_values.setdefault(key, {})[env] = conf

        results: List[CrossEnvDrift] = []
        for key, env_confs in key_values.items():
            if len(env_confs) >= 2:
                values = list(env_confs.values())
                if max(values) - min(values) > 0.3:
                    results.append(CrossEnvDrift(
                        drift_id=f"XDS-{uuid.uuid4().hex[:12]}",
                        drift_type=CrossEnvDriftType.POSTURE_DIVERGENCE,
                        severity="high",
                        environments=list(env_confs.keys()),
                        detail=f"Key {key} confidence diverges: {env_confs}",
                    ))
        return results
