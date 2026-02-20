"""Mesh Node Runtime — Edge, Validator, Aggregator, Seal Authority.

Thread-based node processes with independent state and replication.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from mesh.crypto import DEMO_MODE, canonical_bytes, generate_keypair, verify
from mesh.envelopes import (
    AggregationRecord,
    create_envelope,
    create_validation,
)
from mesh.federation import compute_credibility_index, compute_federated_state
from mesh.logstore import (
    append_jsonl,
    dedupe_by_id,
    load_all,
    load_last_n,
)
from mesh.transport import (
    AGGREGATES_LOG,
    ENVELOPES_LOG,
    SEAL_CHAIN_MIRROR_LOG,
    VALIDATIONS_LOG,
    LocalTransport,
    ensure_node_dirs,
    log_replication,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class NodeRole(str, Enum):
    EDGE = "edge"
    VALIDATOR = "validator"
    AGGREGATOR = "aggregator"
    SEAL_AUTHORITY = "seal_authority"


@dataclass
class MeshNode:
    """A mesh node with a specific role.

    Parameters
    ----------
    transport : Transport, optional
        Pluggable transport for inter-node communication.
        Defaults to LocalTransport (filesystem-based, in-process).
    """

    node_id: str
    tenant_id: str
    region_id: str
    role: NodeRole
    peers: list[str] = field(default_factory=list)
    public_key: str = ""
    private_key: str = ""
    running: bool = False
    _cycle_count: int = 0
    transport: Any = None

    # Scenario overrides
    offline: bool = False
    force_correlation: float | None = None

    def __post_init__(self):
        if self.transport is None:
            self.transport = LocalTransport()
        if not self.public_key or not self.private_key:
            self.public_key, self.private_key = generate_keypair()
        ensure_node_dirs(self.tenant_id, self.node_id)
        self._update_status("initialized")

    def _data_dir(self) -> Path:
        from mesh.transport import _node_dir
        return _node_dir(self.tenant_id, self.node_id)

    def _log_path(self, log_name: str) -> Path:
        return self._data_dir() / log_name

    def _update_status(self, state: str, extra: dict | None = None) -> None:
        status = {
            "node_id": self.node_id,
            "tenant_id": self.tenant_id,
            "region_id": self.region_id,
            "role": self.role.value,
            "state": state,
            "offline": self.offline,
            "crypto_mode": "DEMO" if DEMO_MODE else "Ed25519",
            "public_key": self.public_key[:16] + "...",
            "cycle_count": self._cycle_count,
            "last_updated": _now_iso(),
        }
        if extra:
            status.update(extra)
        self.transport.set_status(self.tenant_id, self.node_id, status)

    def tick(self) -> dict[str, Any]:
        """Execute one cycle of the node's role behavior.

        Returns a summary dict of what happened.
        """
        if self.offline:
            self._update_status("offline")
            return {"node_id": self.node_id, "action": "skip", "reason": "offline"}

        self._cycle_count += 1
        self.running = True

        if self.role == NodeRole.EDGE:
            result = self._tick_edge()
        elif self.role == NodeRole.VALIDATOR:
            result = self._tick_validator()
        elif self.role == NodeRole.AGGREGATOR:
            result = self._tick_aggregator()
        elif self.role == NodeRole.SEAL_AUTHORITY:
            result = self._tick_seal_authority()
        else:
            result = {"action": "noop"}

        result["node_id"] = self.node_id
        result["cycle"] = self._cycle_count
        self._update_status("active", {"last_action": result.get("action", "unknown")})
        return result

    # -------------------------------------------------------------------
    # EDGE: generate envelopes
    # -------------------------------------------------------------------

    def _tick_edge(self) -> dict[str, Any]:
        """Generate signed evidence envelope(s) and replicate to peers."""
        groups = ["G1", "G2", "G3"]
        forced = (
            self.force_correlation is not None
            and self.force_correlation > 0.8
        )

        # Forced correlation: burst of 3 envelopes in one group
        # to immediately trigger the correlation threshold
        burst_count = 3 if forced else 1
        envelopes_created = []

        for _ in range(burst_count):
            # Generate abstract payload
            # Wide range → low demo-correlation coefficient (healthy)
            base_value = random.randint(20, 100)
            confidence = round(random.uniform(0.5, 1.0), 3)
            group = random.choice(groups)

            # If forced correlation: lock to single group + tight values
            # Simulates shared-source risk (all signals from same origin)
            if forced:
                group = "G1"
                base_value = 95
                confidence = 0.98

            payload = {
                "value": base_value,
                "confidence": confidence,
                "source": f"edge-{self.node_id}",
            }

            env = create_envelope(
                tenant_id=self.tenant_id,
                producer_id=self.node_id,
                region_id=self.region_id,
                correlation_group=group,
                payload=payload,
                private_key=self.private_key,
                public_key=self.public_key,
            )

            # Append to own log
            append_jsonl(self._log_path(ENVELOPES_LOG), env.to_dict())

            # Replicate to peers
            for peer_id in self.peers:
                self.transport.push(
                    self.tenant_id, peer_id, ENVELOPES_LOG, [env.to_dict()],
                )

            envelopes_created.append(env)

        # Log replication once per tick
        for peer_id in self.peers:
            log_replication(
                self.tenant_id, self.node_id, "push", peer_id,
                ENVELOPES_LOG, burst_count,
            )

        return {
            "action": "generate_envelope",
            "envelope_id": envelopes_created[-1].envelope_id,
            "envelope_count": burst_count,
            "region": self.region_id,
            "group": group,
            "replicated_to": len(self.peers),
        }

    # -------------------------------------------------------------------
    # VALIDATOR: verify and validate envelopes
    # -------------------------------------------------------------------

    def _tick_validator(self) -> dict[str, Any]:
        """Pull envelopes from peers, verify signatures, emit validations."""
        validated = 0
        rejected = 0

        for peer_id in self.peers:
            envs = self.transport.pull(
                self.tenant_id, peer_id, ENVELOPES_LOG,
            )

            # Dedupe against already-validated
            existing_vals = load_all(self._log_path(VALIDATIONS_LOG))
            validated_env_ids = {v.get("envelope_id") for v in existing_vals}

            for env_dict in envs:
                env_id = env_dict.get("envelope_id", "")
                if env_id in validated_env_ids:
                    continue

                # Verify signature
                sig_ok = verify(
                    env_dict.get("public_key", ""),
                    canonical_bytes(
                        _signable_from_dict(env_dict)
                    ),
                    env_dict.get("signature", ""),
                )

                # Policy checks
                reasons = []
                verdict = "ACCEPT"

                if not sig_ok:
                    verdict = "REJECT"
                    reasons.append("signature_invalid")

                # Check payload hash
                payload_raw = canonical_bytes(env_dict.get("payload", {}))
                expected_hash = hashlib.sha256(payload_raw).hexdigest()[:40]
                if env_dict.get("payload_hash") != expected_hash:
                    verdict = "REJECT"
                    reasons.append("payload_hash_mismatch")

                val = create_validation(
                    tenant_id=self.tenant_id,
                    validator_id=self.node_id,
                    region_id=self.region_id,
                    envelope_id=env_id,
                    verdict=verdict,
                    reasons=reasons,
                    private_key=self.private_key,
                    public_key=self.public_key,
                )

                # Append to own log
                append_jsonl(
                    self._log_path(VALIDATIONS_LOG), val.to_dict(),
                )
                validated_env_ids.add(env_id)

                if verdict == "ACCEPT":
                    validated += 1
                else:
                    rejected += 1

        # Replicate validations to peers
        all_vals = load_all(self._log_path(VALIDATIONS_LOG))
        for peer_id in self.peers:
            self.transport.push(
                self.tenant_id, peer_id, VALIDATIONS_LOG, all_vals[-10:],
            )
            log_replication(
                self.tenant_id, self.node_id, "push", peer_id,
                VALIDATIONS_LOG, min(10, len(all_vals)),
            )

        return {
            "action": "validate_envelopes",
            "accepted": validated,
            "rejected": rejected,
        }

    # -------------------------------------------------------------------
    # AGGREGATOR: compute federated state
    # -------------------------------------------------------------------

    def _tick_aggregator(self) -> dict[str, Any]:
        """Pull envelopes + validations, compute federated claim state."""
        # Gather envelopes and validations from all peers
        all_envs: list[dict] = []
        all_vals: list[dict] = []

        for peer_id in self.peers:
            all_envs.extend(
                self.transport.pull(self.tenant_id, peer_id, ENVELOPES_LOG)
            )
            all_vals.extend(
                self.transport.pull(self.tenant_id, peer_id, VALIDATIONS_LOG)
            )

        # Also include own logs
        all_envs.extend(load_all(self._log_path(ENVELOPES_LOG)))
        all_vals.extend(load_all(self._log_path(VALIDATIONS_LOG)))

        # Deduplicate
        all_envs = dedupe_by_id(all_envs, "envelope_id")
        all_vals = dedupe_by_id(all_vals, "validation_id")

        # Load policy
        from tenancy.policies import get_policy_hash, load_policy
        policy = load_policy(self.tenant_id)
        policy_hash = get_policy_hash(policy)

        # Build sync regions from known peers
        regions = _build_sync_regions(self.peers, self.tenant_id, all_envs, self.transport)

        # Compute federated state
        fed_state = compute_federated_state(
            policy=policy,
            envelopes=all_envs,
            validations=all_vals,
            sync_regions=regions,
        )

        # Compute credibility index
        index = compute_credibility_index(
            claims=fed_state["tier0_claims"],
            clusters=fed_state["correlation_clusters"],
            sync_regions=fed_state["sync_regions"],
            metrics=fed_state["component_metrics"],
        )

        # Build aggregation record
        agg = AggregationRecord(
            tenant_id=self.tenant_id,
            aggregator_id=self.node_id,
            window_start=all_envs[0].get("timestamp", "") if all_envs else "",
            window_end=all_envs[-1].get("timestamp", "") if all_envs else "",
            tier0_claims_state=[c for c in fed_state["tier0_claims"]],
            correlation_clusters=fed_state["correlation_clusters"],
            sync_regions=fed_state["sync_regions"],
            credibility_snapshot=index,
            policy_hash=policy_hash,
        )
        agg.compute_seal_candidate()

        # Append to own log
        append_jsonl(self._log_path(AGGREGATES_LOG), agg.to_dict())

        # Replicate aggregates to peers
        for peer_id in self.peers:
            self.transport.push(
                self.tenant_id, peer_id, AGGREGATES_LOG, [agg.to_dict()],
            )
            log_replication(
                self.tenant_id, self.node_id, "push", peer_id,
                AGGREGATES_LOG, 1,
            )

        return {
            "action": "aggregate",
            "aggregate_id": agg.aggregate_id,
            "index_score": index["score"],
            "index_band": index["band"],
            "claim_state": fed_state["tier0_claims"][0]["state"] if fed_state["tier0_claims"] else "UNKNOWN",
            "envelopes_processed": len(all_envs),
            "validations_processed": len(all_vals),
        }

    # -------------------------------------------------------------------
    # SEAL AUTHORITY: seal via credibility engine
    # -------------------------------------------------------------------

    def _tick_seal_authority(self) -> dict[str, Any]:
        """Pull latest aggregate and create a chained seal."""
        # Pull aggregates from peers
        all_aggs: list[dict] = []
        for peer_id in self.peers:
            all_aggs.extend(
                self.transport.pull(self.tenant_id, peer_id, AGGREGATES_LOG)
            )
        all_aggs.extend(load_all(self._log_path(AGGREGATES_LOG)))
        all_aggs = dedupe_by_id(all_aggs, "aggregate_id")

        if not all_aggs:
            return {"action": "seal_skip", "reason": "no_aggregates"}

        latest_agg = all_aggs[-1]

        # Build seal chain entry
        from tenancy.policies import get_policy_hash, load_policy
        policy = load_policy(self.tenant_id)
        policy_hash = get_policy_hash(policy)

        # Load previous seal from mirror
        prev_seals = load_last_n(
            self._log_path(SEAL_CHAIN_MIRROR_LOG), 1,
        )
        prev_seal_hash = "GENESIS"
        if prev_seals:
            prev_seal_hash = prev_seals[-1].get("seal_hash", "GENESIS")

        snapshot_hash = latest_agg.get("seal_candidate_hash", "")

        # Compute seal hash
        seal_input = f"{prev_seal_hash}|{policy_hash}|{snapshot_hash}"
        seal_hash = f"sha256:{hashlib.sha256(seal_input.encode()).hexdigest()[:40]}"

        seal_entry = {
            "tenant_id": self.tenant_id,
            "aggregate_id": latest_agg.get("aggregate_id", ""),
            "sealed_by": self.node_id,
            "sealed_at": _now_iso(),
            "seal_hash": seal_hash,
            "prev_seal_hash": prev_seal_hash,
            "policy_hash": policy_hash,
            "snapshot_hash": snapshot_hash,
            "index_score": latest_agg.get("credibility_snapshot", {}).get("score"),
            "index_band": latest_agg.get("credibility_snapshot", {}).get("band"),
        }

        # Append to own seal chain mirror
        append_jsonl(self._log_path(SEAL_CHAIN_MIRROR_LOG), seal_entry)

        # Replicate seal to peers
        for peer_id in self.peers:
            self.transport.push(
                self.tenant_id, peer_id, SEAL_CHAIN_MIRROR_LOG,
                [seal_entry],
            )
            log_replication(
                self.tenant_id, self.node_id, "push", peer_id,
                SEAL_CHAIN_MIRROR_LOG, 1,
            )

        return {
            "action": "seal",
            "seal_hash": seal_hash,
            "prev_seal_hash": prev_seal_hash,
            "aggregate_id": latest_agg.get("aggregate_id", ""),
            "index_score": seal_entry["index_score"],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _signable_from_dict(env_dict: dict) -> dict:
    """Extract signable fields from an envelope dict."""
    return {
        "tenant_id": env_dict.get("tenant_id", ""),
        "envelope_id": env_dict.get("envelope_id", ""),
        "timestamp": env_dict.get("timestamp", ""),
        "producer_id": env_dict.get("producer_id", ""),
        "region_id": env_dict.get("region_id", ""),
        "correlation_group": env_dict.get("correlation_group", ""),
        "signal_type": env_dict.get("signal_type", ""),
        "payload_hash": env_dict.get("payload_hash", ""),
    }


def _build_sync_regions(
    peer_ids: list[str],
    tenant_id: str,
    envelopes: list[dict],
    transport: Any = None,
) -> list[dict]:
    """Build sync region list from known peers and envelope activity."""
    regions: dict[str, dict] = {}

    # Derive regions from envelopes
    for env in envelopes:
        rgn = env.get("region_id", "unknown")
        if rgn not in regions:
            regions[rgn] = {
                "region_id": rgn,
                "node_count": 0,
                "online_count": 0,
                "last_heartbeat": "",
                "status": "healthy",
            }
        regions[rgn]["node_count"] += 1
        regions[rgn]["online_count"] += 1
        ts = env.get("timestamp", "")
        if ts > regions[rgn]["last_heartbeat"]:
            regions[rgn]["last_heartbeat"] = ts

    # Check peer statuses to detect offline regions
    if transport is None:
        from mesh.transport import get_node_status

        def _get_status(tid, pid):
            return get_node_status(tid, pid)
    else:
        _get_status = transport.get_status

    for pid in peer_ids:
        status = _get_status(tenant_id, pid)
        if status and status.get("offline"):
            rgn = status.get("region_id", "unknown")
            if rgn in regions:
                regions[rgn]["status"] = "offline"
            else:
                regions[rgn] = {
                    "region_id": rgn,
                    "node_count": 1,
                    "online_count": 0,
                    "last_heartbeat": "",
                    "status": "offline",
                }

    return list(regions.values())
