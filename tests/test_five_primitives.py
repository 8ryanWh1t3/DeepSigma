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


class TestCallSiteScan:
    """Check 5: wrap_primitive() call-site scan."""

    def test_all_call_sites_use_allowed_types(self):
        import re
        core_dir = _SRC_ROOT / "core"
        pattern = re.compile(r"""wrap_primitive\(\s*["'](\w+)["']""")
        bad = []
        for py_file in core_dir.rglob("*.py"):
            for match in pattern.finditer(py_file.read_text()):
                if match.group(1) not in EXPECTED:
                    bad.append(f"{py_file.name}:{match.group(1)}")
        assert bad == [], f"Unexpected wrap_primitive types: {bad}"


class TestNodeKindAlignment:
    """Check 6: PRIMITIVE_TO_NODE_KIND maps all 5 types."""

    def test_all_types_mapped(self):
        from core.primitive_mg import PRIMITIVE_TO_NODE_KIND
        assert set(PRIMITIVE_TO_NODE_KIND.keys()) == set(PrimitiveType)

    def test_node_kinds_exist(self):
        from core.primitive_mg import PRIMITIVE_TO_NODE_KIND
        from core.memory_graph import NodeKind
        for ptype, nkind in PRIMITIVE_TO_NODE_KIND.items():
            assert nkind in NodeKind, f"NodeKind.{nkind.name} missing for {ptype.value}"


class TestNoRogueDataclasses:
    """Check 7: no rogue primitive-type dataclasses in core/."""

    def test_no_unregistered_primitive_type_classes(self):
        import re
        core_dir = _SRC_ROOT / "core"
        known = {
            "PrimitiveEnvelope",
            "ClaimRecord", "EventRecord", "ReviewRecord",
            "PatchRecord", "ApplyRecord",
        }
        ptype_field = re.compile(r"primitive_type\s*[:=]")
        dc_pattern = re.compile(r"@dataclass")
        rogue = []
        for py_file in core_dir.glob("*.py"):
            text = py_file.read_text()
            if dc_pattern.search(text) and ptype_field.search(text):
                for cm in re.finditer(r"\bclass\s+(\w+)", text):
                    if cm.group(1) not in known:
                        rogue.append(f"{py_file.name}:{cm.group(1)}")
        assert rogue == [], f"Rogue dataclasses: {rogue}"


class TestValidatorScript:
    def test_validator_exits_zero(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "scripts" / "validate_five_primitives.py")],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
