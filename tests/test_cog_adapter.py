"""Tests for COG Adapter — import, export, verify, replay, round-trip."""

from __future__ import annotations

import json
import copy
from pathlib import Path

import pytest

# ── Fixture path ──────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_BUNDLE_PATH = (
    _REPO_ROOT / "src" / "core" / "fixtures" / "cog_adapter" / "sample_cog_bundle.json"
)


@pytest.fixture
def sample_bundle_data():
    """Load the sample COG bundle fixture as a dict."""
    return json.loads(SAMPLE_BUNDLE_PATH.read_text())


@pytest.fixture
def sample_bundle(sample_bundle_data):
    """Parse sample fixture into a CogBundle."""
    from core.integrations.cog_adapter.models import CogBundle
    return CogBundle.from_dict(sample_bundle_data)


@pytest.fixture
def minimal_ds_artifact():
    """Create a minimal DeepSigmaDecisionArtifact for export tests."""
    from core.integrations.cog_adapter.models import (
        DeepSigmaDecisionArtifact,
        DeepSigmaReceipt,
        DeepSigmaReplayRecord,
    )
    return DeepSigmaDecisionArtifact(
        artifact_id="ds-artifact-001",
        truth_claims=[{
            "claimId": "CLAIM-001",
            "statement": "System is healthy",
            "confidence": 0.95,
        }],
        reasoning={
            "decisionId": "DEC-001",
            "goal": "Determine system health",
            "selectedOption": "no-action",
        },
        memory_refs=[{
            "precedentId": "PREC-001",
            "takeaway": "Previous incident was a false alarm",
        }],
        drift_annotations=[{
            "driftId": "DRIFT-001",
            "severity": "green",
        }],
        patch_refs=[{
            "patchId": "PATCH-001",
            "action": "update-threshold",
        }],
        receipt=DeepSigmaReceipt(
            artifact_id="ds-artifact-001",
            seal_hash="sha256:abc123",
            sealed_at="2026-03-15T12:00:00Z",
        ),
        replay=DeepSigmaReplayRecord(
            record_id="replay-ds-001",
            artifact_id="ds-artifact-001",
            steps=[
                {"stepIndex": 0, "action": "observe", "timestamp": "2026-03-15T11:00:00Z"},
                {"stepIndex": 1, "action": "decide", "timestamp": "2026-03-15T11:01:00Z"},
            ],
        ),
    )


# ── Import tests ──────────────────────────────────────────────────


class TestImport:
    """Test COG bundle import."""

    def test_load_cog_bundle(self):
        """Load the sample fixture and verify structure."""
        from core.integrations.cog_adapter import load_cog_bundle

        bundle = load_cog_bundle(str(SAMPLE_BUNDLE_PATH))

        assert bundle.manifest.bundle_id == "cog-bundle-demo-001"
        assert bundle.manifest.version == "1.0"
        assert len(bundle.artifacts) == 5
        assert bundle.proof is not None
        assert len(bundle.replay_steps) == 5

    def test_load_bundle_artifact_types(self, sample_bundle):
        """Verify each artifact ref_type is parsed."""
        types = {a.ref_type for a in sample_bundle.artifacts}
        assert types == {"evidence", "rationale", "memory", "drift", "patch"}

    def test_cog_to_deepsigma(self, sample_bundle):
        """Convert bundle to DeepSigma artifact and verify mapping."""
        from core.integrations.cog_adapter import cog_to_deepsigma

        artifact = cog_to_deepsigma(sample_bundle)

        assert artifact.artifact_id == "cog-bundle-demo-001"
        assert len(artifact.truth_claims) == 1
        assert artifact.reasoning  # not empty
        assert len(artifact.memory_refs) == 1
        assert len(artifact.drift_annotations) == 1
        assert len(artifact.patch_refs) == 1
        assert artifact.receipt is not None
        assert artifact.replay is not None
        assert len(artifact.replay.steps) == 5

    def test_import_missing_proof(self, sample_bundle_data):
        """Import a bundle with no proof section — should not crash."""
        from core.integrations.cog_adapter.models import CogBundle
        from core.integrations.cog_adapter import cog_to_deepsigma

        data = copy.deepcopy(sample_bundle_data)
        del data["proof"]
        bundle = CogBundle.from_dict(data)
        artifact = cog_to_deepsigma(bundle)

        assert artifact.receipt is None

    def test_import_missing_replay(self, sample_bundle_data):
        """Import a bundle with no replay steps — should not crash."""
        from core.integrations.cog_adapter.models import CogBundle
        from core.integrations.cog_adapter import cog_to_deepsigma

        data = copy.deepcopy(sample_bundle_data)
        del data["replaySteps"]
        bundle = CogBundle.from_dict(data)
        artifact = cog_to_deepsigma(bundle)

        assert artifact.replay is None


