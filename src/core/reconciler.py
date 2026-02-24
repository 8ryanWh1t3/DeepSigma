"""Reconciler — detect and resolve cross-artifact inconsistencies.

The reconciler compares DLR entries, drift signals, memory graph nodes,
and reflection summaries to find mismatches and propose repair actions.

Repair actions are returned as structured proposals — the reconciler
does not apply them automatically (that is left to the operator or
an automated pipeline).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from core.dlr import DLRBuilder
from core.ds import DriftSignalCollector
from core.mg import MemoryGraph, NodeKind

logger = logging.getLogger(__name__)


class RepairKind(str, Enum):
    """Types of repair the reconciler can propose."""

    ADD_MG_NODE = "add_mg_node"
    LINK_DRIFT_TO_EPISODE = "link_drift_to_episode"
    BACKFILL_POLICY_STAMP = "backfill_policy_stamp"
    FLAG_STALE_DLR = "flag_stale_dlr"
    SUGGEST_PATCH = "suggest_patch"


@dataclass
class RepairProposal:
    """A proposed repair action."""

    kind: RepairKind
    target_id: str
    description: str
    auto_fixable: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReconciliationResult:
    """Output of a reconciliation run."""

    run_at: str
    proposals: List[RepairProposal]
    auto_fixable_count: int
    manual_count: int


class Reconciler:
    """Detect and propose repairs for cross-artifact inconsistencies.

    Usage:
        recon = Reconciler(dlr_builder=dlr, ds=ds, mg=mg)
        result = recon.reconcile()
        for proposal in result.proposals:
            print(proposal.description)
    """

    def __init__(
        self,
        dlr_builder: Optional[DLRBuilder] = None,
        ds: Optional[DriftSignalCollector] = None,
        mg: Optional[MemoryGraph] = None,
    ) -> None:
        self.dlr = dlr_builder
        self.ds = ds
        self.mg = mg

    def reconcile(self) -> ReconciliationResult:
        """Run all reconciliation checks."""
        proposals: List[RepairProposal] = []
        proposals.extend(self._check_mg_missing_episodes())
        proposals.extend(self._check_orphan_drift())
        proposals.extend(self._check_missing_policy_stamps())
        proposals.extend(self._check_unresolved_drift())

        auto = sum(1 for p in proposals if p.auto_fixable)
        manual = len(proposals) - auto

        result = ReconciliationResult(
            run_at=datetime.now(timezone.utc).isoformat(),
            proposals=proposals,
            auto_fixable_count=auto,
            manual_count=manual,
        )
        logger.info(
            "Reconciliation complete: %d proposals (%d auto-fixable, %d manual)",
            len(proposals), auto, manual,
        )
        return result

    def apply_auto_fixes(self) -> List[RepairProposal]:
        """Run reconciliation and apply all auto-fixable proposals.

        Returns the list of proposals that were applied.
        """
        result = self.reconcile()
        applied: List[RepairProposal] = []
        for proposal in result.proposals:
            if proposal.auto_fixable:
                self._apply(proposal)
                applied.append(proposal)
        logger.info("Applied %d auto-fixes", len(applied))
        return applied

    def to_json(self, indent: int = 2) -> str:
        """Reconcile and serialise results to JSON."""
        result = self.reconcile()
        raw = asdict(result)
        for p in raw.get("proposals", []):
            p["kind"] = p["kind"].value if hasattr(p["kind"], "value") else p["kind"]
        return json.dumps(raw, indent=indent)

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def _check_mg_missing_episodes(self) -> List[RepairProposal]:
        """Find DLR episodes not present in the Memory Graph."""
        proposals: List[RepairProposal] = []
        if self.dlr is None or self.mg is None:
            return proposals
        for entry in self.dlr.entries:
            result = self.mg.query("why", episode_id=entry.episode_id)
            if result.get("node") is None:
                proposals.append(RepairProposal(
                    kind=RepairKind.ADD_MG_NODE,
                    target_id=entry.episode_id,
                    description=f"Episode {entry.episode_id} exists in DLR but not in Memory Graph.",
                    auto_fixable=True,
                    details={"dlr_id": entry.dlr_id},
                ))
        return proposals

    def _check_orphan_drift(self) -> List[RepairProposal]:
        """Find drift events whose episode is not in the Memory Graph."""
        proposals: List[RepairProposal] = []
        if self.ds is None or self.mg is None:
            return proposals
        summary = self.ds.summarise()
        for bucket in summary.buckets:
            for ep_id in bucket.episode_ids:
                result = self.mg.query("why", episode_id=ep_id)
                if result.get("node") is None:
                    proposals.append(RepairProposal(
                        kind=RepairKind.LINK_DRIFT_TO_EPISODE,
                        target_id=ep_id,
                        description=(
                            f"Drift fingerprint {bucket.fingerprint_key!r} references "
                            f"episode {ep_id} which is missing from Memory Graph."
                        ),
                        auto_fixable=False,
                        details={"fingerprint": bucket.fingerprint_key},
                    ))
                    break  # one proposal per bucket is enough
        return proposals

    def _check_missing_policy_stamps(self) -> List[RepairProposal]:
        """Find DLR entries without a policy stamp."""
        proposals: List[RepairProposal] = []
        if self.dlr is None:
            return proposals
        for entry in self.dlr.entries:
            if not entry.policy_stamp:
                proposals.append(RepairProposal(
                    kind=RepairKind.BACKFILL_POLICY_STAMP,
                    target_id=entry.episode_id,
                    description=f"DLR {entry.dlr_id} has no policy stamp — backfill recommended.",
                    auto_fixable=False,
                    details={"dlr_id": entry.dlr_id, "decision_type": entry.decision_type},
                ))
        return proposals

    def _check_unresolved_drift(self) -> List[RepairProposal]:
        """Suggest patches for high-recurrence drift without resolution."""
        proposals: List[RepairProposal] = []
        if self.ds is None:
            return proposals
        summary = self.ds.summarise()
        for bucket in summary.buckets:
            if bucket.count >= 3 and bucket.recommended_patches:
                proposals.append(RepairProposal(
                    kind=RepairKind.SUGGEST_PATCH,
                    target_id=bucket.fingerprint_key,
                    description=(
                        f"Drift {bucket.fingerprint_key!r} recurred {bucket.count} times — "
                        f"recommended patches: {bucket.recommended_patches}"
                    ),
                    auto_fixable=False,
                    details={
                        "count": bucket.count,
                        "severity": bucket.worst_severity,
                        "patches": bucket.recommended_patches,
                    },
                ))
        return proposals

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------

    def _apply(self, proposal: RepairProposal) -> None:
        """Apply a single auto-fixable proposal."""
        if proposal.kind == RepairKind.ADD_MG_NODE and self.mg is not None:
            # Create a minimal episode node in the graph
            from core.mg import GraphNode
            self.mg._add_node(GraphNode(
                node_id=proposal.target_id,
                kind=NodeKind.EPISODE,
                label="backfilled",
                timestamp=datetime.now(timezone.utc).isoformat(),
                properties={"backfilled": True},
            ))
            logger.debug("Auto-fix: added MG node for %s", proposal.target_id)
