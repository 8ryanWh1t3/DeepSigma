"""COG bundle verifier — integrity and completeness checks.

Functions:
    verify_cog_bundle — check bundle integrity, proof, and manifest consistency
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.primitives import _seal_hash

from .models import CogBundle


def verify_cog_bundle(bundle: CogBundle) -> Dict[str, Any]:
    """Verify a CogBundle for integrity and completeness.

    Returns a dict with:
        bundle_hash_present     — proof chain contains at least one hash
        proof_metadata_present  — proof section exists
        replay_metadata_present — replay steps exist
        manifest_consistent     — all manifest artifact_refs exist in artifacts
        missing_required_fields — list of missing required fields
        content_hash_valid      — artifact content hashes verify correctly
        status                  — "pass", "warn", or "fail"
    """
    missing_fields: List[str] = []
    issues: List[str] = []

    # Check manifest required fields
    if not bundle.manifest.bundle_id:
        missing_fields.append("manifest.bundleId")

    # Check proof presence
    proof_present = bundle.proof is not None
    bundle_hash_present = False
    if proof_present and bundle.proof is not None:
        bundle_hash_present = len(bundle.proof.proof_chain) > 0

    # Check replay presence
    replay_present = len(bundle.replay_steps) > 0

    # Check manifest consistency — every ref in manifest must exist in artifacts
    artifact_ids = {a.ref_id for a in bundle.artifacts}
    manifest_refs = set(bundle.manifest.artifact_refs)
    orphan_refs = manifest_refs - artifact_ids
    manifest_consistent = len(orphan_refs) == 0
    if not manifest_consistent:
        issues.append(f"manifest refs not in artifacts: {sorted(orphan_refs)}")

    # Verify content hashes on artifacts
    content_hash_valid = True
    for artifact in bundle.artifacts:
        if artifact.content_hash and artifact.payload:
            expected = _seal_hash(artifact.payload)
            if artifact.content_hash != expected:
                content_hash_valid = False
                issues.append(
                    f"hash mismatch on {artifact.ref_id}: "
                    f"expected {expected}, got {artifact.content_hash}"
                )

    # Determine overall status
    if missing_fields or not manifest_consistent or not content_hash_valid:
        status = "fail"
    elif not proof_present or not bundle_hash_present:
        status = "warn"
    else:
        status = "pass"

    return {
        "bundle_hash_present": bundle_hash_present,
        "proof_metadata_present": proof_present,
        "replay_metadata_present": replay_present,
        "manifest_consistent": manifest_consistent,
        "missing_required_fields": missing_fields,
        "content_hash_valid": content_hash_valid,
        "issues": issues,
        "status": status,
    }
