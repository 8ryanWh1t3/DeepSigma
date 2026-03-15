"""COG bundle diff — compare two bundles for audit and drift detection.

Follows the diff pattern from ``core.context.propagation.compute_context_diff``.

Functions:
    diff_cog_bundles — compare two CogBundles, classify changes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .models import CogBundle


@dataclass
class CogBundleDiff:
    """Result of comparing two COG bundles."""

    from_bundle_id: str
    to_bundle_id: str
    added_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    removed_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    modified_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    manifest_changes: Dict[str, Any] = field(default_factory=dict)
    proof_changes: Dict[str, Any] = field(default_factory=dict)
    replay_changes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fromBundleId": self.from_bundle_id,
            "toBundleId": self.to_bundle_id,
            "addedArtifacts": self.added_artifacts,
            "removedArtifacts": self.removed_artifacts,
            "modifiedArtifacts": self.modified_artifacts,
            "manifestChanges": self.manifest_changes,
            "proofChanges": self.proof_changes,
            "replayChanges": self.replay_changes,
        }


def diff_cog_bundles(before: CogBundle, after: CogBundle) -> CogBundleDiff:
    """Compare two CogBundles and classify artifact-level changes.

    Artifacts are keyed by ``ref_id``. An artifact present in *after*
    but not *before* is ``added``; in *before* but not *after* is
    ``removed``; in both but with a different ``content_hash`` is
    ``modified``.
    """
    before_map = {a.ref_id: a for a in before.artifacts}
    after_map = {a.ref_id: a for a in after.artifacts}

    added = []
    removed = []
    modified = []

    # Added and modified
    for ref_id, art in after_map.items():
        if ref_id not in before_map:
            added.append({"refId": ref_id, "refType": art.ref_type})
        else:
            old = before_map[ref_id]
            if old.content_hash != art.content_hash:
                modified.append({
                    "refId": ref_id,
                    "refType": art.ref_type,
                    "beforeHash": old.content_hash,
                    "afterHash": art.content_hash,
                })

    # Removed
    for ref_id, art in before_map.items():
        if ref_id not in after_map:
            removed.append({"refId": ref_id, "refType": art.ref_type})

    # Manifest changes
    manifest_changes: Dict[str, Any] = {}
    if before.manifest.version != after.manifest.version:
        manifest_changes["version"] = {
            "before": before.manifest.version,
            "after": after.manifest.version,
        }
    if before.manifest.description != after.manifest.description:
        manifest_changes["description"] = {
            "before": before.manifest.description,
            "after": after.manifest.description,
        }

    # Proof changes
    proof_changes: Dict[str, Any] = {}
    before_chain_len = len(before.proof.proof_chain) if before.proof else 0
    after_chain_len = len(after.proof.proof_chain) if after.proof else 0
    if before_chain_len != after_chain_len:
        proof_changes["chainLength"] = {
            "before": before_chain_len,
            "after": after_chain_len,
        }

    # Replay changes
    replay_changes: Dict[str, Any] = {}
    if len(before.replay_steps) != len(after.replay_steps):
        replay_changes["stepCount"] = {
            "before": len(before.replay_steps),
            "after": len(after.replay_steps),
        }

    return CogBundleDiff(
        from_bundle_id=before.manifest.bundle_id,
        to_bundle_id=after.manifest.bundle_id,
        added_artifacts=added,
        removed_artifacts=removed,
        modified_artifacts=modified,
        manifest_changes=manifest_changes,
        proof_changes=proof_changes,
        replay_changes=replay_changes,
    )