# ── Export tests ──────────────────────────────────────────────────


class TestExport:
    """Test COG bundle export."""

    def test_deepsigma_to_cog(self, minimal_ds_artifact):
        """Export a DeepSigma artifact and verify bundle structure."""
        from core.integrations.cog_adapter import deepsigma_to_cog

        bundle = deepsigma_to_cog(minimal_ds_artifact)

        assert bundle.manifest.bundle_id == "ds-artifact-001"
        assert len(bundle.artifacts) == 5  # 1 evidence + 1 rationale + 1 memory + 1 drift + 1 patch
        assert bundle.proof is not None
        assert len(bundle.proof.proof_chain) == 1
        assert len(bundle.replay_steps) == 2

    def test_export_artifact_types(self, minimal_ds_artifact):
        """Verify exported artifact ref_types."""
        from core.integrations.cog_adapter import deepsigma_to_cog

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        types = {a.ref_type for a in bundle.artifacts}
        assert types == {"evidence", "rationale", "memory", "drift", "patch"}

    def test_export_content_hashes(self, minimal_ds_artifact):
        """Verify all exported artifacts have content hashes."""
        from core.integrations.cog_adapter import deepsigma_to_cog

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        for artifact in bundle.artifacts:
            assert artifact.content_hash.startswith("sha256:")

    def test_write_cog_bundle(self, minimal_ds_artifact, tmp_path):
        """Write a COG bundle to disk and verify it's valid JSON."""
        from core.integrations.cog_adapter import deepsigma_to_cog, write_cog_bundle

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        out_path = tmp_path / "test_bundle.json"
        write_cog_bundle(bundle, str(out_path))

        assert out_path.exists()
        data = json.loads(out_path.read_text())
        assert "manifest" in data
        assert "artifacts" in data
        assert "proof" in data


# ── Verify tests ──────────────────────────────────────────────────


class TestVerify:
    """Test COG bundle verification."""

    def test_verify_valid_exported_bundle(self, minimal_ds_artifact):
        """A freshly exported bundle should pass verification."""
        from core.integrations.cog_adapter import deepsigma_to_cog, verify_cog_bundle

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        result = verify_cog_bundle(bundle)

        assert result["status"] == "pass"
        assert result["content_hash_valid"] is True
        assert result["manifest_consistent"] is True
        assert result["proof_metadata_present"] is True

    def test_verify_missing_proof(self, sample_bundle_data):
        """Bundle without proof should return 'warn'."""
        from core.integrations.cog_adapter.models import CogBundle
        from core.integrations.cog_adapter import verify_cog_bundle

        data = copy.deepcopy(sample_bundle_data)
        del data["proof"]
        bundle = CogBundle.from_dict(data)
        result = verify_cog_bundle(bundle)

        assert result["status"] == "warn"
        assert result["proof_metadata_present"] is False

    def test_verify_tampered_hash(self, minimal_ds_artifact):
        """Tampered content hash should return 'fail'."""
        from core.integrations.cog_adapter import deepsigma_to_cog, verify_cog_bundle

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        # Tamper with the first artifact's hash
        bundle.artifacts[0].content_hash = "sha256:tampered"
        result = verify_cog_bundle(bundle)

        assert result["status"] == "fail"
        assert result["content_hash_valid"] is False

    def test_verify_manifest_inconsistency(self, minimal_ds_artifact):
        """Manifest refs not matching artifacts should return 'fail'."""
        from core.integrations.cog_adapter import deepsigma_to_cog, verify_cog_bundle

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        bundle.manifest.artifact_refs.append("nonexistent-ref")
        result = verify_cog_bundle(bundle)

        assert result["status"] == "fail"
        assert result["manifest_consistent"] is False


