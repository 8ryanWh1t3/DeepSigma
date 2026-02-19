"""
Tests for verifiers — read_after_write and invariant_check.
"""
from verifiers.read_after_write import verify as raw_verify
from verifiers.invariant_check import verify as invariant_verify


# ── read_after_write ──


class TestReadAfterWrite:
    def test_pass_all_match(self):
        result = raw_verify(lambda: {"a": 1, "b": 2}, {"a": 1, "b": 2})
        assert result["result"] == "pass"
        assert result["details"]["state"] == {"a": 1, "b": 2}

    def test_fail_mismatch(self):
        result = raw_verify(lambda: {"a": 1, "b": 99}, {"a": 1, "b": 2})
        assert result["result"] == "fail"
        assert "b" in result["details"]["mismatches"]
        assert result["details"]["mismatches"]["b"]["expected"] == 2
        assert result["details"]["mismatches"]["b"]["got"] == 99

    def test_fail_missing_key(self):
        result = raw_verify(lambda: {"a": 1}, {"a": 1, "b": 2})
        assert result["result"] == "fail"
        assert result["details"]["mismatches"]["b"]["got"] is None

    def test_inconclusive_on_exception(self):
        def boom():
            raise RuntimeError("storage unavailable")
        result = raw_verify(boom, {"a": 1})
        assert result["result"] == "inconclusive"
        assert "storage unavailable" in result["details"]["error"]

    def test_pass_empty_expected(self):
        result = raw_verify(lambda: {"x": 42}, {})
        assert result["result"] == "pass"

    def test_pass_extra_state_keys(self):
        result = raw_verify(lambda: {"a": 1, "b": 2, "c": 3}, {"a": 1})
        assert result["result"] == "pass"


# ── invariant_check ──


class TestInvariantCheck:
    def test_pass(self):
        result = invariant_verify(lambda s: s["count"] > 0, {"count": 5}, "positive_count")
        assert result["result"] == "pass"
        assert result["details"]["name"] == "positive_count"

    def test_fail(self):
        result = invariant_verify(lambda s: s["count"] > 0, {"count": 0}, "positive_count")
        assert result["result"] == "fail"

    def test_inconclusive_on_exception(self):
        result = invariant_verify(lambda s: s["missing"], {}, "bad_access")
        assert result["result"] == "inconclusive"
        assert "bad_access" in result["details"]["name"]

    def test_default_name(self):
        result = invariant_verify(lambda s: True, {})
        assert result["details"]["name"] == "invariant"

    def test_truthy_coercion(self):
        result = invariant_verify(lambda s: s.get("items"), {"items": [1, 2]})
        assert result["result"] == "pass"

    def test_falsy_coercion(self):
        result = invariant_verify(lambda s: s.get("items"), {"items": []})
        assert result["result"] == "fail"
