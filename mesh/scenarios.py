"""Mesh Scenarios — 4-phase scenario controller.

Phase 0: Healthy — all regions online, low correlation, claims VERIFIED
Phase 1: Partition — region B offline, quorum compression, claim → UNKNOWN
Phase 2: Correlated Failure — region C correlation INVALID, claim → DEGRADED
Phase 3: Recovery — patch event, claims recover

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from mesh.logstore import append_jsonl
from mesh.node_runtime import MeshNode, NodeRole
from mesh.transport import REPLICATION_LOG


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class MeshScenario:
    """Manages a set of mesh nodes through scenario phases."""

    tenant_id: str
    nodes: list[MeshNode] = field(default_factory=list)
    phase: int = -1
    events: list[dict] = field(default_factory=list)

    def init_nodes(self) -> list[dict]:
        """Initialize standard 3-region mesh topology.

        Region A: edge-A, aggregator-A, seal-A
        Region B: validator-B, edge-B
        Region C: edge-C, validator-C
        """
        # Determine all node IDs for peer lists
        all_ids = [
            "edge-A", "aggregator-A", "seal-A",
            "validator-B", "edge-B",
            "edge-C", "validator-C",
        ]

        def peers_for(nid: str) -> list[str]:
            return [p for p in all_ids if p != nid]

        self.nodes = [
            # Region A
            MeshNode(
                node_id="edge-A",
                tenant_id=self.tenant_id,
                region_id="region-A",
                role=NodeRole.EDGE,
                peers=peers_for("edge-A"),
            ),
            MeshNode(
                node_id="aggregator-A",
                tenant_id=self.tenant_id,
                region_id="region-A",
                role=NodeRole.AGGREGATOR,
                peers=peers_for("aggregator-A"),
            ),
            MeshNode(
                node_id="seal-A",
                tenant_id=self.tenant_id,
                region_id="region-A",
                role=NodeRole.SEAL_AUTHORITY,
                peers=peers_for("seal-A"),
            ),
            # Region B
            MeshNode(
                node_id="validator-B",
                tenant_id=self.tenant_id,
                region_id="region-B",
                role=NodeRole.VALIDATOR,
                peers=peers_for("validator-B"),
            ),
            MeshNode(
                node_id="edge-B",
                tenant_id=self.tenant_id,
                region_id="region-B",
                role=NodeRole.EDGE,
                peers=peers_for("edge-B"),
            ),
            # Region C
            MeshNode(
                node_id="edge-C",
                tenant_id=self.tenant_id,
                region_id="region-C",
                role=NodeRole.EDGE,
                peers=peers_for("edge-C"),
            ),
            MeshNode(
                node_id="validator-C",
                tenant_id=self.tenant_id,
                region_id="region-C",
                role=NodeRole.VALIDATOR,
                peers=peers_for("validator-C"),
            ),
        ]

        summaries = []
        for n in self.nodes:
            summaries.append({
                "node_id": n.node_id,
                "region_id": n.region_id,
                "role": n.role.value,
            })
        return summaries

    def run_phase(self, phase: int, cycles: int = 3) -> list[dict]:
        """Run a specific scenario phase for N cycles.

        Returns list of cycle results.
        """
        self.phase = phase
        results = []

        # Clear evidence logs so each phase starts fresh
        # (replication + seal chain persist for continuity)
        self._clear_evidence_logs()

        if phase == 0:
            self._apply_phase_healthy()
        elif phase == 1:
            self._apply_phase_partition()
        elif phase == 2:
            self._apply_phase_correlated_failure()
        elif phase == 3:
            self._apply_phase_recovery()

        # Log phase event
        event = {
            "type": "PHASE_CHANGE",
            "phase": phase,
            "phase_name": _phase_name(phase),
            "timestamp": _now_iso(),
        }
        self.events.append(event)
        self._log_scenario_event(event)

        # Run cycles
        for cycle in range(cycles):
            cycle_results = self._run_one_cycle()
            results.append({
                "phase": phase,
                "cycle": cycle,
                "node_results": cycle_results,
            })
            time.sleep(0.05)  # small delay between cycles

        return results

    def run_all_phases(self, cycles_per_phase: int = 3) -> dict[str, Any]:
        """Run all 4 phases sequentially.

        Returns complete scenario report.
        """
        report: dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "started_at": _now_iso(),
            "phases": {},
        }

        for phase in range(4):
            phase_results = self.run_phase(phase, cycles=cycles_per_phase)
            report["phases"][_phase_name(phase)] = {
                "phase": phase,
                "cycles": len(phase_results),
                "results": phase_results,
            }

        report["completed_at"] = _now_iso()
        report["total_events"] = len(self.events)
        return report

    # -------------------------------------------------------------------
    # Phase implementations
    # -------------------------------------------------------------------

    def _apply_phase_healthy(self) -> None:
        """Phase 0: All nodes online, no forced correlation."""
        for n in self.nodes:
            n.offline = False
            n.force_correlation = None

    def _apply_phase_partition(self) -> None:
        """Phase 1: Region B goes offline."""
        for n in self.nodes:
            if n.region_id == "region-B":
                n.offline = True
            else:
                n.offline = False
                n.force_correlation = None

    def _apply_phase_correlated_failure(self) -> None:
        """Phase 2: Region C has high correlation (INVALID).

        Region B remains offline from phase 1.
        """
        for n in self.nodes:
            if n.region_id == "region-B":
                n.offline = True
            elif n.region_id == "region-C":
                n.offline = False
                n.force_correlation = 0.95  # force high correlation
            else:
                n.offline = False
                n.force_correlation = None

    def _apply_phase_recovery(self) -> None:
        """Phase 3: All regions back online, correlation normalized."""
        for n in self.nodes:
            n.offline = False
            n.force_correlation = None

        # Log patch event
        event = {
            "type": "PATCH_APPLIED",
            "description": "Region B restored, Region C correlation normalized",
            "timestamp": _now_iso(),
        }
        self.events.append(event)
        self._log_scenario_event(event)

    # -------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------

    def _clear_evidence_logs(self) -> None:
        """Clear envelope, validation, and aggregate logs for a fresh phase.

        Seal chain and replication logs persist for continuity.
        """
        from mesh.transport import AGGREGATES_LOG, ENVELOPES_LOG, VALIDATIONS_LOG
        for n in self.nodes:
            for log_name in [ENVELOPES_LOG, VALIDATIONS_LOG, AGGREGATES_LOG]:
                path = n._data_dir() / log_name
                if path.exists():
                    path.unlink()

    def _run_one_cycle(self) -> list[dict]:
        """Run one tick on each node in order: edge → validator → aggregator → seal."""
        results = []

        # Edges first (generate evidence)
        for n in self.nodes:
            if n.role == NodeRole.EDGE:
                results.append(n.tick())

        # Validators second (validate evidence)
        for n in self.nodes:
            if n.role == NodeRole.VALIDATOR:
                results.append(n.tick())

        # Aggregators third (compute federated state)
        for n in self.nodes:
            if n.role == NodeRole.AGGREGATOR:
                results.append(n.tick())

        # Seal authorities last (seal aggregates)
        for n in self.nodes:
            if n.role == NodeRole.SEAL_AUTHORITY:
                results.append(n.tick())

        return results

    def _log_scenario_event(self, event: dict) -> None:
        """Log scenario event to all node replication logs."""
        for n in self.nodes:
            if not n.offline:
                path = n._data_dir() / REPLICATION_LOG
                append_jsonl(path, event)


def _phase_name(phase: int) -> str:
    names = {
        0: "healthy",
        1: "partition",
        2: "correlated_failure",
        3: "recovery",
    }
    return names.get(phase, f"phase_{phase}")
