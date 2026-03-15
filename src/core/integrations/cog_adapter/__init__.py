"""COG Adapter — portable cognition/proof bundle interoperability.

Provides import, export, verification, and replay extraction for
COG-compatible bundles. This is an integration adapter, not a core
primitive.

Public API::

    from core.integrations.cog_adapter import (
        # Models
        CogBundle, CogManifest, CogProof, CogReplayStep, CogArtifactRef,
        DeepSigmaDecisionArtifact, DeepSigmaReceipt, DeepSigmaReplayRecord,
        # Import
        load_cog_bundle, cog_to_deepsigma,
        # Export
        deepsigma_to_cog, write_cog_bundle,
        # Verify
        verify_cog_bundle,
        # Replay
        extract_replay_sequence, to_deepsigma_replay_record,
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
from .importer import cog_to_deepsigma, load_cog_bundle
from .exporter import deepsigma_to_cog, write_cog_bundle
from .verifier import verify_cog_bundle
from .replay import extract_replay_sequence, to_deepsigma_replay_record

__all__ = [
    "CogArtifactRef",
    "CogBundle",
    "CogManifest",
    "CogProof",
    "CogReplayStep",
    "DeepSigmaDecisionArtifact",
    "DeepSigmaReceipt",
    "DeepSigmaReplayRecord",
    "cog_to_deepsigma",
    "deepsigma_to_cog",
    "extract_replay_sequence",
    "load_cog_bundle",
    "to_deepsigma_replay_record",
    "verify_cog_bundle",
    "write_cog_bundle",
]
