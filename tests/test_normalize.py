"""Tests for core.normalize — camel/snake key conversion."""
from core.normalize import _camel_to_snake, _snake_to_camel, normalize_keys


class TestCamelToSnake:
    """Edge cases for _camel_to_snake."""

    def test_simple(self):
        assert _camel_to_snake("episodeId") == "episode_id"

    def test_multi_word(self):
        assert _camel_to_snake("blastRadiusTier") == "blast_radius_tier"

    def test_short_abbrev(self):
        assert _camel_to_snake("dteRef") == "dte_ref"

    def test_upper_run(self):
        assert _camel_to_snake("TTLMs") == "ttl_ms"

    def test_numeric_prefix(self):
        assert _camel_to_snake("p95Ms") == "p95_ms"

    def test_single_word_lowercase(self):
        assert _camel_to_snake("outcome") == "outcome"

    def test_already_snake(self):
        assert _camel_to_snake("episode_id") == "episode_id"

    def test_recommended_patch_type(self):
        assert _camel_to_snake("recommendedPatchType") == "recommended_patch_type"

    def test_sealed_at(self):
        assert _camel_to_snake("sealedAt") == "sealed_at"

    def test_decision_type(self):
        assert _camel_to_snake("decisionType") == "decision_type"

    def test_idempotency_key(self):
        assert _camel_to_snake("idempotencyKey") == "idempotency_key"

    def test_seal_hash(self):
        assert _camel_to_snake("sealHash") == "seal_hash"

    def test_evidence_refs(self):
        assert _camel_to_snake("evidenceRefs") == "evidence_refs"


class TestSnakeToCamel:
    """Edge cases for _snake_to_camel."""

    def test_simple(self):
        assert _snake_to_camel("episode_id") == "episodeId"

    def test_multi_word(self):
        assert _snake_to_camel("blast_radius_tier") == "blastRadiusTier"

    def test_single_word(self):
        assert _snake_to_camel("outcome") == "outcome"

    def test_already_camel(self):
        assert _snake_to_camel("episodeId") == "episodeId"


class TestRoundTrip:
    """snake_to_camel(camel_to_snake(k)) == k for all schema keys."""

    SCHEMA_KEYS = [
        "episodeId", "decisionType", "sealedAt", "dteRef",
        "blastRadiusTier", "driftType", "detectedAt",
        "recommendedPatchType", "idempotencyKey", "sealHash",
        "evidenceRefs", "targetRefs", "rollbackPlan",
        "policyPackId", "outcomeCode", "degradeStep",
        "endToEndMs", "hopCount", "toolCallCount",
    ]

    def test_round_trip(self):
        for key in self.SCHEMA_KEYS:
            snake = _camel_to_snake(key)
            back = _snake_to_camel(snake)
            assert back == key, f"{key} -> {snake} -> {back}"


class TestNormalizeKeys:
    """normalize_keys deep conversion."""

    def test_snake_flat(self):
        data = {"episodeId": "ep-1", "decisionType": "deploy"}
        result = normalize_keys(data, style="snake")
        assert result == {"episode_id": "ep-1", "decision_type": "deploy"}

    def test_camel_flat(self):
        data = {"episode_id": "ep-1", "decision_type": "deploy"}
        result = normalize_keys(data, style="camel")
        assert result == {"episodeId": "ep-1", "decisionType": "deploy"}

    def test_nested_dict(self):
        data = {"outcome": {"outcomeCode": "success"}}
        result = normalize_keys(data, style="snake")
        assert result == {"outcome": {"outcome_code": "success"}}

    def test_nested_list(self):
        data = {"actions": [{"blastRadiusTier": "low"}]}
        result = normalize_keys(data, style="snake")
        assert result == {"actions": [{"blast_radius_tier": "low"}]}

    def test_list_input(self):
        data = [{"episodeId": "a"}, {"episodeId": "b"}]
        result = normalize_keys(data, style="snake")
        assert result == [{"episode_id": "a"}, {"episode_id": "b"}]

    def test_scalar_passthrough(self):
        assert normalize_keys(42, style="snake") == 42
        assert normalize_keys("hello", style="camel") == "hello"
        assert normalize_keys(None, style="snake") is None

    def test_invalid_style_raises(self):
        import pytest
        with pytest.raises(ValueError, match="Unsupported"):
            normalize_keys({}, style="kebab")

    def test_deep_episode(self):
        """Full episode dict normalizes correctly."""
        episode = {
            "episodeId": "ep-1",
            "decisionType": "deploy",
            "sealedAt": "2026-01-01T00:00:00Z",
            "actions": [
                {
                    "idempotencyKey": "ik-1",
                    "blastRadiusTier": "account",
                    "targetRefs": ["acc-1"],
                }
            ],
            "context": {"evidenceRefs": ["ev-1"]},
            "outcome": {"code": "success"},
            "seal": {"sealHash": "sha256:abc"},
        }
        result = normalize_keys(episode, style="snake")
        assert result["episode_id"] == "ep-1"
        assert result["decision_type"] == "deploy"
        assert result["sealed_at"] == "2026-01-01T00:00:00Z"
        assert result["actions"][0]["idempotency_key"] == "ik-1"
        assert result["actions"][0]["blast_radius_tier"] == "account"
        assert result["actions"][0]["target_refs"] == ["acc-1"]
        assert result["context"]["evidence_refs"] == ["ev-1"]
        assert result["seal"]["seal_hash"] == "sha256:abc"
