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
        assert len(bundle.proof.proof_chain) == 5  # one per artifact
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


# ── Schema validation tests ──────────────────────────────────────


class TestSchemaValidation:
    """Test JSON Schema validation of COG bundles."""

    def test_valid_bundle_passes_schema(self, sample_bundle_data):
        """A well-formed bundle should pass schema validation."""
        from core.schema_validator import clear_cache, validate

        clear_cache()
        result = validate(sample_bundle_data, "cog_bundle")
        assert result.valid, result.errors

    def test_missing_bundle_id_fails(self, sample_bundle_data):
        """A bundle with no bundleId should fail validation."""
        from core.schema_validator import clear_cache, validate

        clear_cache()
        data = copy.deepcopy(sample_bundle_data)
        del data["manifest"]["bundleId"]
        result = validate(data, "cog_bundle")
        assert not result.valid

    def test_invalid_ref_type_fails(self, sample_bundle_data):
        """An artifact with an invalid refType should fail validation."""
        from core.schema_validator import clear_cache, validate

        clear_cache()
        data = copy.deepcopy(sample_bundle_data)
        data["artifacts"][0]["refType"] = "invalid_type"
        result = validate(data, "cog_bundle")
        assert not result.valid

    def test_optional_fields_omitted(self):
        """A minimal bundle with only manifest should pass."""
        from core.schema_validator import clear_cache, validate

        clear_cache()
        data = {"manifest": {"bundleId": "minimal-001"}}
        result = validate(data, "cog_bundle")
        assert result.valid, result.errors


# ── Proof chain tests ────────────────────────────────────────────


class TestProofChain:
    """Test per-artifact proof chain build and verify."""

    def test_build_chain_length(self, minimal_ds_artifact):
        """Chain should have one entry per artifact."""
        from core.integrations.cog_adapter import deepsigma_to_cog
        from core.integrations.cog_adapter.proof_chain import build_proof_chain

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        chain = build_proof_chain(bundle.artifacts)
        assert len(chain) == len(bundle.artifacts)

    def test_verify_untampered_chain(self, minimal_ds_artifact):
        """A freshly built chain should verify cleanly."""
        from core.integrations.cog_adapter import deepsigma_to_cog
        from core.integrations.cog_adapter.proof_chain import (
            build_proof_chain,
            verify_proof_chain,
        )

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        chain = build_proof_chain(bundle.artifacts)
        valid, errors = verify_proof_chain(chain)
        assert valid, errors

    def test_detect_tampered_link(self, minimal_ds_artifact):
        """Tampering with a chainHash should be detected."""
        from core.integrations.cog_adapter import deepsigma_to_cog
        from core.integrations.cog_adapter.proof_chain import (
            build_proof_chain,
            verify_proof_chain,
        )

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        chain = build_proof_chain(bundle.artifacts)
        chain[1]["chainHash"] = "sha256:tampered"
        valid, errors = verify_proof_chain(chain)
        assert not valid
        assert any("chainHash mismatch" in e for e in errors)

    def test_empty_chain_valid(self):
        """An empty chain is valid."""
        from core.integrations.cog_adapter.proof_chain import verify_proof_chain

        valid, errors = verify_proof_chain([])
        assert valid
        assert errors == []


# ── Diff tests ───────────────────────────────────────────────────


