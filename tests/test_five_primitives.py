"""Tests for the Five-Primitive Guard — CI validator."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.primitives import ALLOWED_PRIMITIVE_TYPES, PrimitiveType  # noqa: E402

EXPECTED = {"claim", "event", "review", "patch", "apply"}
SCHEMA_PATH = _SRC_ROOT / "core" / "schemas" / "primitives" / "primitive_envelope.schema.json"


class TestEnumGuard:
    def test_exactly_five_members(self):
        assert len(PrimitiveType) == 5

    def test_values_match_expected(self):
        assert {p.value for p in PrimitiveType} == EXPECTED

    def test_allowed_set_matches(self):
        assert set(ALLOWED_PRIMITIVE_TYPES) == EXPECTED


class TestSchemaGuard:
    def test_schema_enum_matches(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        schema_enum = set(schema["properties"]["primitiveType"]["enum"])
        assert schema_enum == EXPECTED


class TestCerpaCoverage:
    def test_each_type_has_cerpa_model(self):
        from core.cerpa.models import ApplyResult, Claim, Event, Patch, Review  # noqa: E402

        mapping = {
            "claim": Claim,
            "event": Event,
            "review": Review,
            "patch": Patch,
            "apply": ApplyResult,
        }
        for ptype in EXPECTED:
            assert ptype in mapping
            assert mapping[ptype] is not None


class TestValidatorScript:
    def test_validator_exits_zero(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "scripts" / "validate_five_primitives.py")],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
