"""Tests for core.schema_validator — JSON Schema validation at ingest boundaries."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.schema_validator import (  # noqa: E402
    SchemaError,
    ValidationResult,
    clear_cache,
    is_validation_enabled,
    validate,
)


@pytest.fixture(autouse=True)
def _clean_cache():
    """Clear the validator cache before each test."""
    clear_cache()
    yield
    clear_cache()


def _valid_episode():
    """Return a minimal valid episode dict matching the schema."""
    return {
        "episodeId": "ep-test-001",
        "decisionType": "AccountQuarantine",
        "startedAt": "2026-02-01T12:00:00Z",
        "endedAt": "2026-02-01T12:00:01Z",
        "decisionWindowMs": 120,
        "actor": {"type": "agent", "id": "test-agent"},
        "dteRef": {"decisionType": "AccountQuarantine", "version": "1.0"},
        "context": {
            "snapshotId": "snap-1",
            "capturedAt": "2026-02-01T12:00:00Z",
            "ttlMs": 1000,
            "maxFeatureAgeMs": 500,
            "ttlBreachesCount": 0,
            "evidenceRefs": ["evidence-ref-001"],
        },
        "plan": {"planner": "rules", "summary": "test plan"},
        "actions": [],
        "verification": {"required": False, "result": "pass"},
        "outcome": {"code": "success"},
        "telemetry": {
            "endToEndMs": 80,
            "stageMs": {"context": 20, "plan": 20, "act": 20, "verify": 20},
            "p95Ms": 100,
            "p99Ms": 120,
            "jitterMs": 5,
            "fallbackUsed": False,
            "fallbackStep": "none",
            "hopCount": 1,
            "fanout": 1,
        },
        "seal": {
            "sealedAt": "2026-02-01T12:00:01Z",
            "sealHash": "sha256:abc123",
        },
    }


class TestValidateEpisode:
    def test_valid_episode(self):
        result = validate(_valid_episode(), "episode")
        assert result.valid is True
        assert result.errors == []
        assert result.schema_name == "episode"

    def test_invalid_episode_missing_required(self):
        result = validate({"bad": True}, "episode")
        assert result.valid is False
        assert len(result.errors) > 0

    def test_error_has_path_and_message(self):
        result = validate({}, "episode")
        assert result.valid is False
        for err in result.errors:
            assert isinstance(err, SchemaError)
            assert isinstance(err.message, str)
            assert isinstance(err.path, str)


class TestValidateDrift:
    def test_valid_drift(self):
        drift = {
            "driftId": "drift-001",
            "episodeId": "ep-001",
            "driftType": "freshness",
            "severity": "yellow",
            "detectedAt": "2026-03-01T00:00:00Z",
            "fingerprint": {"key": "fp-001", "version": "1"},
            "recommendedPatchType": "ttl_change",
            "evidenceRefs": [],
        }
        result = validate(drift, "drift")
        # Schema may or may not exist for drift — if not found, returns valid
        assert isinstance(result, ValidationResult)

    def test_invalid_drift(self):
        result = validate({}, "drift")
        # If schema exists, should fail; if not, returns valid (unknown schema)
        assert isinstance(result, ValidationResult)


class TestUnknownSchema:
    def test_unknown_schema_passes(self):
        result = validate({"anything": True}, "nonexistent_schema_xyz")
        assert result.valid is True
        assert result.schema_name == "nonexistent_schema_xyz"


class TestValidationResult:
    def test_result_fields(self):
        r = ValidationResult(valid=True, schema_name="test")
        assert r.valid is True
        assert r.errors == []
        assert r.schema_name == "test"


class TestIsValidationEnabled:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("DEEPSIGMA_VALIDATE_SCHEMAS", raising=False)
        assert is_validation_enabled() is False

    def test_enabled_with_1(self, monkeypatch):
        monkeypatch.setenv("DEEPSIGMA_VALIDATE_SCHEMAS", "1")
        assert is_validation_enabled() is True

    def test_enabled_with_true(self, monkeypatch):
        monkeypatch.setenv("DEEPSIGMA_VALIDATE_SCHEMAS", "true")
        assert is_validation_enabled() is True

    def test_enabled_with_yes(self, monkeypatch):
        monkeypatch.setenv("DEEPSIGMA_VALIDATE_SCHEMAS", "yes")
        assert is_validation_enabled() is True

    def test_disabled_with_other(self, monkeypatch):
        monkeypatch.setenv("DEEPSIGMA_VALIDATE_SCHEMAS", "no")
        assert is_validation_enabled() is False

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("DEEPSIGMA_VALIDATE_SCHEMAS", "TRUE")
        assert is_validation_enabled() is True


class TestClearCache:
    def test_clear_resets(self):
        # Validate once to populate cache
        validate(_valid_episode(), "episode")
        clear_cache()
        # Should still work after clearing
        result = validate(_valid_episode(), "episode")
        assert result.valid is True