# ── Replay tests ──────────────────────────────────────────────────


class TestReplay:
    """Test replay extraction."""

    def test_extract_replay_sequence(self, sample_bundle):
        """Extract replay steps in sorted order."""
        from core.integrations.cog_adapter import extract_replay_sequence

        steps = extract_replay_sequence(sample_bundle)

        assert len(steps) == 5
        assert steps[0].step_index == 0
        assert steps[4].step_index == 4
        assert steps[0].action == "ingest_evidence"

    def test_extract_empty_replay(self, sample_bundle_data):
        """Empty replay should return empty list."""
        from core.integrations.cog_adapter.models import CogBundle
        from core.integrations.cog_adapter import extract_replay_sequence

        data = copy.deepcopy(sample_bundle_data)
        del data["replaySteps"]
        bundle = CogBundle.from_dict(data)

        steps = extract_replay_sequence(bundle)
        assert steps == []

    def test_to_deepsigma_replay_record(self, sample_bundle):
        """Convert to DeepSigma replay record."""
        from core.integrations.cog_adapter import to_deepsigma_replay_record

        record = to_deepsigma_replay_record(sample_bundle)

        assert record.record_id == "replay-cog-bundle-demo-001"
        assert record.artifact_id == "cog-bundle-demo-001"
        assert len(record.steps) == 5
        assert record.lineage["stepCount"] == 5


# ── Round-trip tests ──────────────────────────────────────────────


class TestRoundTrip:
    """Test import/export round-trip without silent field loss."""

    def test_round_trip_no_field_loss(self, minimal_ds_artifact):
        """Export -> import should preserve all five primitive categories."""
        from core.integrations.cog_adapter import (
            cog_to_deepsigma,
            deepsigma_to_cog,
        )

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        reimported = cog_to_deepsigma(bundle)

        # All five primitives should be present
        assert len(reimported.truth_claims) == len(minimal_ds_artifact.truth_claims)
        assert bool(reimported.reasoning) == bool(minimal_ds_artifact.reasoning)
        assert len(reimported.memory_refs) == len(minimal_ds_artifact.memory_refs)
        assert len(reimported.drift_annotations) == len(minimal_ds_artifact.drift_annotations)
        assert len(reimported.patch_refs) == len(minimal_ds_artifact.patch_refs)

    def test_round_trip_verify_passes(self, minimal_ds_artifact):
        """Exported bundle should pass verification after round-trip."""
        from core.integrations.cog_adapter import (
            deepsigma_to_cog,
            verify_cog_bundle,
        )

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        result = verify_cog_bundle(bundle)
        assert result["status"] == "pass"

    def test_round_trip_file_io(self, minimal_ds_artifact, tmp_path):
        """Export to file -> import from file round-trip."""
        from core.integrations.cog_adapter import (
            cog_to_deepsigma,
            deepsigma_to_cog,
            load_cog_bundle,
            write_cog_bundle,
        )

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        path = str(tmp_path / "round_trip.json")
        write_cog_bundle(bundle, path)

        reloaded = load_cog_bundle(path)
        reimported = cog_to_deepsigma(reloaded)

        assert reimported.artifact_id == minimal_ds_artifact.artifact_id
        assert len(reimported.truth_claims) == 1
        assert len(reimported.memory_refs) == 1
