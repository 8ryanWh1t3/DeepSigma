"""COG Adapter — portable cognition/proof bundle interoperability.

Provides import, export, verification, replay extraction, proof chain
construction, bundle diffing, batch operations, and streaming for
COG-compatible bundles. This is an integration adapter, not a core
primitive.

Public API::

    from core.integrations.cog_adapter import (
        # Models
        CogBundle, CogManifest, CogProof, CogReplayStep, CogArtifactRef,
        DeepSigmaDecisionArtifact, DeepSigmaReceipt, DeepSigmaReplayRecord,
        # Import
        load_cog_bundle, cog_to_deepsigma,
        stream_cog_artifacts, load_cog_bundle_metadata,
        # Export
        deepsigma_to_cog, write_cog_bundle,
        # Verify
        verify_cog_bundle,
        # Replay
        extract_replay_sequence, to_deepsigma_replay_record,
        # Proof Chain
        build_proof_chain, verify_proof_chain,
        # Diff
        CogBundleDiff, diff_cog_bundles,
        # Batch
        BatchImportResult, batch_import_cog_bundles,
        batch_export_deepsigma, filter_artifacts, merge_bundles,
    )
"""

from .models import (
    CogArtifactRef,
    CogBundle,
    CogManifest,
    CogProof,
    CogReplayStep,
    DeepSigmaDecisionArtifact,
    DeepSigmaReceipt,
    DeepSigmaReplayRecord,
)
from .importer import (
    cog_to_deepsigma,
    load_cog_bundle,
    load_cog_bundle_metadata,
    stream_cog_artifacts,
)
from .exporter import deepsigma_to_cog, write_cog_bundle
from .verifier import verify_cog_bundle
from .replay import extract_replay_sequence, to_deepsigma_replay_record
from .proof_chain import build_proof_chain, verify_proof_chain
from .diff import CogBundleDiff, diff_cog_bundles
from .batch import (
    BatchImportResult,
    batch_export_deepsigma,
    batch_import_cog_bundles,
    filter_artifacts,
    merge_bundles,
)

__all__ = [
    "BatchImportResult",
    "CogArtifactRef",
    "CogBundle",
    "CogBundleDiff",
    "CogManifest",
    "CogProof",
    "CogReplayStep",
    "DeepSigmaDecisionArtifact",
    "DeepSigmaReceipt",
    "DeepSigmaReplayRecord",
    "batch_export_deepsigma",
    "batch_import_cog_bundles",
    "build_proof_chain",
    "cog_to_deepsigma",
    "deepsigma_to_cog",
    "diff_cog_bundles",
    "extract_replay_sequence",
    "filter_artifacts",
    "load_cog_bundle",
    "load_cog_bundle_metadata",
    "merge_bundles",
    "stream_cog_artifacts",
    "to_deepsigma_replay_record",
    "verify_cog_bundle",
    "verify_proof_chain",
    "write_cog_bundle",
]
