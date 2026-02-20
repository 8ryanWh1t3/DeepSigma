"""
Tests for compression_engine and primitives.compression.
"""
import pytest

from engine.compression import calculate_entropy, compress_claims
from engine.compression_engine import apply_compression


# ── primitives.compression ──


class TestCalculateEntropy:
    def test_empty(self):
        assert calculate_entropy([]) == 0.0

    def test_all_unique(self):
        assert calculate_entropy(["a", "b", "c"]) == 1.0

    def test_all_same(self):
        assert calculate_entropy(["a", "a", "a"]) == pytest.approx(1 / 3)

    def test_mixed(self):
        ent = calculate_entropy(["a", "b", "a"])
        assert 0 < ent < 1

    def test_dict_claims(self):
        claims = [{"k": 1}, {"k": 2}, {"k": 1}]
        ent = calculate_entropy(claims)
        assert 0 < ent < 1


class TestCompressClaims:
    def test_empty(self):
        result = compress_claims([])
        assert result["claim_count"] == 0
        assert result["entropy"] == 0.0
        assert isinstance(result["semantic_hash"], int)

    def test_basic(self):
        result = compress_claims(["claim A", "claim B"])
        assert result["claim_count"] == 2
        assert result["entropy"] == 1.0
        assert result["semantic_hash"] > 0

    def test_deterministic(self):
        a = compress_claims(["x", "y", "z"])
        b = compress_claims(["x", "y", "z"])
        assert a["semantic_hash"] == b["semantic_hash"]

    def test_different_order_same_hash(self):
        a = compress_claims(["x", "y"])
        b = compress_claims(["y", "x"])
        assert a["semantic_hash"] == b["semantic_hash"]

    def test_different_claims_different_hash(self):
        a = compress_claims(["alpha"])
        b = compress_claims(["beta"])
        assert a["semantic_hash"] != b["semantic_hash"]


# ── engine.compression_engine ──


class TestApplyCompression:
    def test_basic(self):
        episode = {"claims": ["c1", "c2"]}
        result = apply_compression(episode)
        assert "compression" in result
        assert result["compression"]["claim_count"] == 2

    def test_empty_claims(self):
        episode = {"claims": []}
        result = apply_compression(episode)
        assert result["compression"]["claim_count"] == 0

    def test_missing_claims_key(self):
        episode = {"other": "data"}
        result = apply_compression(episode)
        assert result["claims"] == []
        assert result["compression"]["claim_count"] == 0

    def test_mutates_in_place(self):
        episode = {"claims": ["a"]}
        returned = apply_compression(episode)
        assert returned is episode
