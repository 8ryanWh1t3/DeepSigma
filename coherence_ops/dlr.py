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
# Conforms to specs/dlr.schema.json
# ======================================================================


@dataclass
class ClaimRef:
        """A reference to an AtomicClaim within a DLR."""

    claim_id: str
    role: str = "supporting"  # supporting | primary | dissenting | contextual
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
    recorded_at: str
    claim_refs: List[ClaimRef] = field(default_factory=list)
    rationale_graph: List[RationaleEdge] = field(default_factory=list)
    primary_claim_id: Optional[str] = None
    dte_ref: Dict[str, Any] = field(default_factory=dict)
    action_contract: Optional[Dict[str, Any]] = None
    policy_stamp: Optional[Dict[str, Any]] = None
    outcome_code: str = "unknown"
    seal: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)


class ClaimNativeDLRBuilder:
        """Builds claim-native DLR entries from sealed episodes + claim data.

            Usage:
                    builder = ClaimNativeDLRBuilder()
                            dlr = builder.from_episode(sealed_episode, claims=[...])
                                    batch = builder.from_episodes(episode_list)
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
                """Build a claim-native DLR entry from a sealed episode.

                        Args:
                                    episode: A sealed DecisionEpisode dict.
                                                claims: Optional list of AtomicClaim dicts associated with this decision.

                                                        Returns:
                                                                    The constructed ClaimNativeDLREntry.
                                                                            """
                episode_id = episode.get("episodeId", "")
                dlr_id = self._make_dlr_id(episode_id)
                claims = claims or []

        # Build claim refs
                claim_refs = []
        primary_id = None
        for i, claim in enumerate(claims):
                        cid = claim.get("claimId", f"CLAIM-UNKNOWN-{i}")
                        role = claim.get("role", "primary" if i == 0 else "supporting")
                        ref = ClaimRef(
                            claim_id=cid,
                            role=role,
                            confidence_at_decision=claim.get("confidence", {}).get("score"),
                            status_at_decision=claim.get("statusLight"),
                        )
                        claim_refs.append(ref)
                        if role == "primary" and primary_id is None:
                                            primary_id = cid

                    # Build rationale graph from claim graph edges
                    rationale_graph = []
        for claim in claims:
                        cid = claim.get("claimId", "")
                        graph = claim.get("graph", {})
                        for dep in graph.get("dependsOn", []):
                                            rationale_graph.append(
                                                                    RationaleEdge(source=cid, target=dep, relation="depends_on")
                                            )
                                        for contra in graph.get("contradicts", []):
                                                            rationale_graph.append(
                                                                                    RationaleEdge(source=cid, target=contra, relation="contradicts")
                                                            )
                                                        for sup in graph.get("supports", []):
                                                                            rationale_graph.append(
                                                                                                    RationaleEdge(source=cid, target=sup, relation="supports")
                                                                            )
                                                                        supersedes = graph.get("supersedes")
            if supersedes:
                                rationale_graph.append(
                                                        RationaleEdge(source=cid, target=supersedes, relation="supersedes")
                                )

        # Build seal
        seal_data = episode.get("seal")
        seal = None
        if seal_data:
                        seal = {
                            "hash": seal_data.get("sealHash", ""),
                            "sealedAt": seal_data.get("sealedAt", ""),
                            "version": seal_data.get("sealVersion", 1),
        }

        entry = ClaimNativeDLREntry(
                        dlr_id=dlr_id,
                        episode_id=episode_id,
                        decision_type=episode.get("decisionType", ""),
                        recorded_at=datetime.now(timezone.utc).isoformat(),
                        claim_refs=claim_refs,
                        rationale_graph=rationale_graph,
                        primary_claim_id=primary_id,
                        dte_ref=episode.get("dteRef", {}),
                        action_contract=DLRBuilder._extract_action_contract(episode),
                        policy_stamp=episode.get("policy"),
                        outcome_code=episode.get("outcome", {}).get("code", "unknown"),
                        seal=seal,
        )
        self._entries.append(entry)
        logger.debug(
                        "Claim-native DLR %s created for episode %s with %d claims",
                        dlr_id, episode_id, len(claim_refs),
        )
        return entry

    def from_episodes(
                self,
                episodes: List[Dict[str, Any]],
                claims_by_episode: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> List[ClaimNativeDLREntry]:
                """Build claim-native DLR entries for a batch of episodes."""
        claims_by_episode = claims_by_episode or {}
        return [
                        self.from_episode(ep, claims_by_episode.get(ep.get("episodeId", ""), []))
                        for ep in episodes
        ]

    def to_dict_list(self) -> List[Dict[str, Any]]:
                """Serialise all entries to a list of plain dicts."""
        return [asdict(e) for e in self._entries]

    def to_json(self, indent: int = 2) -> str:
                """Serialise all entries to a JSON string."""
        return json.dumps(self.to_dict_list(), indent=indent, default=str)

    def clear(self) -> None:
                """Reset the builder, discarding all entries."""
        self._entries.clear()

    @staticmethod
    def _make_dlr_id(episode_id: str) -> str:
                """Derive a deterministic DLR id from the episode id."""
        digest = hashlib.sha256(episode_id.encode("utf-8")).hexdigest()[:12]
        return f"dlr-cn-{digest}"
