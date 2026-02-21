"""Decision Log Record (DLR) builder.

The DLR is the *truth constitution* for a decision class.  It captures
the DTE reference, action contract used (or blocked), verification
requirement, and policy pack stamp from a sealed DecisionEpisode.

A DLR answers: "what policy governed this decision, and was it followed?"
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DLREntry:
    """A single Decision Log Record produced from one sealed episode."""

    dlr_id: str
    episode_id: str
    decision_type: str
    recorded_at: str
    dte_ref: Dict[str, Any]
    action_contract: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    policy_stamp: Optional[Dict[str, Any]] = None
    outcome_code: str = "unknown"
    degrade_step: Optional[str] = None
    tags: List[str] = field(default_factory=list)


class DLRBuilder:
    """Builds DLR entries from sealed DecisionEpisodes.

    Usage:
        builder = DLRBuilder()
        dlr = builder.from_episode(sealed_episode)
        batch = builder.from_episodes(episode_list)
    """

    def __init__(self) -> None:
        self._entries: List[DLREntry] = []

    @property
    def entries(self) -> List[DLREntry]:
        """All DLR entries built so far."""
        return list(self._entries)

    def from_episode(self, episode: Dict[str, Any]) -> DLREntry:
        """Extract a DLR entry from a single sealed episode dict.

        Args:
            episode: A sealed DecisionEpisode (dict).

        Returns:
            The constructed DLREntry.
        """
        episode_id = episode.get("episodeId", "")
        dlr_id = self._make_dlr_id(episode_id)

        entry = DLREntry(
            dlr_id=dlr_id,
            episode_id=episode_id,
            decision_type=episode.get("decisionType", ""),
            recorded_at=datetime.now(timezone.utc).isoformat(),
            dte_ref=episode.get("dteRef", {}),
            action_contract=self._extract_action_contract(episode),
            verification=episode.get("verification"),
            policy_stamp=episode.get("policy"),
            outcome_code=episode.get("outcome", {}).get("code", "unknown"),
            degrade_step=episode.get("degrade", {}).get("step"),
        )
        self._entries.append(entry)
        logger.debug("DLR entry %s created for episode %s", dlr_id, episode_id)
        return entry

    def from_episodes(self, episodes: List[Dict[str, Any]]) -> List[DLREntry]:
        """Build DLR entries for a batch of episodes."""
        return [self.from_episode(ep) for ep in episodes]

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Serialise all entries to a list of plain dicts."""
        return [asdict(e) for e in self._entries]

    def to_json(self, indent: int = 2) -> str:
        """Serialise all entries to a JSON string."""
        return json.dumps(self.to_dict_list(), indent=indent)

    def clear(self) -> None:
        """Reset the builder, discarding all entries."""
        self._entries.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_dlr_id(episode_id: str) -> str:
        """Derive a deterministic DLR id from the episode id."""
        digest = hashlib.sha256(episode_id.encode("utf-8")).hexdigest()[:12]
        return f"dlr-{digest}"

    @staticmethod
    def _extract_action_contract(episode: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Pull action-contract fields from the actions list."""
        actions = episode.get("actions", [])
        if not actions:
            return None
        first = actions[0] if isinstance(actions, list) else actions
        return {
            "blastRadiusTier": first.get("blastRadiusTier"),
            "idempotencyKey": first.get("idempotencyKey"),
            "rollbackPlan": first.get("rollbackPlan"),
            "authMode": first.get("authorization", {}).get("mode"),
        }



# ======================================================================
# Claim-Native DLR Builder (v1.0)
# Produces DLRs that reference AtomicClaim IDs rather than raw text.
# Conforms to schemas/core/dlr.schema.json
# ======================================================================


@dataclass
class ClaimRef:
    """A reference to an AtomicClaim within a DLR."""

    claim_id: str
    role: str = "supporting"  # supporting | primary | dissenting | rejected
    confidence_at_decision: Optional[float] = None
    status_at_decision: Optional[str] = None  # green | yellow | red


@dataclass
class RationaleEdge:
    """An edge in the DLR rationale graph."""

    source: str  # claim_id
    target: str  # claim_id
    relation: str  # depends_on | contradicts | supports | supersedes


@dataclass
class ClaimNativeDLREntry:
    """A claim-native Decision Log Record entry."""

    dlr_id: str
    episode_id: str
    decision_type: str
    claims: List[ClaimRef] = field(default_factory=list)
    rationale_edges: List[RationaleEdge] = field(default_factory=list)
    policy_pack_id: Optional[str] = None
    sealed_at: Optional[str] = None
    outcome_code: Optional[str] = None


class ClaimNativeDLRBuilder:
    """Builds claim-native DLR entries from sealed episodes + claims.

    Usage:
        builder = ClaimNativeDLRBuilder()
        dlr = builder.from_episode(sealed_episode, claims)
        batch = builder.from_episodes(episodes_with_claims)
    """

    def __init__(self) -> None:
        self._entries: List[ClaimNativeDLREntry] = []

    @property
    def entries(self) -> List[ClaimNativeDLREntry]:
        """All claim-native DLR entries built so far."""
        return list(self._entries)

    def from_episode(
        self,
        episode: Dict[str, Any],
        claims: Optional[List[Dict[str, Any]]] = None,
    ) -> ClaimNativeDLREntry:
        """Build a claim-native DLR entry from a sealed episode and its claims."""
        ep_id = episode.get("episodeId", "")
        dlr_id = f"DLR-CN-{ep_id}"

        claim_refs = []
        if claims:
            for c in claims:
                claim_refs.append(ClaimRef(
                    claim_id=c.get("claimId", ""),
                    role=c.get("role", "supporting"),
                    confidence_at_decision=c.get("confidence", {}).get("score"),
                    status_at_decision=c.get("statusLight"),
                ))

        rationale_edges = []
        if claims:
            for c in claims:
                graph = c.get("graph", {})
                cid = c.get("claimId", "")
                for dep in graph.get("dependsOn", []):
                    rationale_edges.append(RationaleEdge(
                        source=cid, target=dep, relation="depends_on",
                    ))
                for contra in graph.get("contradicts", []):
                    rationale_edges.append(RationaleEdge(
                        source=cid, target=contra, relation="contradicts",
                    ))
                for sup in graph.get("supports", []):
                    rationale_edges.append(RationaleEdge(
                        source=cid, target=sup, relation="supports",
                    ))
                supersedes = graph.get("supersedes")
                if supersedes:
                    rationale_edges.append(RationaleEdge(
                        source=cid, target=supersedes, relation="supersedes",
                    ))

        entry = ClaimNativeDLREntry(
            dlr_id=dlr_id,
            episode_id=ep_id,
            decision_type=episode.get("decisionType", ""),
            claims=claim_refs,
            rationale_edges=rationale_edges,
            policy_pack_id=episode.get("policyPack", {}).get("policyPackId"),
            sealed_at=episode.get("sealedAt"),
            outcome_code=episode.get("outcome", {}).get("code"),
        )
        self._entries.append(entry)
        return entry

    def from_episodes(
        self,
        episodes_with_claims: List[Dict[str, Any]],
    ) -> List[ClaimNativeDLREntry]:
        """Build batch of claim-native DLR entries.

        Each item in the list must have 'episode' and optional 'claims' keys.
        """
        results = []
        for item in episodes_with_claims:
            ep = item.get("episode", item)
            claims = item.get("claims")
            results.append(self.from_episode(ep, claims))
        return results
