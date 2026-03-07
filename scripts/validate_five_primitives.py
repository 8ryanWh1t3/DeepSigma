#!/usr/bin/env python3
"""Five-Primitive Guard — CI validator.

Enforces the rule that exactly five canonical primitive types exist:
CLAIM, EVENT, REVIEW, PATCH, APPLY.

Checks:
  1. PrimitiveType enum has exactly 5 members.
  2. primitive_envelope.schema.json enum matches PrimitiveType values.
  3. No sixth primitive type in src/core/ source files.
  4. CERPA coverage — each PrimitiveType maps to a CERPA model class.
  5. wrap_primitive() call-site scan — only 5 allowed types.
  6. NodeKind alignment — PRIMITIVE_TO_NODE_KIND covers all 5 types.
  7. No rogue primitive-like dataclasses in core/*.py.

Usage:
    python scripts/validate_five_primitives.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

EXPECTED_TYPES = {"claim", "event", "review", "patch", "apply"}
SCHEMA_PATH = SRC_ROOT / "core" / "schemas" / "primitives" / "primitive_envelope.schema.json"
CORE_DIR = SRC_ROOT / "core"

passed = 0
failed = 0
errors: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f": {detail}"
        print(msg)
        errors.append(msg)


# ── Check 1: Enum count ─────────────────────────────────────────

print("Five-Primitive Guard")
print("=" * 50)

from core.primitives import ALLOWED_PRIMITIVE_TYPES, PrimitiveType  # noqa: E402

enum_values = {p.value for p in PrimitiveType}
check(
    "PrimitiveType has exactly 5 members",
    len(PrimitiveType) == 5,
    f"Found {len(PrimitiveType)}: {enum_values}",
)
check(
    "PrimitiveType values match expected set",
    enum_values == EXPECTED_TYPES,
    f"Got {enum_values}, expected {EXPECTED_TYPES}",
)
check(
    "ALLOWED_PRIMITIVE_TYPES matches enum",
    set(ALLOWED_PRIMITIVE_TYPES) == EXPECTED_TYPES,
    f"Got {set(ALLOWED_PRIMITIVE_TYPES)}",
)


# ── Check 2: Schema match ───────────────────────────────────────

if SCHEMA_PATH.exists():
    schema = json.loads(SCHEMA_PATH.read_text())
    schema_enum = set(schema["properties"]["primitiveType"]["enum"])
    check(
        "Schema enum matches PrimitiveType",
        schema_enum == EXPECTED_TYPES,
        f"Schema has {schema_enum}, expected {EXPECTED_TYPES}",
    )
else:
    check("Schema file exists", False, f"Not found: {SCHEMA_PATH}")


# ── Check 3: No sixth primitive ─────────────────────────────────

# Scan for any new PrimitiveType-like additions
SIXTH_PATTERN = re.compile(
    r"""PrimitiveType\.\w+\s*=\s*["'](\w+)["']""",
)

sixth_found = []
for py_file in CORE_DIR.rglob("*.py"):
    text = py_file.read_text()
    for match in SIXTH_PATTERN.finditer(text):
        value = match.group(1)
        if value not in EXPECTED_TYPES:
            sixth_found.append(f"{py_file.relative_to(REPO_ROOT)}:{value}")

check(
    "No sixth primitive type defined",
    len(sixth_found) == 0,
    f"Found: {sixth_found}" if sixth_found else "",
)


# ── Check 4: CERPA coverage ─────────────────────────────────────

from core.cerpa.models import ApplyResult, Claim, Event, Patch, Review  # noqa: E402

cerpa_map = {
    "claim": Claim,
    "event": Event,
    "review": Review,
    "patch": Patch,
    "apply": ApplyResult,
}

for ptype in EXPECTED_TYPES:
    cls = cerpa_map.get(ptype)
    check(
        f"CERPA model for '{ptype}'",
        cls is not None,
        f"No CERPA model class for {ptype}" if cls is None else "",
    )


# ── Check 5: wrap_primitive() call-site scan ─────────────────────

WRAP_PATTERN = re.compile(r"""wrap_primitive\(\s*["'](\w+)["']""")
WRAP_REF_PATTERN = re.compile(r"""wrap_primitive\(\s*PrimitiveType\.(\w+)\.value""")

bad_calls = []
for py_file in CORE_DIR.rglob("*.py"):
    text = py_file.read_text()
    for match in WRAP_PATTERN.finditer(text):
        value = match.group(1)
        if value not in EXPECTED_TYPES:
            bad_calls.append(f"{py_file.relative_to(REPO_ROOT)}:{value}")
    # Also accept PrimitiveType.CLAIM.value style (always valid by definition)

check(
    "wrap_primitive() call sites use allowed types only",
    len(bad_calls) == 0,
    f"Unrecognised types: {bad_calls}" if bad_calls else "",
)


# ── Check 6: NodeKind alignment ─────────────────────────────────

from core.primitive_mg import PRIMITIVE_TO_NODE_KIND  # noqa: E402
from core.memory_graph import NodeKind  # noqa: E402

mg_mapped = set(PRIMITIVE_TO_NODE_KIND.keys())
mg_expected = set(PrimitiveType)
check(
    "PRIMITIVE_TO_NODE_KIND maps all 5 types",
    mg_mapped == mg_expected,
    f"Mapped: {[p.value for p in mg_mapped]}, expected: {[p.value for p in mg_expected]}",
)

for ptype, nkind in PRIMITIVE_TO_NODE_KIND.items():
    check(
        f"NodeKind.{nkind.name} exists for {ptype.value}",
        nkind in NodeKind,
        f"NodeKind.{nkind.name} not found",
    )


# ── Check 7: No rogue primitive-like dataclasses ────────────────

PRIMITIVE_TYPE_FIELD = re.compile(r"primitive_type\s*[:=]")
DATACLASS_PATTERN = re.compile(r"@dataclass")
KNOWN_CLASSES = {
    "PrimitiveEnvelope",
    "ClaimRecord",
    "EventRecord",
    "ReviewRecord",
    "PatchRecord",
    "ApplyRecord",
}

rogue = []
for py_file in CORE_DIR.glob("*.py"):  # top-level only, not subpackages
    text = py_file.read_text()
    if DATACLASS_PATTERN.search(text) and PRIMITIVE_TYPE_FIELD.search(text):
        # Extract class names
        for cm in re.finditer(r"\bclass\s+(\w+)", text):
            cls_name = cm.group(1)
            if cls_name not in KNOWN_CLASSES:
                rogue.append(f"{py_file.name}:{cls_name}")

check(
    "No rogue primitive-type dataclasses in core/",
    len(rogue) == 0,
    f"Found: {rogue}. Register in KNOWN_CLASSES if intentional." if rogue else "",
)


# ── Summary ─────────────────────────────────────────────────────

print()
print(f"Results: {passed} passed, {failed} failed")

if failed:
    print()
    print("ERRORS:")
    for e in errors:
        print(e)
    sys.exit(1)
else:
    print("Five-Primitive Guard: PASS")
    sys.exit(0)