class TestDiff:
    """Test bundle diff/compare."""

    def test_identical_bundles(self, sample_bundle):
        """Diffing identical bundles should show no changes."""
        from core.integrations.cog_adapter.diff import diff_cog_bundles

        diff = diff_cog_bundles(sample_bundle, sample_bundle)
        assert diff.added_artifacts == []
        assert diff.removed_artifacts == []
        assert diff.modified_artifacts == []

    def test_added_artifact(self, sample_bundle):
        """An artifact present only in 'after' is detected as added."""
        from core.integrations.cog_adapter.diff import diff_cog_bundles
        from core.integrations.cog_adapter.models import CogArtifactRef, CogBundle

        after = CogBundle(
            manifest=sample_bundle.manifest,
            artifacts=sample_bundle.artifacts + [
                CogArtifactRef(ref_id="new-001", ref_type="evidence"),
            ],
            proof=sample_bundle.proof,
            replay_steps=sample_bundle.replay_steps,
        )
        diff = diff_cog_bundles(sample_bundle, after)
        assert len(diff.added_artifacts) == 1
        assert diff.added_artifacts[0]["refId"] == "new-001"

    def test_removed_artifact(self, sample_bundle):
        """An artifact present only in 'before' is detected as removed."""
        from core.integrations.cog_adapter.diff import diff_cog_bundles
        from core.integrations.cog_adapter.models import CogBundle

        after = CogBundle(
            manifest=sample_bundle.manifest,
            artifacts=sample_bundle.artifacts[1:],  # drop first
            proof=sample_bundle.proof,
            replay_steps=sample_bundle.replay_steps,
        )
        diff = diff_cog_bundles(sample_bundle, after)
        assert len(diff.removed_artifacts) == 1
        assert diff.removed_artifacts[0]["refId"] == sample_bundle.artifacts[0].ref_id

    def test_modified_artifact(self, sample_bundle):
        """An artifact with changed hash is detected as modified."""
        from core.integrations.cog_adapter.diff import diff_cog_bundles
        from core.integrations.cog_adapter.models import CogArtifactRef, CogBundle

        modified_art = CogArtifactRef(
            ref_id=sample_bundle.artifacts[0].ref_id,
            ref_type=sample_bundle.artifacts[0].ref_type,
            content_hash="sha256:changed",
            payload=sample_bundle.artifacts[0].payload,
        )
        after = CogBundle(
            manifest=sample_bundle.manifest,
            artifacts=[modified_art] + sample_bundle.artifacts[1:],
            proof=sample_bundle.proof,
            replay_steps=sample_bundle.replay_steps,
        )
        diff = diff_cog_bundles(sample_bundle, after)
        assert len(diff.modified_artifacts) == 1
        assert diff.modified_artifacts[0]["afterHash"] == "sha256:changed"


# ── Batch tests ──────────────────────────────────────────────────


class TestBatch:
    """Test batch import/export, filter, and merge."""

    def test_batch_import(self, tmp_path, minimal_ds_artifact):
        """Batch import a directory of bundles."""
        from core.integrations.cog_adapter import deepsigma_to_cog, write_cog_bundle
        from core.integrations.cog_adapter.batch import batch_import_cog_bundles

        # Write two bundle files
        for suffix in ("a", "b"):
            bundle = deepsigma_to_cog(minimal_ds_artifact)
            write_cog_bundle(bundle, str(tmp_path / f"bundle_{suffix}.json"))

        result = batch_import_cog_bundles([
            str(tmp_path / "bundle_a.json"),
            str(tmp_path / "bundle_b.json"),
        ])
        assert result.total == 2
        assert result.succeeded == 2
        assert result.failed == 0

    def test_batch_export(self, tmp_path, minimal_ds_artifact):
        """Batch export multiple artifacts."""
        from core.integrations.cog_adapter.batch import batch_export_deepsigma

        result = batch_export_deepsigma([minimal_ds_artifact], str(tmp_path))
        assert result.succeeded == 1
        assert (tmp_path / "ds-artifact-001.cog.json").exists()

    def test_filter_artifacts(self, sample_bundle):
        """Filter artifacts by ref_type."""
        from core.integrations.cog_adapter.batch import filter_artifacts

        evidence = filter_artifacts(sample_bundle, {"evidence"})
        assert len(evidence) == 1
        assert evidence[0].ref_type == "evidence"

        multi = filter_artifacts(sample_bundle, {"evidence", "drift"})
        assert len(multi) == 2

    def test_merge_bundles(self, sample_bundle):
        """Merge two bundles with deduplication."""
        from core.integrations.cog_adapter.batch import merge_bundles
        from core.integrations.cog_adapter.models import CogArtifactRef, CogBundle, CogManifest

        other = CogBundle(
            manifest=CogManifest(bundle_id="other-001"),
            artifacts=[
                CogArtifactRef(ref_id="new-evidence-001", ref_type="evidence"),
                # duplicate from sample_bundle
                sample_bundle.artifacts[0],
            ],
        )
        merged = merge_bundles([sample_bundle, other])
        ref_ids = [a.ref_id for a in merged.artifacts]
        # Deduplication: sample_bundle's artifact[0] should appear once
        assert ref_ids.count(sample_bundle.artifacts[0].ref_id) == 1
        assert "new-evidence-001" in ref_ids
        assert merged.manifest.bundle_id.startswith("merged-")


