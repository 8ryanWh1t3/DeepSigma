"""COG bundle exporter — convert DeepSigma artifacts to COG bundles.

Functions:
    deepsigma_to_cog — map a DeepSigmaDecisionArtifact into a CogBundle
    write_cog_bundle — serialize a CogBundle to a JSON file
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from core.primitives import _seal_hash

from .models import (
    CogArtifactRef,
    CogBundle,
    CogManifest,
    CogProof,
    CogReplayStep,
    DeepSigmaDecisionArtifact,
)


def _make_artifact_ref(
    ref_type: str,
    payload: Dict[str, Any],
    ref_id_prefix: str = "",
) -> CogArtifactRef:
    """Create a CogArtifactRef with a content hash."""
    ref_id = f"{ref_id_prefix}{ref_type}-{uuid.uuid4().hex[:8]}"
    content_hash = _seal_hash(payload)
    return CogArtifactRef(
        ref_id=ref_id,
        ref_type=ref_type,
        content_hash=content_hash,
        payload=payload,
    )


def deepsigma_to_cog(artifact: DeepSigmaDecisionArtifact) -> CogBundle:
    """Convert a DeepSigmaDecisionArtifact into a CogBundle.

    Maps:
        truth_claims      -> artifact refs with ref_type="evidence"
        reasoning         -> artifact ref with ref_type="rationale"
        memory_refs       -> artifact refs with ref_type="memory"
        drift_annotations -> artifact refs with ref_type="drift"
        patch_refs        -> artifact refs with ref_type="patch"
    """
    now = datetime.now(timezone.utc).isoformat()
    prefix = f"{artifact.artifact_id}:"
    artifacts: List[CogArtifactRef] = []

    # Truth -> evidence
    for claim in artifact.truth_claims:
        artifacts.append(_make_artifact_ref("evidence", claim, prefix))

    # Reasoning -> rationale
    if artifact.reasoning:
        artifacts.append(_make_artifact_ref("rationale", artifact.reasoning, prefix))

    # Memory -> memory
    for mem in artifact.memory_refs:
        artifacts.append(_make_artifact_ref("memory", mem, prefix))

    # Drift -> drift (optional)
    for drift in artifact.drift_annotations:
        artifacts.append(_make_artifact_ref("drift", drift, prefix))

    # Patch -> patch (optional)
    for patch in artifact.patch_refs:
        artifacts.append(_make_artifact_ref("patch", patch, prefix))

    # Build manifest
    manifest = CogManifest(
        bundle_id=artifact.artifact_id,
        version="1.0",
        created_at=now,
        description=f"COG bundle exported from DeepSigma artifact {artifact.artifact_id}",
        artifact_refs=[a.ref_id for a in artifacts],
        metadata=artifact.metadata,
    )

    # Build proof chain (per-artifact entries)
    from .proof_chain import build_proof_chain

    chain = build_proof_chain(artifacts)
    rule_seal = artifact.metadata.get("policyHash") if artifact.metadata else None
    proof = CogProof(
        proof_chain=chain,
        timestamps=[now],
        rule_seal=rule_seal,
    )

    # Build replay steps from replay record if present
    replay_steps: List[CogReplayStep] = []
    if artifact.replay and artifact.replay.steps:
        for i, step in enumerate(artifact.replay.steps):
            replay_steps.append(CogReplayStep(
                step_index=step.get("stepIndex", step.get("step_index", i)),
                action=step.get("action", "unknown"),
                input_ref=step.get("inputRef", step.get("input_ref", "")),
                output_ref=step.get("outputRef", step.get("output_ref", "")),
                timestamp=step.get("timestamp", ""),
                metadata=step.get("metadata", {}),
            ))

    return CogBundle(
        manifest=manifest,
        artifacts=artifacts,
        proof=proof,
        replay_steps=replay_steps,
        raw_metadata=artifact.metadata,
    )


def write_cog_bundle(bundle: CogBundle, path: str) -> None:
    """Serialize a CogBundle to a JSON file at *path*.

    Uses deterministic key ordering for reproducibility.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = bundle.to_dict()
    p.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
