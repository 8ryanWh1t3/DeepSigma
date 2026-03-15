"""COG batch operations — multi-bundle import/export, filter, and merge.

Functions:
    batch_import_cog_bundles — import multiple COG bundles from a list of paths
    batch_export_deepsigma   — export multiple DeepSigma artifacts as COG bundles
    filter_artifacts         — filter bundle artifacts by ref_type
    merge_bundles            — combine multiple bundles into one
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

from .models import (
    CogArtifactRef,
    CogBundle,
    CogManifest,
    CogReplayStep,
    DeepSigmaDecisionArtifact,
)


@dataclass
class BatchImportResult:
    """Aggregate result for batch import/export operations."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "results": self.results,
            "errors": self.errors,
        }


def batch_import_cog_bundles(paths: List[str]) -> BatchImportResult:
    """Import multiple COG bundles and convert to DeepSigma artifacts.

    Each path is processed independently — failures do not block other
    imports.
    """
    from .importer import cog_to_deepsigma, load_cog_bundle

    result = BatchImportResult(total=len(paths))

    for path in paths:
        try:
            bundle = load_cog_bundle(path)
            artifact = cog_to_deepsigma(bundle)
            result.succeeded += 1
            result.results.append({
                "path": path,
                "bundleId": bundle.manifest.bundle_id,
                "artifactId": artifact.artifact_id,
                "artifactCount": len(bundle.artifacts),
            })
        except Exception as exc:
            result.failed += 1
            result.errors.append(f"{path}: {exc}")

    return result


def batch_export_deepsigma(
    artifacts: List[DeepSigmaDecisionArtifact],
    output_dir: str,
) -> BatchImportResult:
    """Export multiple DeepSigma artifacts as COG bundles.

    Each artifact is written to ``output_dir/{artifact_id}.cog.json``.
    """
    from .exporter import deepsigma_to_cog, write_cog_bundle

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = BatchImportResult(total=len(artifacts))

    for artifact in artifacts:
        try:
            bundle = deepsigma_to_cog(artifact)
            path = str(out / f"{artifact.artifact_id}.cog.json")
            write_cog_bundle(bundle, path)
            result.succeeded += 1
            result.results.append({
                "artifactId": artifact.artifact_id,
                "path": path,
                "bundleId": bundle.manifest.bundle_id,
            })
        except Exception as exc:
            result.failed += 1
            result.errors.append(f"{artifact.artifact_id}: {exc}")

    return result


def filter_artifacts(
    bundle: CogBundle,
    ref_types: Set[str],
) -> List[CogArtifactRef]:
    """Return artifacts from *bundle* whose ref_type is in *ref_types*."""
    return [a for a in bundle.artifacts if a.ref_type in ref_types]


def merge_bundles(bundles: List[CogBundle]) -> CogBundle:
    """Merge multiple CogBundles into a single bundle.

    Artifacts are de-duplicated by ``ref_id`` — later bundles win on
    conflict. A fresh proof chain is built over the merged artifact set.
    Replay steps from all bundles are concatenated and re-indexed.
    """
    from .proof_chain import build_proof_chain

    if not bundles:
        raise ValueError("merge_bundles requires at least one bundle")

    seen: Dict[str, CogArtifactRef] = {}
    all_replay: List[CogReplayStep] = []
    metadata: Dict[str, Any] = {}

    for bundle in bundles:
        for artifact in bundle.artifacts:
            seen[artifact.ref_id] = artifact
        all_replay.extend(bundle.replay_steps)
        metadata.update(bundle.raw_metadata)

    artifacts = list(seen.values())
    now = datetime.now(timezone.utc).isoformat()

    # Re-index replay steps
    replay_steps = []
    for i, step in enumerate(all_replay):
        replay_steps.append(CogReplayStep(
            step_index=i,
            action=step.action,
            input_ref=step.input_ref,
            output_ref=step.output_ref,
            timestamp=step.timestamp,
            metadata=step.metadata,
        ))

    # Build proof chain
    from .models import CogProof

    chain = build_proof_chain(artifacts)
    proof = CogProof(proof_chain=chain, timestamps=[now])

    merge_id = f"merged-{uuid.uuid4().hex[:8]}"
    manifest = CogManifest(
        bundle_id=merge_id,
        version="1.0",
        created_at=now,
        description=f"Merged from {len(bundles)} bundles",
        artifact_refs=[a.ref_id for a in artifacts],
        metadata=metadata,
    )

    return CogBundle(
        manifest=manifest,
        artifacts=artifacts,
        proof=proof,
        replay_steps=replay_steps,
        raw_metadata=metadata,
    )
