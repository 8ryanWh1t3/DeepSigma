"""Tests for core.primitive_envelope — canonical envelope wrapping."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.primitive_envelope import (  # noqa: E402
    PrimitiveEnvelope,
    supersede_envelope,
    validate_envelope,
    wrap_primitive,
)
from core.primitives import ALLOWED_PRIMITIVE_TYPES, PrimitiveType  # noqa: E402


def _sample_payload():
    return {"id": "C-001", "text": "System is healthy", "domain": "ops"}


# ── wrap_primitive ──────────────────────────────────────────────


class TestWrapPrimitive:
    def test_produces_valid_envelope(self):
        env = wrap_primitive("claim", _sample_payload(), "test-src")
        assert isinstance(env, PrimitiveEnvelope)
        assert env.primitive_type == PrimitiveType.CLAIM
        assert env.version == 1
        assert env.payload == _sample_payload()
        assert env.source == "test-src"
        assert env.sealed is False

    def test_envelope_id_format(self):
        env = wrap_primitive("claim", _sample_payload(), "test")
        assert env.envelope_id.startswith("ENV-")
        assert len(env.envelope_id) == len("ENV-") + 12

    def test_created_at_populated(self):
        env = wrap_primitive("event", _sample_payload(), "test")
        assert env.created_at is not None
        assert len(env.created_at) > 0

    def test_all_five_types(self):
        for ptype in ALLOWED_PRIMITIVE_TYPES:
            env = wrap_primitive(ptype, _sample_payload(), "test")
            assert env.primitive_type.value == ptype

    def test_rejects_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown primitive type"):
            wrap_primitive("widget", _sample_payload(), "test")

    def test_rejects_empty_type(self):
        with pytest.raises(ValueError):
            wrap_primitive("", _sample_payload(), "test")

    def test_custom_metadata(self):
        meta = {"priority": "high", "ttl": 3600}
        env = wrap_primitive("claim", _sample_payload(), "test", metadata=meta)
        assert env.metadata == meta

    def test_custom_version(self):
        env = wrap_primitive("claim", _sample_payload(), "test", version=3)
        assert env.version == 3

    def test_parent_envelope_id(self):
        env = wrap_primitive(
            "claim", _sample_payload(), "test",
            parent_envelope_id="ENV-aabbccddee00",
        )
        assert env.parent_envelope_id == "ENV-aabbccddee00"


# ── validate_envelope ──────────────────────────────────────────


class TestValidateEnvelope:
    def test_valid_envelope_passes(self):
        env = wrap_primitive("claim", _sample_payload(), "test")
        validate_envelope(env)  # should not raise

    def test_all_five_types_pass(self):
        for ptype in ALLOWED_PRIMITIVE_TYPES:
            env = wrap_primitive(ptype, _sample_payload(), "test")
            validate_envelope(env)  # should not raise

    def test_invalid_type_raises(self):
        env = PrimitiveEnvelope(
            envelope_id="ENV-000000000000",
            primitive_type="bogus",
            version=1,
            payload={},
            created_at="2026-01-01T00:00:00Z",
            source="test",
        )
        with pytest.raises(ValueError, match="Invalid primitive type"):
            validate_envelope(env)


# ── seal ───────────────────────────────────────────────────────


class TestSeal:
    def test_seal_sets_sealed(self):
        env = wrap_primitive("review", _sample_payload(), "test")
        assert env.sealed is False
        result = env.seal()
        assert env.sealed is True
        assert result is env  # returns self

    def test_seal_idempotent(self):
        env = wrap_primitive("patch", _sample_payload(), "test")
        env.seal()
        env.seal()
        assert env.sealed is True


# ── supersede_envelope ─────────────────────────────────────────


class TestSupersedeEnvelope:
    def test_increments_version(self):
        old = wrap_primitive("claim", _sample_payload(), "test")
        new = supersede_envelope(old, {"id": "C-002", "text": "Updated"})
        assert new.version == old.version + 1

    def test_links_parent(self):
        old = wrap_primitive("claim", _sample_payload(), "test")
        new = supersede_envelope(old, {"id": "C-002", "text": "Updated"})
        assert new.parent_envelope_id == old.envelope_id

    def test_preserves_type(self):
        old = wrap_primitive("event", _sample_payload(), "test")
        new = supersede_envelope(old, {"id": "E-002"})
        assert new.primitive_type == old.primitive_type

    def test_new_payload(self):
        old = wrap_primitive("claim", _sample_payload(), "test")
        new_payload = {"id": "C-002", "text": "New text"}
        new = supersede_envelope(old, new_payload)
        assert new.payload == new_payload

    def test_custom_source(self):
        old = wrap_primitive("claim", _sample_payload(), "original")
        new = supersede_envelope(old, {}, source="override")
        assert new.source == "override"

    def test_default_source_from_old(self):
        old = wrap_primitive("claim", _sample_payload(), "original")
        new = supersede_envelope(old, {})
        assert new.source == "original"

    def test_preserves_metadata(self):
        old = wrap_primitive("claim", _sample_payload(), "test", metadata={"k": "v"})
        new = supersede_envelope(old, {})
        assert new.metadata == {"k": "v"}


# ── to_dict ────────────────────────────────────────────────────


class TestToDict:
    def test_round_trip_keys(self):
        env = wrap_primitive("claim", _sample_payload(), "test")
        d = env.to_dict()
        assert "envelopeId" in d
        assert "primitiveType" in d
        assert "version" in d
        assert "payload" in d
        assert "createdAt" in d
        assert "source" in d
        assert "sealed" in d

    def test_parent_included_when_set(self):
        env = wrap_primitive(
            "claim", _sample_payload(), "test",
            parent_envelope_id="ENV-parent000000",
        )
        d = env.to_dict()
        assert d["parentEnvelopeId"] == "ENV-parent000000"

    def test_parent_absent_when_none(self):
        env = wrap_primitive("claim", _sample_payload(), "test")
        d = env.to_dict()
        assert "parentEnvelopeId" not in d

    def test_metadata_included_when_set(self):
        env = wrap_primitive("claim", _sample_payload(), "test", metadata={"k": "v"})
        d = env.to_dict()
        assert d["metadata"] == {"k": "v"}

    def test_metadata_absent_when_empty(self):
        env = wrap_primitive("claim", _sample_payload(), "test")
        d = env.to_dict()
        assert "metadata" not in d
