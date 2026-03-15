"""COG bundle importer — load and convert inbound bundles.

Functions:
    load_cog_bundle          — parse a JSON file into a CogBundle
    cog_to_deepsigma         — map a CogBundle into a DeepSigmaDecisionArtifact
    stream_cog_artifacts     — yield artifacts one at a time (iterator)
    load_cog_bundle_metadata — load only manifest + proof (skip artifacts)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .heuristics import suggest_cerpa_stage
from .models import (
    CogArtifactRef,
    CogBundle,
    CogManifest,
    CogProof,
    DeepSigmaDecisionArtifact,
    DeepSigmaReceipt,
    DeepSigmaReplayRecord,
)


def load_cog_bundle(path: str) -> CogBundle:
    """Load a COG-compatible JSON bundle from *path*.

    Missing sections become None or empty — never invented.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    data: Dict[str, Any] = json.loads(text)
    return CogBundle.from_dict(data)


def cog_to_deepsigma(bundle: CogBundle) -> DeepSigmaDecisionArtifact:
    """Convert a CogBundle into a DeepSigmaDecisionArtifact.

    Maps artifact refs by ref_type:
        evidence  -> truth_claims
        rationale -> reasoning
        memory    -> memory_refs
        drift     -> drift_annotations
        patch     -> patch_refs

    Missing fields are preserved as empty, never fabricated.
    """
    truth_claims: List[Dict[str, Any]] = []
    reasoning: Dict[str, Any] = {}
    memory_refs: List[Dict[str, Any]] = []
    drift_annotations: List[Dict[str, Any]] = []
    patch_refs: List[Dict[str, Any]] = []

    for artifact in bundle.artifacts:
        ref_dict = artifact.to_dict()
        rt = artifact.ref_type.lower()

        if rt == "evidence":
            truth_claims.append(ref_dict)
        elif rt == "rationale":
            reasoning = ref_dict.get("payload", ref_dict)
        elif rt == "memory":
            memory_refs.append(ref_dict)
        elif rt == "drift":
            drift_annotations.append(ref_dict)
        elif rt == "patch":
            patch_refs.append(ref_dict)
        else:
            # Unknown ref_type — suggest CERPA stage via heuristics
            suggestion = suggest_cerpa_stage(artifact.payload, rt)
            ref_dict["_suggestion"] = suggestion.to_dict()
            truth_claims.append(ref_dict)

    # Build receipt from proof metadata
    receipt = None
    if bundle.proof is not None:
        receipt = DeepSigmaReceipt(
            artifact_id=bundle.manifest.bundle_id,
            proof_metadata=bundle.proof.to_dict(),
            source_bundle_id=bundle.manifest.bundle_id,
        )

    # Build replay record
    replay = None
    if bundle.replay_steps:
        replay = DeepSigmaReplayRecord(
            record_id=f"replay-{bundle.manifest.bundle_id}",
            artifact_id=bundle.manifest.bundle_id,
            steps=[s.to_dict() for s in bundle.replay_steps],
            lineage={"sourceBundleId": bundle.manifest.bundle_id},
        )

    return DeepSigmaDecisionArtifact(
        artifact_id=bundle.manifest.bundle_id,
        truth_claims=truth_claims,
        reasoning=reasoning,
        memory_refs=memory_refs,
        drift_annotations=drift_annotations,
        patch_refs=patch_refs,
        receipt=receipt,
        replay=replay,
        metadata=bundle.raw_metadata,
    )


def stream_cog_artifacts(path: str) -> Iterator[CogArtifactRef]:
    """Yield artifacts from a COG bundle one at a time.

    Loads the full JSON (no ``ijson`` dependency) but yields artifacts
    lazily so downstream pipelines can process them without holding all
    converted results in memory simultaneously.  A future version could
    swap in ``ijson`` for true streaming on very large bundles.
    """
    p = Path(path)
    data: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    for artifact_data in data.get("artifacts", []):
        yield CogArtifactRef.from_dict(artifact_data)


def load_cog_bundle_metadata(
    path: str,
) -> Tuple[CogManifest, Optional[CogProof]]:
    """Load only the manifest and proof from a COG bundle.

    Useful for batch listing or quick inspection without parsing all
    artifacts.
    """
    p = Path(path)
    data: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    manifest = CogManifest.from_dict(data.get("manifest", {}))
    proof_data = data.get("proof")
    proof = CogProof.from_dict(proof_data) if proof_data else None
    return manifest, proof