# ── Streaming tests ──────────────────────────────────────────────


class TestStreaming:
    """Test streaming artifact import."""

    def test_stream_cog_artifacts(self):
        """Stream yields correct number of artifacts."""
        from core.integrations.cog_adapter.importer import stream_cog_artifacts

        artifacts = list(stream_cog_artifacts(str(SAMPLE_BUNDLE_PATH)))
        assert len(artifacts) == 5
        assert artifacts[0].ref_id == "evidence-001"

    def test_stream_empty_bundle(self, tmp_path):
        """Stream from a bundle with no artifacts yields nothing."""
        import json
        from core.integrations.cog_adapter.importer import stream_cog_artifacts

        path = tmp_path / "empty.json"
        path.write_text(json.dumps({"manifest": {"bundleId": "empty"}}))
        artifacts = list(stream_cog_artifacts(str(path)))
        assert artifacts == []

    def test_load_metadata_only(self):
        """Metadata-only load returns manifest and proof without artifacts."""
        from core.integrations.cog_adapter.importer import load_cog_bundle_metadata

        manifest, proof = load_cog_bundle_metadata(str(SAMPLE_BUNDLE_PATH))
        assert manifest.bundle_id == "cog-bundle-demo-001"
        assert proof is not None


# ── Heuristic suggestion tests ───────────────────────────────────


class TestHeuristics:
    """Test CERPA stage heuristic suggestions for unmapped refTypes."""

    def test_suggest_patch_like(self):
        """Payload with patch signals should suggest Apply stage."""
        from core.integrations.cog_adapter.heuristics import suggest_cerpa_stage

        payload = {"patchId": "p-1", "action": "adjust", "target": "policy-7"}
        result = suggest_cerpa_stage(payload, "custom_fix")
        assert result.suggested_ref_type == "patch"
        assert result.suggested_cerpa_stage == "Apply"
        assert result.confidence > 0.0
        assert "action" in result.signals

    def test_suggest_drift_like(self):
        """Payload with drift signals should suggest Review stage."""
        from core.integrations.cog_adapter.heuristics import suggest_cerpa_stage

        payload = {"severity": "high", "observed_state": "degraded", "trigger": "alert"}
        result = suggest_cerpa_stage(payload, "anomaly_report")
        assert result.suggested_ref_type == "drift"
        assert result.suggested_cerpa_stage == "Review"
        assert result.confidence > 0.0

    def test_suggest_memory_like(self):
        """Payload with memory signals should suggest Apply stage."""
        from core.integrations.cog_adapter.heuristics import suggest_cerpa_stage

        payload = {"precedentId": "prec-42", "recall": "last quarter", "takeaway": "ok"}
        result = suggest_cerpa_stage(payload, "historical_ref")
        assert result.suggested_ref_type == "memory"
        assert result.suggested_cerpa_stage == "Apply"
        assert result.confidence > 0.0

    def test_suggest_unknown_default(self):
        """Payload with no matching signals defaults to evidence/Claim."""
        from core.integrations.cog_adapter.heuristics import suggest_cerpa_stage

        payload = {"foo": "bar", "baz": 42}
        result = suggest_cerpa_stage(payload, "totally_unknown")
        assert result.suggested_ref_type == "evidence"
        assert result.suggested_cerpa_stage == "Claim"
        assert result.confidence == 0.0
        assert result.signals == []

    def test_importer_attaches_suggestion(self):
        """Unknown refType in import should have _suggestion metadata."""
        from core.integrations.cog_adapter.importer import cog_to_deepsigma
        from core.integrations.cog_adapter.models import (
            CogArtifactRef, CogBundle, CogManifest,
        )

        bundle = CogBundle(
            manifest=CogManifest(bundle_id="test-heur-001"),
            artifacts=[
                CogArtifactRef(
                    ref_id="unk-001",
                    ref_type="custom_audit",
                    payload={"severity": "low", "trigger": "scan"},
                ),
            ],
        )
        ds = cog_to_deepsigma(bundle)
        assert len(ds.truth_claims) == 1
        suggestion = ds.truth_claims[0].get("_suggestion")
        assert suggestion is not None
        assert suggestion["suggestedRefType"] == "drift"


