"""Tests for the Golden Path end-to-end pipeline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURE_DIR = str(Path(__file__).parent.parent / "demos" / "golden_path" / "fixtures" / "sharepoint_small")


# ── Full Pipeline Tests ──────────────────────────────────────────────

class TestGoldenPathFullPipeline:

    def _run(self, output_dir):
        from demos.golden_path.config import GoldenPathConfig
        from demos.golden_path.pipeline import GoldenPathPipeline
        config = GoldenPathConfig(
            source="sharepoint",
            fixture_path=FIXTURE_DIR,
            output_dir=output_dir,
        )
        return GoldenPathPipeline(config).run()

    def test_all_seven_steps_complete(self, tmp_path):
        result = self._run(str(tmp_path))
        assert result.steps_completed == [
            "connect", "normalize", "extract", "seal", "drift", "patch", "recall",
        ]

    def test_canonical_records_count(self, tmp_path):
        result = self._run(str(tmp_path))
        assert result.canonical_records == 5

    def test_claims_extracted(self, tmp_path):
        result = self._run(str(tmp_path))
        assert result.claims_extracted == 5

    def test_episode_id(self, tmp_path):
        result = self._run(str(tmp_path))
        assert result.episode_id == "gp-demo"

    def test_baseline_score_positive(self, tmp_path):
        result = self._run(str(tmp_path))
        assert result.baseline_score > 0

    def test_baseline_grade_is_letter(self, tmp_path):
        result = self._run(str(tmp_path))
        assert result.baseline_grade in ("A", "B", "C", "D", "F")

    def test_drift_events_detected(self, tmp_path):
        result = self._run(str(tmp_path))
        assert result.drift_events > 0

    def test_patch_applied(self, tmp_path):
        result = self._run(str(tmp_path))
        assert result.patch_applied is True

    def test_patched_score_positive(self, tmp_path):
        result = self._run(str(tmp_path))
        assert result.patched_score > 0

    def test_iris_all_resolved(self, tmp_path):
        result = self._run(str(tmp_path))
        for qtype, status in result.iris_queries.items():
            assert status == "RESOLVED", f"IRIS {qtype} was {status}"

    def test_output_files_written(self, tmp_path):
        self._run(str(tmp_path))
        expected = [
            "step_1_connect/canonical_records.json",
            "step_2_normalize/episode.json",
            "step_3_extract/claims.json",
            "step_4_seal/dlr.json",
            "step_4_seal/coherence_report.json",
            "step_5_drift/drift_report.json",
            "step_6_patch/patch.json",
            "step_7_recall/iris_why.json",
            "step_7_recall/iris_status.json",
            "summary.json",
        ]
        for f in expected:
            assert (tmp_path / f).exists(), f"Missing: {f}"

    def test_summary_json_valid(self, tmp_path):
        self._run(str(tmp_path))
        data = json.loads((tmp_path / "summary.json").read_text())
        assert data["steps_completed"] == [
            "connect", "normalize", "extract", "seal", "drift", "patch", "recall",
        ]
        assert data["canonical_records"] == 5

    def test_to_dict(self, tmp_path):
        result = self._run(str(tmp_path))
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "steps_completed" in d
        assert "iris_queries" in d

    def test_matches_expected_summary(self, tmp_path):
        result = self._run(str(tmp_path))
        expected = json.loads(
            Path(FIXTURE_DIR, "expected_summary.json").read_text()
        )
        actual = result.to_dict()
        for key, val in expected.items():
            assert actual[key] == val, f"Mismatch on {key}: {actual[key]} != {val}"


# ── RecordToEpisodeAssembler Tests ───────────────────────────────────

class TestRecordToEpisodeAssembler:

    def _load_records(self):
        return json.loads(Path(FIXTURE_DIR, "baseline.json").read_text())

    def test_single_record(self):
        from demos.golden_path.assembler import RecordToEpisodeAssembler
        records = [self._load_records()[0]]
        episode = RecordToEpisodeAssembler().assemble(records, source_name="sharepoint")
        assert "episodeId" in episode
        assert episode["decisionType"] == "ingest"

    def test_multiple_records(self):
        from demos.golden_path.assembler import RecordToEpisodeAssembler
        records = self._load_records()
        episode = RecordToEpisodeAssembler().assemble(records, source_name="sharepoint")
        assert len(episode["context"]["evidenceRefs"]) == 5

    def test_episode_has_required_fields(self):
        from demos.golden_path.assembler import RecordToEpisodeAssembler
        records = self._load_records()
        ep = RecordToEpisodeAssembler().assemble(records, source_name="sharepoint")
        for field in ("episodeId", "decisionType", "startedAt", "actor",
                      "context", "plan", "actions", "verification",
                      "outcome", "telemetry", "seal"):
            assert field in ep, f"Missing: {field}"

    def test_seal_hash_present(self):
        from demos.golden_path.assembler import RecordToEpisodeAssembler
        records = self._load_records()
        ep = RecordToEpisodeAssembler().assemble(records, source_name="sharepoint")
        assert ep["seal"]["sealHash"]
        assert len(ep["seal"]["sealHash"]) == 64  # SHA-256 hex

    def test_custom_episode_id(self):
        from demos.golden_path.assembler import RecordToEpisodeAssembler
        records = [self._load_records()[0]]
        ep = RecordToEpisodeAssembler().assemble(records, episode_id="custom-123")
        assert ep["episodeId"] == "custom-123"

    def test_empty_records_raises(self):
        from demos.golden_path.assembler import RecordToEpisodeAssembler
        import pytest
        with pytest.raises(ValueError, match="empty"):
            RecordToEpisodeAssembler().assemble([])

    def test_provenance_chain(self):
        from demos.golden_path.assembler import RecordToEpisodeAssembler
        records = self._load_records()[:2]
        ep = RecordToEpisodeAssembler().assemble(records, source_name="sharepoint")
        refs = ep["context"]["evidenceRefs"]
        assert all("sharepoint://" in r for r in refs)


# ── ClaimExtractor Tests ─────────────────────────────────────────────

class TestClaimExtractor:

    def _load_records(self):
        return json.loads(Path(FIXTURE_DIR, "baseline.json").read_text())

    def test_one_claim_per_record(self):
        from demos.golden_path.claim_extractor import ClaimExtractor
        records = self._load_records()
        claims = ClaimExtractor().extract(records)
        assert len(claims) == len(records)

    def test_claim_has_required_fields(self):
        from demos.golden_path.claim_extractor import ClaimExtractor
        records = self._load_records()[:1]
        claims = ClaimExtractor().extract(records)
        claim = claims[0]
        for field in ("claim_id", "text", "source_ref", "confidence", "status", "evidence"):
            assert field in claim, f"Missing: {field}"

    def test_confidence_to_status_green(self):
        from demos.golden_path.claim_extractor import ClaimExtractor
        records = [{"record_id": "test", "content": {"title": "T"}, "confidence": {"score": 0.85}, "provenance": [{"ref": "x"}]}]
        claims = ClaimExtractor().extract(records)
        assert claims[0]["status"] == "green"

    def test_confidence_to_status_yellow(self):
        from demos.golden_path.claim_extractor import ClaimExtractor
        records = [{"record_id": "test", "content": {"title": "T"}, "confidence": {"score": 0.55}, "provenance": [{"ref": "x"}]}]
        claims = ClaimExtractor().extract(records)
        assert claims[0]["status"] == "yellow"

    def test_confidence_to_status_red(self):
        from demos.golden_path.claim_extractor import ClaimExtractor
        records = [{"record_id": "test", "content": {"title": "T"}, "confidence": {"score": 0.3}, "provenance": [{"ref": "x"}]}]
        claims = ClaimExtractor().extract(records)
        assert claims[0]["status"] == "red"

    def test_empty_records(self):
        from demos.golden_path.claim_extractor import ClaimExtractor
        claims = ClaimExtractor().extract([])
        assert claims == []


# ── DeltaDriftDetector Tests ─────────────────────────────────────────

class TestDeltaDriftDetector:

    def _load_baseline(self):
        return json.loads(Path(FIXTURE_DIR, "baseline.json").read_text())

    def _load_delta(self):
        return json.loads(Path(FIXTURE_DIR, "delta.json").read_text())

    def test_no_changes_no_drift(self):
        from demos.golden_path.delta_detector import DeltaDriftDetector
        baseline = self._load_baseline()
        drifts = DeltaDriftDetector().detect(baseline, baseline, "ep-test")
        # No new/changed/removed, maybe freshness depending on TTL
        non_freshness = [d for d in drifts if d["driftType"] != "freshness"]
        assert len(non_freshness) == 0

    def test_new_record_detected(self):
        from demos.golden_path.delta_detector import DeltaDriftDetector
        baseline = self._load_baseline()
        delta = self._load_delta()
        drifts = DeltaDriftDetector().detect(baseline, delta, "ep-test")
        new_drifts = [d for d in drifts if d["driftType"] == "new_evidence"]
        assert len(new_drifts) >= 1

    def test_changed_record_detected(self):
        from demos.golden_path.delta_detector import DeltaDriftDetector
        baseline = self._load_baseline()
        delta = self._load_delta()
        drifts = DeltaDriftDetector().detect(baseline, delta, "ep-test")
        changed = [d for d in drifts if d["driftType"] == "evidence_changed"]
        assert len(changed) >= 1

    def test_removed_record_detected(self):
        from demos.golden_path.delta_detector import DeltaDriftDetector
        baseline = self._load_baseline()
        delta = self._load_delta()
        drifts = DeltaDriftDetector().detect(baseline, delta, "ep-test")
        removed = [d for d in drifts if d["driftType"] == "evidence_removed"]
        assert len(removed) >= 1

    def test_confidence_drop_is_red(self):
        from demos.golden_path.delta_detector import DeltaDriftDetector
        baseline = self._load_baseline()
        delta = self._load_delta()
        drifts = DeltaDriftDetector().detect(baseline, delta, "ep-test")
        # Record b2c3... had confidence 0.75→0.40
        red_changed = [d for d in drifts if d["driftType"] == "evidence_changed" and d["severity"] == "red"]
        assert len(red_changed) >= 1

    def test_drift_event_structure(self):
        from demos.golden_path.delta_detector import DeltaDriftDetector
        baseline = self._load_baseline()
        delta = self._load_delta()
        drifts = DeltaDriftDetector().detect(baseline, delta, "ep-test")
        assert len(drifts) > 0
        d = drifts[0]
        for field in ("driftId", "episodeId", "detectedAt", "severity", "fingerprint"):
            assert field in d, f"Missing: {field}"
        assert isinstance(d["fingerprint"], dict)
        assert "key" in d["fingerprint"]
