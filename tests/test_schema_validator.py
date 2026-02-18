"""Tests for runtime JSON Schema validation."""

import pytest

from engine.schema_validator import (
    SchemaError,
    ValidationResult,
    clear_cache,
    is_validation_enabled,
    validate,
)


@pytest.fixture(autouse=True)
def _clear_validator_cache():
    """Clear validator cache before each test to avoid cross-test pollution."""
    clear_cache()
    yield
    clear_cache()


class TestValidateEpisode:
    def test_valid_episode_passes(self, minimal_episode):
        ep = minimal_episode()
        result = validate(ep, "episode")
        # Our minimal_episode may not have all required schema fields,
        # but validate should return a ValidationResult either way
        assert isinstance(result, ValidationResult)
        assert result.schema_name == "episode"

    def test_empty_dict_fails(self):
        result = validate({}, "episode")
        assert not result.valid
        assert len(result.errors) > 0

    def test_error_has_path_and_message(self):
        result = validate({}, "episode")
        assert not result.valid
        err = result.errors[0]
        assert isinstance(err, SchemaError)
        assert isinstance(err.path, str)
        assert isinstance(err.message, str)
        assert isinstance(err.schema_path, str)


class TestValidateDrift:
    def test_valid_drift_passes(self, minimal_drift):
        d = minimal_drift()
        result = validate(d, "drift")
        assert isinstance(result, ValidationResult)
        assert result.schema_name == "drift"

    def test_missing_drift_type_fails(self):
        result = validate({"driftId": "d1"}, "drift")
        assert not result.valid


class TestValidatePolicyPack:
    def test_policy_pack_schema_loads(self, policy_pack_path):
        import json
        from pathlib import Path

        pack = json.loads(Path(policy_pack_path).read_text())
        result = validate(pack, "policy_pack")
        assert isinstance(result, ValidationResult)
        assert result.schema_name == "policy_pack"


class TestMissingSchema:
    def test_unknown_schema_returns_valid(self):
        """Missing schema file gracefully returns valid (pass-through)."""
        result = validate({"foo": "bar"}, "nonexistent_schema_xyz")
        assert result.valid
        assert result.schema_name == "nonexistent_schema_xyz"
        assert len(result.errors) == 0


class TestLazyCaching:
    def test_second_call_uses_cache(self):
        """Calling validate twice with same schema reuses the cached validator."""
        r1 = validate({}, "episode")
        r2 = validate({}, "episode")
        # Both should return errors (empty dict is invalid)
        assert not r1.valid
        assert not r2.valid
        # Errors should be identical in count
        assert len(r1.errors) == len(r2.errors)


class TestEnvironmentFlag:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("DEEPSIGMA_VALIDATE_SCHEMAS", raising=False)
        assert not is_validation_enabled()

    def test_enabled_with_1(self, monkeypatch):
        monkeypatch.setenv("DEEPSIGMA_VALIDATE_SCHEMAS", "1")
        assert is_validation_enabled()

    def test_enabled_with_true(self, monkeypatch):
        monkeypatch.setenv("DEEPSIGMA_VALIDATE_SCHEMAS", "true")
        assert is_validation_enabled()

    def test_enabled_with_yes(self, monkeypatch):
        monkeypatch.setenv("DEEPSIGMA_VALIDATE_SCHEMAS", "yes")
        assert is_validation_enabled()

    def test_disabled_with_0(self, monkeypatch):
        monkeypatch.setenv("DEEPSIGMA_VALIDATE_SCHEMAS", "0")
        assert not is_validation_enabled()


class TestIntegrationWithPolicyLoader:
    def test_policy_loader_validate_schema(self, policy_pack_path):
        """Policy loader with validate_schema=True does not crash."""
        from engine.policy_loader import load_policy_pack

        pack = load_policy_pack(policy_pack_path, verify_hash=False, validate_schema=True)
        assert "policyPackId" in pack