# ── SBOM tests ───────────────────────────────────────────────────


class TestSBOM:
    """Test CycloneDX 1.5 and SPDX 2.3 SBOM generation from COG bundles."""

    def test_sbom_cyclonedx_structure(self, minimal_ds_artifact):
        """CycloneDX SBOM has correct format, version, and component count."""
        from core.integrations.cog_adapter import deepsigma_to_cog
        from core.integrations.cog_adapter.sbom import generate_cyclonedx_sbom

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        sbom = generate_cyclonedx_sbom(bundle)

        assert sbom["bomFormat"] == "CycloneDX"
        assert sbom["specVersion"] == "1.5"
        assert sbom["serialNumber"].startswith("urn:uuid:")
        assert len(sbom["components"]) == len(bundle.artifacts)

    def test_sbom_spdx_structure(self, minimal_ds_artifact):
        """SPDX SBOM has correct version, license, and package count."""
        from core.integrations.cog_adapter import deepsigma_to_cog
        from core.integrations.cog_adapter.sbom import generate_spdx_sbom

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        sbom = generate_spdx_sbom(bundle)

        assert sbom["spdxVersion"] == "SPDX-2.3"
        assert sbom["dataLicense"] == "CC0-1.0"
        assert len(sbom["packages"]) == len(bundle.artifacts)
        assert len(sbom["relationships"]) == len(bundle.artifacts)

    def test_sbom_artifact_mapping(self, minimal_ds_artifact):
        """Each artifact refType appears in CycloneDX properties and SPDX description."""
        from core.integrations.cog_adapter import deepsigma_to_cog
        from core.integrations.cog_adapter.sbom import (
            generate_cyclonedx_sbom,
            generate_spdx_sbom,
        )

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        cdx = generate_cyclonedx_sbom(bundle)
        spdx = generate_spdx_sbom(bundle)

        for i, artifact in enumerate(bundle.artifacts):
            # CycloneDX: refType in properties
            props = cdx["components"][i]["properties"]
            ref_type_values = [p["value"] for p in props if p["name"] == "cog:refType"]
            assert artifact.ref_type in ref_type_values

            # SPDX: refType in description
            assert artifact.ref_type in spdx["packages"][i]["description"]

    def test_sbom_hash_integrity(self, minimal_ds_artifact):
        """Content hashes in SBOMs match the original artifact hashes."""
        from core.integrations.cog_adapter import deepsigma_to_cog
        from core.integrations.cog_adapter.sbom import (
            generate_cyclonedx_sbom,
            generate_spdx_sbom,
        )

        bundle = deepsigma_to_cog(minimal_ds_artifact)
        cdx = generate_cyclonedx_sbom(bundle)
        spdx = generate_spdx_sbom(bundle)

        for i, artifact in enumerate(bundle.artifacts):
            expected = artifact.content_hash.replace("sha256:", "")

            # CycloneDX hash
            cdx_hash = cdx["components"][i]["hashes"][0]["content"]
            assert cdx_hash == expected

            # SPDX hash
            spdx_hash = spdx["packages"][i]["checksums"][0]["checksumValue"]
            assert spdx_hash == expected
